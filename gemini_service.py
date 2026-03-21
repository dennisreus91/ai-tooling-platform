import json
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any

import requests
from google import genai
from google.genai import types

from prompts import EXTRACT_REPORT_PROMPT
from schemas import ExtractedReport


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


def _build_generate_config() -> types.GenerateContentConfig:
    store_name = _get_methodology_store_name()

    tools: list[types.Tool] = []
    if store_name:
        tools.append(
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_name],
                )
            )
        )

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ExtractedReport,
        tools=tools or None,
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
        config=_build_generate_config(),
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
