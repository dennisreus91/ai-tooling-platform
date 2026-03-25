import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from gemini_service import (
    build_final_report,
    download_file_to_temp,
    extract_report_data,
    optimize_report,
    upload_case_file,
)
from schemas import Constraints, OptimizationResult


@patch("gemini_service.requests.get")
def test_download_file_to_temp(mock_get):
    mock_response = Mock()
    mock_response.content = b"fake-pdf-content"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    local_path = download_file_to_temp("https://example.com/report.pdf")

    assert local_path.endswith(".pdf")


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=False)
@patch("gemini_service.genai.Client")
def test_upload_case_file(mock_client_cls, tmp_path):
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"fake-pdf-content")

    mock_client = Mock()
    mock_client.files.upload.return_value = SimpleNamespace(name="files/123")
    mock_client_cls.return_value = mock_client

    uploaded = upload_case_file(str(test_file))

    assert uploaded.name == "files/123"


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-test-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_extract_report_data_returns_extracted_report(mock_client_cls):
    mock_response_payload = {
        "current_label": "D",
        "current_score": 220,
        "current_ep2_kwh_m2": 260,
        "measures": [],
        "notes": [],
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    uploaded_file = SimpleNamespace(name="files/123")

    result = extract_report_data(uploaded_file)

    assert result.current_label == "D"
    assert result.current_ep2_kwh_m2 == 260


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_returns_optimization_result(mock_client_cls):
    uploaded_file = SimpleNamespace(name="files/123")
    constraints = Constraints(target_label="A", required_measures=["Dakisolatie"])

    mock_response_payload = {
        "selected_measures": [
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen maatregel.",
            }
        ],
        "total_cost": 4000,
        "score_increase": 20,
        "expected_label": "A",
        "resulting_score": 240,
        "expected_ep2_kwh_m2": 180,
        "monthly_savings_eur": 85,
        "expected_property_value_gain_eur": 9000,
        "calculation_notes": ["Conservatieve methodiekschatting."],
        "summary": "Scenario richting label A.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    result = optimize_report(uploaded_file, constraints)

    assert result.expected_label == "A"
    assert result.expected_ep2_kwh_m2 == 180


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_raises_when_required_measure_missing(mock_client_cls):
    uploaded_file = SimpleNamespace(name="files/123")
    constraints = Constraints(target_label="A", required_measures=["Dakisolatie"])

    mock_response_payload = {
        "selected_measures": [
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Goedkoopste losse maatregel.",
            }
        ],
        "total_cost": 3500,
        "score_increase": 15,
        "expected_label": "B",
        "resulting_score": 235,
        "expected_ep2_kwh_m2": 210,
        "monthly_savings_eur": 70,
        "expected_property_value_gain_eur": 6000,
        "calculation_notes": ["Onvoldoende voor label A."],
        "summary": "Goedkoopste maatregel.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="insufficient_measures"):
        optimize_report(uploaded_file, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_returns_final_report(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verlaagt warmtevraag sterk.",
            }
        ],
        total_cost=4000,
        score_increase=20,
        expected_label="A",
        resulting_score=240,
        expected_ep2_kwh_m2=180,
        monthly_savings_eur=85,
        expected_property_value_gain_eur=9000,
        calculation_notes=["Conservatief."],
        summary="Scenario richting A.",
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_response_payload = {
        "title": "Verduurzamingsadvies",
        "summary": "Met deze combinatie beweegt de woning richting label A.",
        "measures": [
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verlaagt warmtevraag sterk.",
            }
        ],
        "total_investment": 4000,
        "expected_label": "A",
        "expected_ep2_kwh_m2": 180,
        "monthly_savings_eur": 85,
        "expected_property_value_gain_eur": 9000,
        "rationale": "Dit scenario combineert verplichte en kostenefficiënte maatregelen.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    result = build_final_report(opt_result, constraints)

    assert result.expected_ep2_kwh_m2 == 180
    assert result.monthly_savings_eur == 85
