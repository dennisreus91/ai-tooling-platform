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
from schemas import Constraints, ExtractedReport, OptimizationResult


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


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
        "GEMINI_METHOD_FILE_SEARCH_STORE": "stores/test-method-store",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_returns_optimization_result(mock_client_cls):
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Zonnepanelen", "cost": 3500, "score_gain": 15},
        ],
        notes=[],
    )
    constraints = Constraints(
        target_label="A",
        required_measures=["Dakisolatie"],
    )

    mock_response_payload = {
        "selected_measures": [
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen maatregel.",
            },
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Aanvullende kostenefficiënte maatregel.",
            },
        ],
        "total_cost": 7500,
        "score_increase": 35,
        "expected_label": "A",
        "resulting_score": 255,
        "summary": "Goedkoopste geldige combinatie richting label A.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    result = optimize_report(validated_report, constraints)

    assert result.expected_label == "A"
    assert result.total_cost == 7500
    assert len(result.selected_measures) == 2
    assert result.selected_measures[0].name == "Dakisolatie"

    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-opt-model"


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_raises_on_empty_response(mock_client_cls):
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[{"name": "Dakisolatie", "cost": 4000, "score_gain": 20}],
        notes=[],
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(text="")
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="empty response"):
        optimize_report(validated_report, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_raises_on_invalid_json(mock_client_cls):
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[{"name": "Dakisolatie", "cost": 4000, "score_gain": 20}],
        notes=[],
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(text="not-json")
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="valid JSON"):
        optimize_report(validated_report, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_OPTIMIZATION_MODEL": "gemini-opt-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_optimize_report_raises_on_invalid_schema(mock_client_cls):
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[{"name": "Dakisolatie", "cost": 4000, "score_gain": 20}],
        notes=[],
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(
            {
                "selected_measures": [],
                "total_cost": -1,
                "score_increase": 0,
                "expected_label": "",
                "resulting_score": 0,
            }
        )
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="invalid OptimizationResult"):
        optimize_report(validated_report, constraints)


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
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Zonnepanelen", "cost": 3500, "score_gain": 15},
        ],
        notes=[],
    )
    constraints = Constraints(
        target_label="A",
        required_measures=["Dakisolatie"],
    )

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
        "summary": "Goedkoopste maatregel.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="required_measures"):
        optimize_report(validated_report, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
        "GEMINI_METHOD_FILE_SEARCH_STORE": "stores/test-method-store",
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
            },
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Levert extra labelsprong op.",
            },
        ],
        total_cost=7500,
        score_increase=35,
        expected_label="A",
        resulting_score=255,
        summary="Goedkoopste geldige combinatie richting label A.",
    )
    constraints = Constraints(
        target_label="A",
        required_measures=["Dakisolatie"],
    )

    mock_response_payload = {
        "title": "Verduurzamingsadvies",
        "summary": "Met deze combinatie beweegt de woning richting label A.",
        "measures": [
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verlaagt warmtevraag sterk.",
            },
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Levert extra labelsprong op.",
            },
        ],
        "total_investment": 7500,
        "expected_label": "A",
        "rationale": "Dit scenario combineert verplichte en kostenefficiënte maatregelen.",
    }

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response_payload)
    )
    mock_client_cls.return_value = mock_client

    result = build_final_report(opt_result, constraints)

    assert result.title == "Verduurzamingsadvies"
    assert result.expected_label == "A"
    assert result.total_investment == 7500
    assert len(result.measures) == 2

    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-report-model"


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_raises_on_empty_response(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[],
        total_cost=0,
        score_increase=0,
        expected_label="B",
        resulting_score=190,
        summary="Geen maatregelen nodig.",
    )
    constraints = Constraints(target_label="B", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(text="")
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="empty response"):
        build_final_report(opt_result, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_raises_on_invalid_json(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[],
        total_cost=0,
        score_increase=0,
        expected_label="B",
        resulting_score=190,
        summary="Geen maatregelen nodig.",
    )
    constraints = Constraints(target_label="B", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(text="not-json")
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="valid JSON"):
        build_final_report(opt_result, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_raises_on_invalid_schema(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[],
        total_cost=0,
        score_increase=0,
        expected_label="B",
        resulting_score=190,
        summary="Geen maatregelen nodig.",
    )
    constraints = Constraints(target_label="B", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(
            {
                "title": "",
                "summary": "",
                "measures": [],
                "total_investment": -1,
                "expected_label": "",
                "rationale": "",
            }
        )
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="invalid FinalReport"):
        build_final_report(opt_result, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_raises_on_mismatched_expected_label(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[],
        total_cost=5000,
        score_increase=20,
        expected_label="A",
        resulting_score=210,
        summary="Scenario richting A.",
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(
            {
                "title": "Verduurzamingsadvies",
                "summary": "Samenvatting",
                "measures": [],
                "total_investment": 5000,
                "expected_label": "B",
                "rationale": "Onderbouwing",
            }
        )
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="expected_label"):
        build_final_report(opt_result, constraints)


@patch.dict(
    "os.environ",
    {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_REPORT_MODEL": "gemini-report-model",
    },
    clear=False,
)
@patch("gemini_service.genai.Client")
def test_build_final_report_raises_on_mismatched_total_investment(mock_client_cls):
    opt_result = OptimizationResult(
        selected_measures=[],
        total_cost=5000,
        score_increase=20,
        expected_label="A",
        resulting_score=210,
        summary="Scenario richting A.",
    )
    constraints = Constraints(target_label="A", required_measures=[])

    mock_client = Mock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(
            {
                "title": "Verduurzamingsadvies",
                "summary": "Samenvatting",
                "measures": [],
                "total_investment": 6500,
                "expected_label": "A",
                "rationale": "Onderbouwing",
            }
        )
    )
    mock_client_cls.return_value = mock_client

    with pytest.raises(RuntimeError, match="total_investment"):
        build_final_report(opt_result, constraints)
