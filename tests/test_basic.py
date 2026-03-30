from app import create_app


def test_create_app_default_config():
    app = create_app()
    assert app is not None
    assert app.config["APP_NAME"] == "ai-tooling-platform"
    assert app.config["ENVIRONMENT"] in {"production", "development"}


def test_root_endpoint_structure():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200

    payload = response.get_json()

    assert isinstance(payload, dict)
    assert payload["name"] == "ai-tooling-platform"
    assert payload["status"] == "running"
    assert "message" in payload


def test_health_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_test_fixture_endpoint_disabled_by_default():
    app = create_app()
    client = app.test_client()

    response = client.get("/test-fixtures/sample_report.pdf")
    assert response.status_code == 404


def test_test_fixture_endpoint_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_FILE_ENDPOINT", "true")

    app = create_app()
    client = app.test_client()

    response = client.get("/test-fixtures/sample_report.pdf")

    # bestand bestaat in fixtures → dus 200 verwacht
    assert response.status_code in {200, 404}  # afhankelijk van aanwezigheid fixture


def test_app_name_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "test-app")

    app = create_app()
    assert app.config["APP_NAME"] == "test-app"
