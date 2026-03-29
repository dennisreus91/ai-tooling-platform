from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


def test_run_poc_flow_rejects_missing_json_body():
    app = create_app()
    client = app.test_client()
    response = client.post("/run-poc-flow", data="not-json", content_type="text/plain")
    assert response.status_code == 400


@patch("app.run_poc_flow")
@patch("app.extract_report_data")
@patch("app.upload_case_file")
@patch("app.download_file_to_temp")
def test_run_poc_flow_completes_successfully(mock_download, mock_upload, mock_extract, mock_pipeline):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "u1",
        "target_label": "A",
        "required_measures": ["Dakisolatie"],
        "file_url": "https://example.com/report.pdf",
        "debug": True,
    }

    mock_download.return_value = "/tmp/report.pdf"
    mock_upload.return_value = SimpleNamespace(name="files/123")
    mock_extract.return_value = SimpleNamespace(model_dump=lambda: {"current_label": "D", "current_ep2_kwh_m2": 280, "measures": [], "notes": []})
    mock_pipeline.return_value = SimpleNamespace(model_dump=lambda: {"final_report": {"new_label": "B"}, "chosen_scenario": {"scenario_id": "GEBALANCEERD"}, "woningmodel": {}})

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "completed"
    assert data["data"]["final_report"]["new_label"] == "B"
