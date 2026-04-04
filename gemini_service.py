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
from google.genai import types

from prompts import (
    SYSTEM_INSTRUCTION_BASELINE,
    build_extract_report_prompt,
    build_measure_gap_prompt,
    build_scenario_advice_prompt,
)
from schemas import Constraints, MeasureOverview, MeasureStatus, ScenarioAdvice, WoningModel
from services.config_service import get_label_boundaries, get_scenario_templates, get_trias_structure, get_woning_schema
from services.config_service import get_measures_library
from services.extraction_service import extract_woningmodel_from_payload

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


def _generate_json(*, model: str, contents: list[Any], context_name: str, tools: list[Any] | None = None) -> Any:
    client = _get_gemini_client()
    config: dict[str, Any] = {"system_instruction": SYSTEM_INSTRUCTION_BASELINE}
    if tools:
        config["tools"] = tools
    response = client.models.generate_content(model=model, contents=contents, config=config)

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError(f"{context_name} returned an empty response.")

    return _parse_llm_json(raw_text, context_name)


def extract_woningmodel_data(uploaded_file: Any) -> WoningModel:
    payload = _generate_json(
        model=_get_extract_model(),
        contents=[uploaded_file, build_extract_report_prompt(get_woning_schema())],
        context_name="Gemini woningmodel extraction",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_llm_json: Gemini woningmodel extraction payload should be an object.")
    return extract_woningmodel_from_payload(payload)


def _normalize_measure_gap_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    normalized = dict(raw)
    for key in ("measure_id", "canonical_name", "status", "reason"):
        if normalized.get(key) is None:
            normalized[key] = ""

    status = str(normalized.get("status", "")).strip().lower()
    if status not in {"missing", "improvable", "sufficient", "not_applicable", "capacity_limited"}:
        status = "missing"
    normalized["status"] = status

    if not isinstance(normalized.get("evidence_fields"), list):
        normalized["evidence_fields"] = []
    if not isinstance(normalized.get("current_values_snapshot"), dict):
        normalized["current_values_snapshot"] = {}
    if not isinstance(normalized.get("assumptions"), list):
        normalized["assumptions"] = []
    if not isinstance(normalized.get("uncertainties"), list):
        normalized["uncertainties"] = []

    gap_delta = normalized.get("gap_delta")
    if gap_delta is not None:
        try:
            normalized["gap_delta"] = float(gap_delta)
        except (TypeError, ValueError):
            normalized["gap_delta"] = None

    return normalized


def _normalize_measure_gap_payload(raw: dict[str, Any]) -> dict[str, Any]:
    missing_raw = raw.get("missing")
    improvable_raw = raw.get("improvable")
    combined_raw = raw.get("combined")

    def _normalize_collection(values: Any) -> list[dict[str, Any]]:
        if not isinstance(values, list):
            return []
        result: list[dict[str, Any]] = []
        for item in values:
            normalized_item = _normalize_measure_gap_item(item)
            if normalized_item is not None:
                result.append(normalized_item)
        return result

    missing = _normalize_collection(missing_raw)
    improvable = _normalize_collection(improvable_raw)
    combined = _normalize_collection(combined_raw)

    if not combined:
        combined = [*missing, *improvable]

    return {
        "missing": missing,
        "improvable": improvable,
        "combined": combined,
    }


def get_measure_gap_analysis_with_gemini(
    *,
    woningmodel: WoningModel,
    file_search_store: str | None = None,
) -> tuple[list[MeasureStatus], MeasureOverview]:
    input_payload = {
        "woningmodel": woningmodel.model_dump(),
        "relevante_woninginformatie": {
            "woning": woningmodel.woning.model_dump(),
            "prestatie": woningmodel.prestatie.model_dump(),
            "bouwdelen": woningmodel.bouwdelen.model_dump(),
            "installaties": woningmodel.installaties.model_dump(),
            "huidige_maatregelen_samenvatting": woningmodel.samenvatting_huidige_maatregelen,
            "huidige_maatregelen_gestructureerd": [m.model_dump() for m in woningmodel.maatregelen],
        },
        "maatregelenbibliotheek": get_measures_library().get("measures", []),
    }

    tools = None
    if file_search_store:
        tools = [
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[file_search_store]
                )
            )
        ]
        input_payload["file_search_store"] = file_search_store

    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(input_payload, ensure_ascii=False), build_measure_gap_prompt()],
        context_name="Gemini measure gap analysis",
        tools=tools,
    )

    if not isinstance(raw, dict):
        raise RuntimeError("invalid_llm_json: Measure gap analysis response should be an object.")

    normalized = _normalize_measure_gap_payload(raw)
    overview = MeasureOverview.model_validate(normalized)
    statuses = [*overview.missing, *overview.improvable]
    return statuses, overview




def _normalize_scenario_advice_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {
        "scenario_id",
        "scenario_name",
        "expected_label",
        "expected_ep2_kwh_m2",
        "selected_measures",
        "logical_order",
        "total_investment_eur",
        "monthly_savings_eur",
        "expected_property_value_gain_eur",
        "motivation",
        "assumptions",
        "uncertainties",
        "methodiek_bronnen",
    }
    normalized = {key: value for key, value in raw.items() if key in allowed_fields}

    def _normalize_measures(values: Any) -> list[str]:
        result: list[str] = []
        if not isinstance(values, list):
            return result
        for item in values:
            if isinstance(item, str):
                v = item.strip()
                if v:
                    result.append(v)
                continue
            if isinstance(item, dict):
                for key in ("measure_id", "id", "name", "canonical_name"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        result.append(value.strip())
                        break
        return result

    if "selected_measures" in normalized:
        normalized["selected_measures"] = _normalize_measures(normalized.get("selected_measures"))
    if "logical_order" in normalized:
        normalized["logical_order"] = _normalize_measures(normalized.get("logical_order"))

    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace(",", ".").strip()
            return float(value)
        except (TypeError, ValueError):
            return None

    def _estimate_measure_investment(measure: dict[str, Any]) -> float:
        per_unit = _safe_float(measure.get("investment_per_unit_eur"))
        if per_unit is not None and per_unit > 0:
            return round(per_unit, 2)

        bandwidth = measure.get("investment_bandwidth_eur", {})
        low = _safe_float(bandwidth.get("min"))
        high = _safe_float(bandwidth.get("max"))
        if low is not None and high is not None and low > 0 and high > 0:
            return round((low + high) / 2.0, 2)

        return 0.0

    selected_measures = normalized.get("selected_measures") or []
    provided_total = _safe_float(normalized.get("total_investment_eur"))
    if isinstance(selected_measures, list) and selected_measures and (provided_total is None or provided_total <= 0.0):
        library = get_measures_library().get("measures", [])
        measure_index = {
            str(measure.get("id", "")).strip(): measure
            for measure in library
            if isinstance(measure, dict) and str(measure.get("id", "")).strip()
        }

        fallback_total = 0.0
        fallback_uncertainties: list[str] = []
        for measure_id in selected_measures:
            measure = measure_index.get(str(measure_id).strip())
            if not measure:
                fallback_uncertainties.append(
                    f"Maatregel '{measure_id}' ontbreekt in maatregelenbibliotheek; investering niet meegerekend."
                )
                continue
            estimated = _estimate_measure_investment(measure)
            fallback_total += estimated
            if estimated == 0.0:
                fallback_uncertainties.append(
                    f"Maatregel '{measure_id}' heeft geen bruikbare investment_per_unit_eur/investment_bandwidth_eur in de bibliotheek."
                )

        normalized["total_investment_eur"] = round(fallback_total, 2)

        assumptions = normalized.get("assumptions")
        if not isinstance(assumptions, list):
            assumptions = []
        assumptions.append(
            "total_investment_eur is deterministisch afgeleid uit maatregelenbibliotheek (POC-fallback) omdat Gemini geen bruikbare investeringswaarde gaf."
        )
        normalized["assumptions"] = assumptions

        uncertainties = normalized.get("uncertainties")
        if not isinstance(uncertainties, list):
            uncertainties = []
        uncertainties.extend(fallback_uncertainties)
        normalized["uncertainties"] = uncertainties

    for key in ("total_investment_eur", "monthly_savings_eur", "expected_property_value_gain_eur"):
        value = normalized.get(key)
        if value is None:
            normalized[key] = 0.0

    if normalized.get("expected_ep2_kwh_m2") is None:
        label = normalized.get("expected_label")
        boundaries = get_label_boundaries().get("boundaries", [])
        normalized_label = str(label or "").strip().upper()
        fallback_ep2 = None
        for rule in boundaries:
            if str(rule.get("label", "")).upper() != normalized_label:
                continue
            min_v = rule.get("ep2_min_inclusive")
            max_v = rule.get("ep2_max_exclusive")
            if min_v is not None and max_v is not None:
                fallback_ep2 = float(min_v + (max_v - min_v) / 2.0)
            elif min_v is not None:
                fallback_ep2 = float(min_v + 10.0)
            elif max_v is not None:
                fallback_ep2 = max(float(max_v) - 10.0, 0.0)
            break
        normalized["expected_ep2_kwh_m2"] = fallback_ep2 if fallback_ep2 is not None else 0.0

    if not isinstance(normalized.get("motivation"), str) or not normalized["motivation"].strip():
        normalized["motivation"] = "Gemini-output bevatte geen geldige motivatie; fallback toegepast."

    return normalized


def get_scenario_advice_with_gemini(
    *,
    constraints: Constraints,
    woningmodel: WoningModel,
    measure_overview: MeasureOverview,
    file_search_store: str | None = None,
) -> ScenarioAdvice:
    input_payload = {
        "constraints": constraints.model_dump(),
        "woningmodel": woningmodel.model_dump(),
        "measure_overview": measure_overview.model_dump(),
        "relevante_woninginformatie": {
            "woning": woningmodel.woning.model_dump(),
            "prestatie": woningmodel.prestatie.model_dump(),
            "bouwdelen": woningmodel.bouwdelen.model_dump(),
            "installaties": woningmodel.installaties.model_dump(),
        },
        "scenario_templates": get_scenario_templates().get("templates", []),
        "trias_structuur": get_trias_structure(),
    }

    tools = None
    if file_search_store:
        tools = [
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[file_search_store]
                )
            )
        ]
        input_payload["file_search_store"] = file_search_store

    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(input_payload, ensure_ascii=False), build_scenario_advice_prompt()],
        context_name="Gemini scenario advice",
        tools=tools,
    )

    if not isinstance(raw, dict):
        raise RuntimeError("invalid_llm_json: Scenario advice response should be an object.")

    return ScenarioAdvice.model_validate(_normalize_scenario_advice_payload(raw))
