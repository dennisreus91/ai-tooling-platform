import json
import os
import signal
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from gemini_service import extract_woningmodel_data, upload_case_file
from schemas import Constraints
from services.poc_flow_service import run_poc_flow

pytestmark = [pytest.mark.live_gemini, pytest.mark.e2e_live]


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
    """Allow per-step timeout overrides for slower live Gemini calls."""
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


def _run_timed_step(
    step_name: str,
    fn,
    timeout_seconds: int,
    timings: dict[str, float],
    retries: int = 0,
    retry_on: tuple[type[BaseException], ...] = (),
):
    def _handler(signum, frame):
        raise _StepTimeout(f"Step '{step_name}' exceeded timeout of {timeout_seconds}s.")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handler)
    started = time.monotonic()
    last_error: BaseException | None = None
    result = None
    for attempt in range(1, retries + 2):
        signal.alarm(timeout_seconds)
        try:
            result = fn()
            last_error = None
            break
        except _StepTimeout as exc:
            pytest.fail(
                f"{exc} Increase LIVE_GEMINI_STEP_TIMEOUT_SECONDS for slower runs.",
                pytrace=False,
            )
        except retry_on as exc:
            last_error = exc
            if attempt > retries:
                raise
            print(
                f"[RETRY] {step_name} attempt {attempt}/{retries + 1} failed: {type(exc).__name__}: {exc}"
            )
        finally:
            signal.alarm(0)

    signal.signal(signal.SIGALRM, previous_handler)
    if last_error is not None:
        raise last_error

    elapsed = time.monotonic() - started
    timings[step_name] = elapsed
    print(f"[TIMING] {step_name}: {elapsed:.2f}s")
    return result


def test_live_e2e_pipeline(sample_report_path: Path):
    step_timeout = _env_int("LIVE_GEMINI_STEP_TIMEOUT_SECONDS", 180)
    run_flow_timeout = _step_timeout_seconds("run_poc_flow", 360)
    total_budget = _env_int("LIVE_GEMINI_TOTAL_BUDGET_SECONDS", 900)
    retries = _env_int("LIVE_GEMINI_STEP_RETRIES", 1)
    suite_started = time.monotonic()
    timings: dict[str, float] = {}

    print(
        "[CONFIG] step_timeout=%ss run_poc_flow_timeout=%ss total_budget=%ss retries=%s"
        % (step_timeout, run_flow_timeout, total_budget, retries)
    )

    uploaded = _run_timed_step(
        "upload_case_file",
        lambda: upload_case_file(str(sample_report_path)),
        timeout_seconds=step_timeout,
        timings=timings,
        retries=retries,
        retry_on=(RuntimeError, ValidationError),
    )
    woningmodel = _run_timed_step(
        "extract_woningmodel_data",
        lambda: extract_woningmodel_data(uploaded),
        timeout_seconds=step_timeout,
        timings=timings,
        retries=retries,
        retry_on=(RuntimeError, ValidationError),
    )

    constraints = Constraints(target_label="B", required_measures=[])
    result = _run_timed_step(
        "run_poc_flow",
        lambda: run_poc_flow(constraints, woningmodel),
        timeout_seconds=run_flow_timeout,
        timings=timings,
        retries=retries,
        retry_on=(RuntimeError, ValidationError, ValueError),
    )
    _write_debug_json("e2e_woningmodel.json", result.woningmodel.model_dump())
    _write_debug_json("e2e_measure_overview.json", result.measure_overview.model_dump())

    assert result.final_report is not None
    assert result.final_report.current_label
    assert result.final_report.new_label
    assert result.final_report.new_ep2_kwh_m2 is not None
    assert result.scenario_advice.scenario_id
    assert result.final_report.poc_disclaimer

    total_elapsed = time.monotonic() - suite_started
    print(f"[TIMING] total_live_e2e: {total_elapsed:.2f}s")
    print(f"[TIMING] details: {json.dumps(timings, ensure_ascii=False, indent=2)}")
    assert total_elapsed <= total_budget, (
        f"Live e2e pipeline exceeded total budget of {total_budget}s "
        f"(actual: {total_elapsed:.2f}s). "
        "Increase LIVE_GEMINI_TOTAL_BUDGET_SECONDS when needed."
    )
