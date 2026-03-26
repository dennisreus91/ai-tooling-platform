import json
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import requests
from google import genai
from google.genai import types

from prompts import (
    SYSTEM_INSTRUCTION_BASELINE,
    build_extract_report_prompt,
    build_final_report_prompt,
    build_optimize_report_prompt,
)
from schemas import (
    Constraints,
    ExtractedReport,
    FinalReport,
    OptimizationResult,
)


DEFAULT_TIMEOUT_SECONDS = 60


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_gemini_client() -> genai.Client:
    api_key = _get_required_env("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def _get_extract_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _get_optimize_model() -> str:
    return os.getenv("GEMINI_OPTIMIZATION_MODEL", _get_extract_model())


def _get_report_model() -> str:
    return os.getenv("GEMINI_REPORT_MODEL", _get_optimize_model())


def _get_methodology_store_name() -> str | None:
    return os.getenv("GEMINI_METHOD_FILE_SEARCH_STORE")


def _guess_mime_type(file_path: str) -> str | None:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def download_file_to_temp(file_url: str) -> str:
    """
    Download a remote file to a temporary local path.

    Returns the absolute path to the downloaded file.
    """
    response = requests.get(file_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()

    suffix = Path(file_url).suffix or ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(response.content)
        return temp_file.name


def upload_case_file(local_path: str) -> Any:
    """
    Upload a local case file to the Gemini Files API.

    Returns the uploaded file object from the SDK.
    """
    client = _get_gemini_client()
    mime_type = _guess_mime_type(local_path)

    if mime_type:
        return client.files.upload(file=local_path, config={"mime_type": mime_type})

    return client.files.upload(file=local_path)


def _build_file_search_tools() -> list[types.Tool] | None:
    store_name = _get_methodology_store_name()
    if not store_name:
        return None

    return [
        types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=[store_name],
            )
        )
    ]


def _build_extract_config() -> types.GenerateContentConfig:
    tools = _build_file_search_tools()
    if tools:
        return types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_INSTRUCTION_BASELINE,
        )

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=ExtractedReport.model_json_schema(),
        system_instruction=SYSTEM_INSTRUCTION_BASELINE,
    )


def _build_optimize_config() -> types.GenerateContentConfig:
    tools = _build_file_search_tools()
    if tools:
        return types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_INSTRUCTION_BASELINE,
        )

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=OptimizationResult.model_json_schema(),
        system_instruction=SYSTEM_INSTRUCTION_BASELINE,
    )


def _build_final_report_config() -> types.GenerateContentConfig:
    tools = _build_file_search_tools()
    if tools:
        return types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_INSTRUCTION_BASELINE,
        )

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=FinalReport.model_json_schema(),
        system_instruction=SYSTEM_INSTRUCTION_BASELINE,
    )


def extract_report_data(uploaded_file: Any) -> ExtractedReport:
    """
    Extract structured report data from an uploaded Gemini file.

    The uploaded file is expected to come from upload_case_file().
    """
    client = _get_gemini_client()
    model = _get_extract_model()

    response = client.models.generate_content(
        model=model,
        contents=[uploaded_file, build_extract_report_prompt()],
        config=_build_extract_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini extraction returned an empty response.")

    payload = _parse_llm_json(raw_text, "Gemini extraction")
    payload = _normalize_extracted_report_payload(payload)

    try:
        return ExtractedReport.model_validate(payload)
    except Exception as exc:
        raise RuntimeError("Gemini extraction returned invalid ExtractedReport data.") from exc


def _normalize_extracted_report_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {
        "current_label": str(payload.get("current_label", "")).strip(),
        "current_score": _coerce_float(payload.get("current_score")),
        "current_ep2_kwh_m2": _coerce_float(payload.get("current_ep2_kwh_m2")),
        "measures": [],
        "notes": [],
    }

    raw_measures = payload.get("measures")
    if isinstance(raw_measures, list):
        cleaned_measures: list[dict[str, Any]] = []
        for raw_measure in raw_measures:
            if not isinstance(raw_measure, dict):
                continue

            name = str(raw_measure.get("name", "")).strip()
            cost = _coerce_float(raw_measure.get("cost"))
            score_gain = _coerce_float(raw_measure.get("score_gain"))

            if not name or cost is None or score_gain is None:
                continue

            measure: dict[str, Any] = {
                "name": name,
                "cost": cost,
                "score_gain": score_gain,
            }

            notes = raw_measure.get("notes")
            if isinstance(notes, str) and notes.strip():
                measure["notes"] = notes.strip()

            cleaned_measures.append(measure)

        normalized["measures"] = cleaned_measures

    raw_notes = payload.get("notes")
    if isinstance(raw_notes, list):
        normalized["notes"] = [str(item).strip() for item in raw_notes if str(item).strip()]
    elif isinstance(raw_notes, str) and raw_notes.strip():
        normalized["notes"] = [raw_notes.strip()]

    return normalized


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def optimize_report(
    uploaded_file: Any,
    constraints: Constraints,
    extracted_report: ExtractedReport,
) -> OptimizationResult:
    """
    Optimize a case file directly into a structured scenario result.
    """
    client = _get_gemini_client()
    model = _get_optimize_model()

    optimization_input = {
        "constraints": constraints.model_dump(),
        "extracted_report": extracted_report.model_dump(),
    }

    response = client.models.generate_content(
        model=model,
        contents=[
            uploaded_file,
            build_optimize_report_prompt(),
            json.dumps(optimization_input, ensure_ascii=False, indent=2),
        ],
        config=_build_optimize_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini optimization returned an empty response.")

    payload = _parse_llm_json(raw_text, "Gemini optimization")

    try:
        result = OptimizationResult.model_validate(payload)
    except Exception:
        result = _build_conservative_optimization_result(payload, constraints)

    selected_names = {m.name.strip().lower() for m in result.selected_measures}
    missing_required = [
        measure
        for measure in constraints.required_measures
        if measure.strip().lower() not in selected_names
    ]

    if missing_required:
        raise RuntimeError(
            "insufficient_measures: Gemini optimization did not include all required_measures: "
            + ", ".join(missing_required)
        )

    selected_total_cost = sum(measure.cost for measure in result.selected_measures)
    if abs(selected_total_cost - result.total_cost) > 1e-6:
        raise RuntimeError(
            "methodology_conflict: total_cost does not match the sum of selected_measures."
        )

    if constraints.target_label != "next_step":
        if not _is_label_achieved(result.expected_label, constraints.target_label):
            raise RuntimeError(
                "methodology_conflict: optimization expected_label does not achieve target_label."
            )

    return result


def _is_label_achieved(expected_label: str, target_label: str) -> bool:
    expected_rank = _label_rank(expected_label)
    target_rank = _label_rank(target_label)

    if expected_rank is None or target_rank is None:
        return False

    return expected_rank <= target_rank


def _label_rank(label: str) -> int | None:
    value = label.strip().upper()
    if not value:
        return None

    first = value[0]
    ranking = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
    }
    return ranking.get(first)


def build_final_report(
    opt_result: OptimizationResult,
    constraints: Constraints,
) -> FinalReport:
    """
    Build a structured final report from the optimization result.
    """
    client = _get_gemini_client()
    model = _get_report_model()

    report_input = {
        "constraints": constraints.model_dump(),
        "optimization_result": opt_result.model_dump(),
    }

    response = client.models.generate_content(
        model=model,
        contents=[
            build_final_report_prompt(),
            json.dumps(report_input, ensure_ascii=False, indent=2),
        ],
        config=_build_final_report_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini final report generation returned an empty response.")

    payload = _parse_llm_json(raw_text, "Gemini final report generation")

    try:
        result = FinalReport.model_validate(payload)
    except Exception as exc:
        raise RuntimeError("Gemini final report generation returned invalid FinalReport data.") from exc

    if result.expected_label.strip() != opt_result.expected_label.strip():
        raise RuntimeError(
            "Gemini final report generation returned an expected_label that does not match the optimization result."
        )

    if abs(result.total_investment - opt_result.total_cost) > 1e-6:
        raise RuntimeError(
            "Gemini final report generation returned a total_investment that does not match the optimization result."
        )

    if abs(result.expected_ep2_kwh_m2 - opt_result.expected_ep2_kwh_m2) > 1e-6:
        raise RuntimeError(
            "Gemini final report generation returned an expected_ep2_kwh_m2 that does not match the optimization result."
        )

    if abs(result.monthly_savings_eur - opt_result.monthly_savings_eur) > 1e-6:
        raise RuntimeError(
            "Gemini final report generation returned a monthly_savings_eur that does not match the optimization result."
        )

    if (
        abs(
            result.expected_property_value_gain_eur
            - opt_result.expected_property_value_gain_eur
        )
        > 1e-6
    ):
        raise RuntimeError(
            "Gemini final report generation returned an expected_property_value_gain_eur that does not match the optimization result."
        )

    return result


def _parse_llm_json(raw_text: str, context: str) -> Any:
    """
    Parse LLM output as JSON, with a conservative fallback for fenced JSON blocks.
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", raw_text, re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    json_like_match = re.search(r"(\{.*\}|\[.*\])", raw_text, re.DOTALL)
    if json_like_match:
        candidate = json_like_match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"{context} did not return valid JSON.")


def _build_conservative_optimization_result(
    payload: dict[str, Any],
    constraints: Constraints,
) -> OptimizationResult:
    """
    Build a conservative OptimizationResult when LLM output is parseable JSON
    but does not match the expected schema.
    """
    raw_measures = payload.get("selected_measures") if isinstance(payload, dict) else None
    selected_measures: list[dict[str, Any]] = []

    if isinstance(raw_measures, list):
        for raw_measure in raw_measures:
            if not isinstance(raw_measure, dict):
                continue

            name = str(raw_measure.get("name", "")).strip()
            cost = raw_measure.get("cost")
            score_gain = raw_measure.get("score_gain")

            if not name:
                continue
            if not isinstance(cost, (int, float)) or cost < 0:
                continue
            if not isinstance(score_gain, (int, float)) or score_gain <= 0:
                continue

            selected_measures.append(
                {
                    "name": name,
                    "cost": float(cost),
                    "score_gain": float(score_gain),
                    "rationale": raw_measure.get("rationale"),
                }
            )

    notes: list[str] = []
    raw_notes = payload.get("calculation_notes") if isinstance(payload, dict) else None
    if isinstance(raw_notes, list):
        notes.extend(str(item) for item in raw_notes if str(item).strip())
    elif isinstance(raw_notes, str) and raw_notes.strip():
        notes.append(raw_notes)

    notes.append(
        "Conservatieve fallback toegepast: optimization-output was niet volledig schema-conform."
    )

    total_cost = payload.get("total_cost") if isinstance(payload, dict) else None
    score_increase = payload.get("score_increase") if isinstance(payload, dict) else None
    resulting_score = payload.get("resulting_score") if isinstance(payload, dict) else None
    expected_ep2_kwh_m2 = payload.get("expected_ep2_kwh_m2") if isinstance(payload, dict) else None
    monthly_savings_eur = (
        payload.get("monthly_savings_eur") if isinstance(payload, dict) else None
    )
    expected_property_value_gain_eur = (
        payload.get("expected_property_value_gain_eur") if isinstance(payload, dict) else None
    )

    raw_expected_label = payload.get("expected_label") if isinstance(payload, dict) else None

    return OptimizationResult.model_validate(
        {
            "selected_measures": selected_measures,
            "total_cost": float(total_cost)
            if isinstance(total_cost, (int, float)) and total_cost >= 0
            else 0.0,
            "score_increase": float(score_increase)
            if isinstance(score_increase, (int, float)) and score_increase >= 0
            else 0.0,
            "expected_label": raw_expected_label.strip()
            if isinstance(raw_expected_label, str) and raw_expected_label.strip()
            else constraints.target_label,
            "resulting_score": float(resulting_score)
            if isinstance(resulting_score, (int, float)) and resulting_score >= 0
            else 0.0,
            "expected_ep2_kwh_m2": float(expected_ep2_kwh_m2)
            if isinstance(expected_ep2_kwh_m2, (int, float)) and expected_ep2_kwh_m2 >= 0
            else 0.0,
            "monthly_savings_eur": float(monthly_savings_eur)
            if isinstance(monthly_savings_eur, (int, float)) and monthly_savings_eur >= 0
            else 0.0,
            "expected_property_value_gain_eur": float(expected_property_value_gain_eur)
            if isinstance(expected_property_value_gain_eur, (int, float))
            and expected_property_value_gain_eur >= 0
            else 0.0,
            "calculation_notes": notes,
            "summary": payload.get("summary")
            if isinstance(payload, dict) and isinstance(payload.get("summary"), str)
            else "Conservatief scenario op basis van beperkte, onvolledige optimalisatie-output.",
        }
    )
