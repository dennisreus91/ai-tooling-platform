from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


def test_run_poc_flow_rejects_missing_json_body():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/run-poc-flow",
        data="not-json",
        content_type="text/plain",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"]["code"] == "invalid_json"


def test_run_poc_flow_rejects_invalid_payload():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "u1",
        # target_label ontbreekt
        "file_url": "https://example.com/report.pdf",
    }

    response = client.post("/run-poc-flow", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


@patch("app.run_poc_flow")
@patch("app.extract_woningmodel_data")
@patch("app.upload_case_file")
@patch("app.download_file_to_temp")
def test_run_poc_flow_completes_successfully_debug_true(
    mock_download,
    mock_upload,
    mock_extract,
    mock_pipeline,
):
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
    mock_extract.return_value = SimpleNamespace(
        model_dump=lambda: {
            "prestatie": {"current_label": "D", "current_ep2_kwh_m2": 280},
            "extractie_meta": {
                "confidence": 0.8,
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )
    mock_pipeline.return_value = SimpleNamespace(
        model_dump=lambda: {
            "final_report": {"new_label": "B"},
            "chosen_scenario": {"scenario_id": "GEBALANCEERD"},
            "woningmodel": {"prestatie": {"current_label": "D"}},
            "measure_statuses": [],
            "measure_overview": {"missing": [], "improvable": [], "combined": []},
            "scenario_advice": {"scenario_id": "GEMINI_GEBALANCEERD"},
        }
    )

    response = client.post("/run-poc-flow", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "completed"
    assert data["data"]["final_report"]["new_label"] == "B"
    assert "woningmodel" in data["data"]


@patch("app.run_poc_flow")
@patch("app.extract_woningmodel_data")
@patch("app.upload_case_file")
@patch("app.download_file_to_temp")
def test_run_poc_flow_hides_debug_fields_when_debug_false(
    mock_download,
    mock_upload,
    mock_extract,
    mock_pipeline,
):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "u1",
        "target_label": "A",
        "required_measures": ["Dakisolatie"],
        "file_url": "https://example.com/report.pdf",
        "debug": False,
    }

    mock_download.return_value = "/tmp/report.pdf"
    mock_upload.return_value = SimpleNamespace(name="files/123")
    mock_extract.return_value = SimpleNamespace(
        model_dump=lambda: {
            "prestatie": {"current_label": "D", "current_ep2_kwh_m2": 280},
            "extractie_meta": {
                "confidence": 0.8,
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )
    mock_pipeline.return_value = SimpleNamespace(
        model_dump=lambda: {
            "final_report": {"new_label": "B"},
            "chosen_scenario": {"scenario_id": "GEBALANCEERD"},
            "woningmodel": {"prestatie": {"current_label": "D"}},
            "measure_statuses": [{"measure_id": "dakisolatie"}],
            "measure_overview": {"missing": [], "improvable": [], "combined": []},
            "scenario_advice": {"scenario_id": "GEMINI_GEBALANCEERD"},
        }
    )

    response = client.post("/run-poc-flow", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "completed"
    assert "woningmodel" not in data["data"]
    assert "measure_statuses" not in data["data"]
    assert "measure_overview" not in data["data"]
    assert "scenario_advice" not in data["data"]
    assert data["data"]["final_report"]["new_label"] == "B"


@patch("app.extract_woningmodel_data")
@patch("app.upload_case_file")
@patch("app.download_file_to_temp")
def test_run_poc_flow_returns_processing_error_on_runtime_failure(
    mock_download,
    mock_upload,
    mock_extract,
):
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "u1",
        "target_label": "A",
        "required_measures": [],
        "file_url": "https://example.com/report.pdf",
        "debug": False,
    }

    mock_download.return_value = "/tmp/report.pdf"
    mock_upload.return_value = SimpleNamespace(name="files/123")
    mock_extract.side_effect = RuntimeError("invalid_llm_json: extraction failed")

    response = client.post("/run-poc-flow", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert data["error"]["code"] == "invalid_llm_json"
    assert "extraction failed" in data["error"]["message"]
