import json
import os
import signal
import time
from pathlib import Path

import pytest

from gemini_service import (
    extract_woningmodel_data,
    get_measure_gap_analysis_with_gemini,
    get_scenario_advice_with_gemini,
    upload_case_file,
)
from schemas import Constraints, MeasureOverview
from services.normalization_service import normalize_woningmodel
from services.poc_flow_service import run_poc_flow

pytestmark = [pytest.mark.live_gemini, pytest.mark.stepwise_live]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def _step_timeout_seconds(step_name: str, default: int) -> int:
    env_key = f"LIVE_GEMINI_TIMEOUT_{step_name.upper()}"
    return _env_int(env_key, _env_int("LIVE_GEMINI_STEP_TIMEOUT_SECONDS", default))


def _debug_output_dir() -> str:
    return os.getenv("LIVE_GEMINI_DEBUG_OUTPUT_DIR", "").strip()


def _write_debug_json(filename: str, payload: dict) -> None:
    output_dir = _debug_output_dir()
    if not output_dir:
        return
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"[DEBUG] wrote {path}")


class _StepTimeout(Exception):
    pass


def _run_timed_step(step_name: str, fn, timeout_seconds: int, timings: dict[str, float]):
    def _handler(signum, frame):
        raise _StepTimeout(f"Step '{step_name}' exceeded timeout of {timeout_seconds}s.")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handler)
    started = time.monotonic()
    signal.alarm(timeout_seconds)
    try:
        result = fn()
    except _StepTimeout as exc:
        pytest.fail(
            f"{exc} Increase LIVE_GEMINI_STEP_TIMEOUT_SECONDS for slower runs.",
            pytrace=False,
        )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)

    elapsed = time.monotonic() - started
    timings[step_name] = elapsed
    print(f"[TIMING] {step_name}: {elapsed:.2f}s")
    return result


def test_live_stepwise_pipeline(sample_report_path: Path):
    step_timeout = _env_int("LIVE_GEMINI_STEP_TIMEOUT_SECONDS", 180)
    run_flow_timeout = _step_timeout_seconds("run_poc_flow", 360)
    total_budget = _env_int("LIVE_GEMINI_TOTAL_BUDGET_SECONDS", 900)
    suite_started = time.monotonic()
    timings: dict[str, float] = {}
    print(
        "[CONFIG] step_timeout=%ss run_poc_flow_timeout=%ss total_budget=%ss"
        % (step_timeout, run_flow_timeout, total_budget)
    )

    print("\n[STEP 1] sample_report.pdf aanwezig")
    assert sample_report_path.exists()

    print("\n[STEP 2] upload naar Gemini")
    uploaded = _run_timed_step(
        "upload_case_file",
        lambda: upload_case_file(str(sample_report_path)),
        timeout_seconds=step_timeout,
        timings=timings,
    )
    assert uploaded is not None

    print("\n[STEP 3] extractie naar WoningModel")
    woningmodel = _run_timed_step(
        "extract_woningmodel_data",
        lambda: extract_woningmodel_data(uploaded),
        timeout_seconds=step_timeout,
        timings=timings,
    )
    assert woningmodel.extractie_meta is not None

    print("\n[STEP 4] normalisatie")
    normalized = _run_timed_step(
        "normalize_woningmodel",
        lambda: normalize_woningmodel(woningmodel),
        timeout_seconds=step_timeout,
        timings=timings,
    )
    _write_debug_json("stepwise_woningmodel_normalized.json", normalized.model_dump())

    print("\n[STEP 5] Gemini measure gap analyse")
    statuses, overview = _run_timed_step(
        "get_measure_gap_analysis_with_gemini",
        lambda: get_measure_gap_analysis_with_gemini(woningmodel=normalized),
        timeout_seconds=step_timeout,
        timings=timings,
    )
    _write_debug_json("stepwise_measure_overview.json", overview.model_dump())
    assert len(statuses) > 0

    print("\n[STEP 6] Gemini scenario advice")
    overview = MeasureOverview.model_validate(overview.model_dump())
    advice = _run_timed_step(
        "get_scenario_advice_with_gemini",
        lambda: get_scenario_advice_with_gemini(
            constraints=Constraints(target_label="B", required_measures=[]),
            woningmodel=normalized,
            measure_overview=overview,
        ),
        timeout_seconds=step_timeout,
        timings=timings,
    )
    print(json.dumps(advice.model_dump(), indent=2, ensure_ascii=False)[:4000])

    print("\n[STEP 7] run volledige flow")
    result = _run_timed_step(
        "run_poc_flow",
        lambda: run_poc_flow(Constraints(target_label="B", required_measures=[]), woningmodel),
        timeout_seconds=run_flow_timeout,
        timings=timings,
    )
    assert result.final_report.new_label

    total_elapsed = time.monotonic() - suite_started
    print(f"[TIMING] total_live_stepwise: {total_elapsed:.2f}s")
    print(f"[TIMING] details: {json.dumps(timings, ensure_ascii=False, indent=2)}")
    assert total_elapsed <= total_budget, (
        f"Live stepwise pipeline exceeded total budget of {total_budget}s "
        f"(actual: {total_elapsed:.2f}s). "
        "Increase LIVE_GEMINI_TOTAL_BUDGET_SECONDS when needed."
    )
