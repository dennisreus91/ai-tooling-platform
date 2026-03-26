import json
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any

import requests
from google import genai
from google.genai import types

from prompts import (
    BUILD_FINAL_REPORT_PROMPT,
    EXTRACT_REPORT_PROMPT,
    OPTIMIZE_REPORT_PROMPT,
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
        return types.GenerateContentConfig(tools=tools)

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=ExtractedReport.model_json_schema(),
    )


def _build_optimize_config() -> types.GenerateContentConfig:
    tools = _build_file_search_tools()
    if tools:
        return types.GenerateContentConfig(tools=tools)

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=OptimizationResult.model_json_schema(),
    )


def _build_final_report_config() -> types.GenerateContentConfig:
    tools = _build_file_search_tools()
    if tools:
        return types.GenerateContentConfig(tools=tools)

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=FinalReport.model_json_schema(),
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
        contents=[uploaded_file, EXTRACT_REPORT_PROMPT],
        config=_build_extract_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini extraction returned an empty response.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini extraction did not return valid JSON.") from exc

    try:
        return ExtractedReport.model_validate(payload)
    except Exception as exc:
        raise RuntimeError("Gemini extraction returned invalid ExtractedReport data.") from exc


def optimize_report(
    uploaded_file: Any,
    constraints: Constraints,
) -> OptimizationResult:
    """
    Optimize a case file directly into a structured scenario result.
    """
    client = _get_gemini_client()
    model = _get_optimize_model()

    optimization_input = {
        "constraints": constraints.model_dump(),
    }

    response = client.models.generate_content(
        model=model,
        contents=[
            uploaded_file,
            OPTIMIZE_REPORT_PROMPT,
            json.dumps(optimization_input, ensure_ascii=False, indent=2),
        ],
        config=_build_optimize_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini optimization returned an empty response.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini optimization did not return valid JSON.") from exc

    try:
        result = OptimizationResult.model_validate(payload)
    except Exception as exc:
        raise RuntimeError("Gemini optimization returned invalid OptimizationResult data.") from exc

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

    return result


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
            BUILD_FINAL_REPORT_PROMPT,
            json.dumps(report_input, ensure_ascii=False, indent=2),
        ],
        config=_build_final_report_config(),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini final report generation returned an empty response.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini final report generation did not return valid JSON.") from exc

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
