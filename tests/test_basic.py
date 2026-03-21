from app import create_app


def test_create_app():
    app = create_app()
    assert app is not None
    assert app.config["APP_NAME"] == "ai-tooling-platform"


def test_root_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["name"] == "ai-tooling-platform"
    assert payload["status"] == "running"
    assert payload["message"] == "AI tooling platform API is online."


def test_health_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
