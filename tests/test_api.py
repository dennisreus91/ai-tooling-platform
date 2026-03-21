from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from schemas import Constraints, ExtractedReport, FinalReport, OptimizationResult


def test_run_poc_flow_rejects_missing_json_body():
    app = create_app()
    client = app.test_client()

    response = client.post("/run-poc-flow", data="not-json", content_type="text/plain")
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] == "invalid_json"


def test_run_poc_flow_rejects_invalid_target_label():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "D",
        "required_measures": ["isolatie"],
        "file_url": "https://example.com/report.pdf",
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] in {"validation_error", "constraint_error"}


def test_run_poc_flow_rejects_missing_required_field():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "A",
        "required_measures": ["isolatie"],
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


def test_run_poc_flow_rejects_invalid_file_url():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "A",
        "required_measures": ["isolatie"],
        "file_url": "not-a-url",
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


def test_run_poc_flow_rejects_extra_fields():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "A",
        "required_measures": ["isolatie"],
        "file_url": "https://example.com/report.pdf",
        "unexpected": "value",
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


@patch("app.build_final_report")
@patch("app.optimize_report")
@patch("app.validate_extract")
@patch("app.extract_report_data")
@patch("app.upload_case_file")
@patch("app.download_file_to_temp")
def test_run_poc_flow_completes_successfully(
    mock_download_file_to_temp,
    mock_upload_case_file,
    mock_extract_report_data,
    mock_validate_extract,
    mock_optimize_report,
    mock_build_final_report,
):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "a",
        "required_measures": ["Dakisolatie"],
        "file_url": "https://example.com/report.pdf",
    }

    mock_download_file_to_temp.return_value = "/tmp/report.pdf"
    mock_upload_case_file.return_value = SimpleNamespace(name="files/123")

    extracted_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Zonnepanelen", "cost": 3500, "score_gain": 15},
        ],
        notes=["Extractie gelukt."],
    )
    validated_report = ExtractedReport(
        current_label="D",
        current_score=220,
        measures=[
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Zonnepanelen", "cost": 3500, "score_gain": 15},
        ],
        notes=["Extractie gelukt."],
    )
    optimization_result = OptimizationResult(
        selected_measures=[
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen.",
            },
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Kostenefficiënte aanvulling.",
            },
        ],
        total_cost=7500,
        score_increase=35,
        expected_label="A",
        resulting_score=255,
        summary="Goedkoopste geldige combinatie richting label A.",
    )
    final_report = FinalReport(
        title="Verduurzamingsadvies",
        summary="De woning kan met twee maatregelen richting label A bewegen.",
        measures=[
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen.",
            },
            {
                "name": "Zonnepanelen",
                "cost": 3500,
                "score_gain": 15,
                "rationale": "Kostenefficiënte aanvulling.",
            },
        ],
        total_investment=7500,
        expected_label="A",
        rationale="De gekozen combinatie combineert verplichte opname en kostenefficiëntie.",
    )

    mock_extract_report_data.return_value = extracted_report
    mock_validate_extract.return_value = validated_report
    mock_optimize_report.return_value = optimization_result
    mock_build_final_report.return_value = final_report

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "completed"
    assert data["data"]["user_id"] == "user-123"
    assert data["data"]["constraints"]["target_label"] == "A"
    assert data["data"]["constraints"]["required_measures"] == ["Dakisolatie"]
    assert data["data"]["validated_report"]["current_label"] == "D"
    assert data["data"]["optimization_result"]["expected_label"] == "A"
    assert data["data"]["final_report"]["title"] == "Verduurzamingsadvies"

    mock_download_file_to_temp.assert_called_once_with("https://example.com/report.pdf")
    mock_upload_case_file.assert_called_once_with("/tmp/report.pdf")
    mock_extract_report_data.assert_called_once()
    mock_validate_extract.assert_called_once()
    mock_optimize_report.assert_called_once()
    mock_build_final_report.assert_called_once()


@patch("app.download_file_to_temp")
def test_run_poc_flow_returns_processing_error_on_runtime_error(
    mock_download_file_to_temp,
):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "A",
        "required_measures": ["Dakisolatie"],
        "file_url": "https://example.com/report.pdf",
    }

    mock_download_file_to_temp.side_effect = RuntimeError("Download failed.")

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 500

    data = response.get_json()
    assert data["error"]["code"] == "processing_error"
    assert data["error"]["message"] == "Download failed."


@patch("app.download_file_to_temp")
def test_run_poc_flow_returns_unexpected_error_on_unknown_exception(
    mock_download_file_to_temp,
):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "A",
        "required_measures": ["Dakisolatie"],
        "file_url": "https://example.com/report.pdf",
    }

    mock_download_file_to_temp.side_effect = Exception("Boom")

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 500

    data = response.get_json()
    assert data["error"]["code"] == "unexpected_error"
    assert "Unexpected error during POC flow" in data["error"]["message"]
