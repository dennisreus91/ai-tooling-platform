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

from prompts import SYSTEM_INSTRUCTION_BASELINE, build_extract_report_prompt, build_scenario_advice_prompt
from schemas import Constraints, MeasureOverview, ScenarioAdvice, WoningModel
from services.config_service import get_label_boundaries, get_scenario_templates, get_trias_structure, get_woning_schema
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
