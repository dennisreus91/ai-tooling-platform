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

from prompts import SYSTEM_INSTRUCTION_BASELINE, build_extract_report_prompt
from schemas import ExtractedReport

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

    parsed = decode_start(raw_text.strip())
    if parsed is not None:
        return parsed

    fenced_blocks = re.findall(r"```(?:json)?\\s*(.*?)\\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    for block in fenced_blocks:
        parsed = decode_start(block.strip())
        if parsed is not None:
            return parsed

    raise RuntimeError(f"invalid_llm_json: {context} did not return valid JSON.")


def extract_report_data(uploaded_file: Any) -> ExtractedReport:
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=_get_extract_model(),
        contents=[uploaded_file, build_extract_report_prompt()],
        config={"system_instruction": SYSTEM_INSTRUCTION_BASELINE},
    )
    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Gemini extraction returned an empty response.")

    payload = _parse_llm_json(raw_text, "Gemini extraction")
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_llm_json: Gemini extraction payload should be an object.")

    payload.setdefault("current_label", "onbekend")
    payload.setdefault("current_score", float(payload.get("current_ep2_kwh_m2", 0) or 0))
    payload.setdefault("current_ep2_kwh_m2", 0)
    payload.setdefault("measures", [])
    payload.setdefault("notes", [])
    return ExtractedReport.model_validate(payload)
