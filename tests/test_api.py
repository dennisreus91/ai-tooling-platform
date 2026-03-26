from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from schemas import Constraints, FinalReport, OptimizationResult


def test_run_poc_flow_rejects_missing_json_body():
    app = create_app()
    client = app.test_client()

    response = client.post("/run-poc-flow", data="not-json", content_type="text/plain")
    assert response.status_code == 400

    data = response.get_json()
    assert data["error"]["code"] == "invalid_json"


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
    mock_extract_report_data.return_value = SimpleNamespace(
        current_label="D",
        current_score=220,
        current_ep2_kwh_m2=260,
        measures=[],
        notes=[],
    )
    mock_validate_extract.return_value = mock_extract_report_data.return_value

    optimization_result = OptimizationResult(
        selected_measures=[
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen.",
            }
        ],
        total_cost=4000,
        score_increase=20,
        expected_label="A",
        resulting_score=240,
        expected_ep2_kwh_m2=180,
        monthly_savings_eur=85,
        expected_property_value_gain_eur=9000,
        calculation_notes=["Conservatieve inschatting."],
        summary="Scenario richting label A.",
    )
    final_report = FinalReport(
        title="Verduurzamingsadvies",
        summary="De woning kan met één maatregel richting label A bewegen.",
        measures=[
            {
                "name": "Dakisolatie",
                "cost": 4000,
                "score_gain": 20,
                "rationale": "Verplicht opgenomen.",
            }
        ],
        total_investment=4000,
        expected_label="A",
        expected_ep2_kwh_m2=180,
        monthly_savings_eur=85,
        expected_property_value_gain_eur=9000,
        rationale="Verplichte maatregel met aantoonbare labelsprong.",
    )

    mock_optimize_report.return_value = optimization_result
    mock_build_final_report.return_value = final_report

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "completed"
    assert data["data"]["constraints"]["target_label"] == "A"
    assert data["data"]["optimization_result"]["expected_ep2_kwh_m2"] == 180
    assert data["data"]["final_report"]["expected_property_value_gain_eur"] == 9000


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


def test_constraints_schema_still_supports_required_measures_list():
    constraints = Constraints(target_label="A", required_measures=["Dakisolatie"])
    assert constraints.required_measures == ["Dakisolatie"]
