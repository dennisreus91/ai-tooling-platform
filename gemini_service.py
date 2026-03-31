from __future__ import annotations

import json
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import requests
from google import genai

from services.extraction_service import extract_woningmodel_from_payload
from prompts import (
    SYSTEM_INSTRUCTION_BASELINE,
    build_extract_report_prompt,
    build_final_report_prompt,
    build_measure_impact_prompt,
    build_optimize_report_prompt,
)
from schemas import (
    ChosenScenario,
    ExtractedReport,
    FinalReport,
    MeasureImpact,
    MeasureStatus,
    ScenarioDefinition,
    ScenarioResult,
    WoningModel,
)
from validators import validate_woningmodel


DEFAULT_TIMEOUT_SECONDS = 60


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=_get_required_env("GEMINI_API_KEY"))


def _get_extract_model() -> str:
    return os.getenv("GEMINI_EXTRACTION_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def _get_scenario_model() -> str:
    return os.getenv("GEMINI_SCENARIO_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def _get_report_model() -> str:
    return os.getenv("GEMINI_REPORT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def _guess_mime_type(file_path: str) -> str | None:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def download_file_to_temp(file_url: str) -> str:
    response = requests.get(file_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()

    suffix = Path(file_url).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(response.content)
        return temp_file.name


def upload_case_file(local_path: str) -> Any:
    client = _get_gemini_client()
    mime_type = _guess_mime_type(local_path)
    if mime_type:
        return client.files.upload(file=local_path, config={"mime_type": mime_type})
    return client.files.upload(file=local_path)


def _parse_llm_json(raw_text: str, context: str) -> Any:
    decoder = json.JSONDecoder()

    def decode_start(text: str) -> Any | None:
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
                return value
            except json.JSONDecodeError:
                continue
        return None

    stripped = raw_text.strip()
    parsed = decode_start(stripped)
    if parsed is not None:
        return parsed

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    for block in fenced_blocks:
        parsed = decode_start(block.strip())
        if parsed is not None:
            return parsed

    raise RuntimeError(f"invalid_llm_json: {context} did not return valid JSON.")


def _generate_json(
    *,
    model: str,
    contents: list[Any],
    context_name: str,
) -> Any:
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={"system_instruction": SYSTEM_INSTRUCTION_BASELINE},
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError(f"{context_name} returned an empty response.")

    return _parse_llm_json(raw_text, context_name)


# -------------------------------------------------------------------
# Extractie
# -------------------------------------------------------------------

def extract_woningmodel_data(uploaded_file: Any) -> WoningModel:
    """
    Voer Vabi/PDF-extractie uit via Gemini en zet de output daarna om
    naar een null-safe WoningModel.
    """
    payload = _generate_json(
        model=_get_extract_model(),
        contents=[uploaded_file, build_extract_report_prompt()],
        context_name="Gemini woningmodel extraction",
    )

    if not isinstance(payload, dict):
        raise RuntimeError("invalid_llm_json: Gemini woningmodel extraction payload should be an object.")

    woningmodel = extract_woningmodel_from_payload(payload)
    return validate_woningmodel(woningmodel)


def extract_report_data(uploaded_file: Any) -> ExtractedReport:
    """
    Legacy / compatibility helper.
    Zet Gemini extractie om naar het oudere ExtractedReport-model waar nodig.
    Gebruik voor de nieuwe flow bij voorkeur extract_woningmodel_data().
    """
    woningmodel = extract_woningmodel_data(uploaded_file)

    current_ep2 = woningmodel.prestatie.current_ep2_kwh_m2
    current_label = woningmodel.prestatie.current_label

    if current_ep2 is None:
        raise RuntimeError("missing_ep2_data: current_ep2_kwh_m2 ontbreekt of is ongeldig voor legacy ExtractedReport.")
    if current_label is None:
        current_label = "ONBEKEND"

    return ExtractedReport(
        current_label=current_label,
        current_score=float(current_ep2),
        current_ep2_kwh_m2=float(current_ep2),
        measures=[],
        notes=[
            "Legacy ExtractedReport opgebouwd vanuit WoningModel-extractie.",
            *woningmodel.extractie_meta.assumptions,
            *woningmodel.extractie_meta.uncertainties,
        ],
    )


# -------------------------------------------------------------------
# Optionele Gemini helpers voor latere uitbreidingen binnen de POC
# -------------------------------------------------------------------

def screen_measure_impacts_with_gemini(statuses: list[MeasureStatus]) -> list[MeasureImpact]:
    """
    Optionele Gemini-gebaseerde maatregelimpactscreening.
    Deze functie kan later gebruikt worden wanneer de POC expliciet
    Gemini wil inzetten voor deze stap.
    """
    payload = [status.model_dump() for status in statuses]
    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(payload, ensure_ascii=False), build_measure_impact_prompt()],
        context_name="Gemini measure impact screening",
    )

    if not isinstance(raw, list):
        raise RuntimeError("invalid_llm_json: Measure impact response should be a list.")

    return [MeasureImpact.model_validate(item) for item in raw]


def build_scenarios_with_gemini(impacts: list[MeasureImpact]) -> list[ScenarioDefinition]:
    """
    Optionele Gemini-gebaseerde scenario-opbouw.
    Deze functie is niet verplicht voor de deterministische basisflow,
    maar kan later gebruikt worden als extra POC-laag.
    """
    payload = [impact.model_dump() for impact in impacts]
    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(payload, ensure_ascii=False), build_optimize_report_prompt()],
        context_name="Gemini scenario build",
    )

    if not isinstance(raw, list):
        raise RuntimeError("invalid_llm_json: Scenario build response should be a list.")

    return [ScenarioDefinition.model_validate(item) for item in raw]


def build_final_report_with_gemini(
    current_label: str,
    current_ep2: float,
    chosen: ChosenScenario,
    scenario_result: ScenarioResult,
) -> FinalReport:
    """
    Optionele Gemini-gebaseerde rapportgeneratie.
    Gebruik alleen als je de rapportlaag via Gemini wilt laten formuleren,
    maar blijf schema-validatie afdwingen.
    """
    input_payload = {
        "current_label": current_label,
        "current_ep2_kwh_m2": current_ep2,
        "chosen_scenario": chosen.model_dump(),
        "scenario_result": scenario_result.model_dump(),
    }

    raw = _generate_json(
        model=_get_report_model(),
        contents=[json.dumps(input_payload, ensure_ascii=False), build_final_report_prompt()],
        context_name="Gemini final report build",
    )

    if not isinstance(raw, dict):
        raise RuntimeError("invalid_llm_json: Final report response should be an object.")

    return FinalReport.model_validate(raw)
