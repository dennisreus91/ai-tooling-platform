import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from gemini_service import (
    download_file_to_temp,
    extract_report_data,
    upload_case_file,
)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
        "GEMINI_METHOD_FILE_SEARCH_STORE": "stores/test-method-store",
    },
    clear=False,
)
@patch("gemini_service.requests.get")
def test_download_file_to_temp(mock_get):
    mock_response = Mock()
    mock_response.content = b"fake-pdf-content"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    local_path = download_file_to_temp("https://example.com/report.pdf")

    assert local_path.endswith(".pdf")


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_upload_case_file(mock_client_cls, tmp_path):
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"fake-pdf-content")

    mock_client = Mock()
    mock_client.files.upload.return_value = SimpleNamespace(name="files/123")
    mock_client_cls.return_value = mock_client

    uploaded = upload_case_file(str(test_file))

    assert uploaded.name == "files/123"
    mock_client.files.upload.assert_called_once()


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
        "GEMINI_METHOD_FILE_SEARCH_STORE": "stores/test-method-store",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_extract_report_data_returns_extracted_report(mock_client_cls):
    mock_response_payload = {
        "current_label": "D",
        "current_score": 220,
        "measures": [
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "notes": "Indicatieve maatregel uit rapport.",
            }
        ],
        "notes": ["Extractie gebaseerd op aangeleverd bronbestand."],
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    uploaded_file = SimpleNamespace(name="files/123")

    result = extract_report_data(uploaded_file)

    assert result.current_label == "D"
    assert result.current_score == 220
    assert len(result.measures) == 1
    assert result.measures[0].name == "Dakisolatie"

    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-test-model"
    assert uploaded_file in call_kwargs["contents"]


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_extract_report_data_raises_on_empty_response(mock_client_cls):
    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(text="")
    mock_client_cls.return_value = mock_client

    uploaded_file = SimpleNamespace(name="files/123")

    with pytest.raises(RuntimeError, match="empty response"):
        extract_report_data(uploaded_file)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_extract_report_data_raises_on_invalid_json(mock_client_cls):
    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text="not-json"
    )
    mock_client_cls.return_value = mock_client

    uploaded_file = SimpleNamespace(name="files/123")

    with pytest.raises(RuntimeError, match="valid JSON"):
        extract_report_data(uploaded_file)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_extract_report_data_raises_on_invalid_schema(mock_client_cls):
    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(
            {
                "current_label": "",
                "current_score": -1,
                "measures": [],
                "notes": [],
            }
        )
    )
    mock_client_cls.return_value = mock_client

    uploaded_file = SimpleNamespace(name="files/123")

    with pytest.raises(RuntimeError, match="invalid ExtractedReport"):
        extract_report_data(uploaded_file)
