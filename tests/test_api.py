from app import create_app


def test_run_poc_flow_accepts_valid_payload_with_list():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-123",
        "target_label": "a",
        "required_measures": ["isolatie", "zonnepanelen"],
        "file_url": "https://example.com/report.pdf",
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "accepted"
    assert data["data"]["user_id"] == "user-123"
    assert data["data"]["file_url"] == "https://example.com/report.pdf"
    assert data["data"]["constraints"]["target_label"] == "A"
    assert data["data"]["constraints"]["required_measures"] == [
        "isolatie",
        "zonnepanelen",
    ]


def test_run_poc_flow_accepts_valid_payload_with_string_measure():
    app = create_app()
    client = app.test_client()

    payload = {
        "user_id": "user-456",
        "target_label": "nextstep",
        "required_measures": "warmtepomp",
        "file_url": "https://example.com/report.xml",
    }

    response = client.post("/run-poc-flow", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["data"]["constraints"]["target_label"] == "next_step"
    assert data["data"]["constraints"]["required_measures"] == ["warmtepomp"]


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
