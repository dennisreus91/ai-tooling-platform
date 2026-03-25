import os
import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app import create_app


def _live_tests_enabled() -> bool:
    return os.getenv("RUN_GEMINI_LIVE_TESTS", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not _live_tests_enabled(),
    reason="Live Gemini tests are disabled. Set RUN_GEMINI_LIVE_TESTS=true to enable.",
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def run_fixture_server():
    port = _find_free_port()
    app = create_app()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        time.sleep(0.2)
        yield port
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_live_end_to_end_vabi_report_to_final_report(monkeypatch):
    """
    Full live E2E test:
    - starts a local Flask server
    - serves tests/fixtures/sample_report.pdf via /test-fixtures/...
    - calls /run-poc-flow
    - validates the full pipeline result
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")

    sample_path = Path("tests/fixtures/sample_report.pdf")
    if not sample_path.exists():
        pytest.skip("tests/fixtures/sample_report.pdf not found")

    monkeypatch.setenv("ALLOW_TEST_FILE_ENDPOINT", "true")

    with run_fixture_server() as port:
        file_url = f"http://127.0.0.1:{port}/test-fixtures/sample_report.pdf"

        app = create_app()
        client = app.test_client()

        payload = {
            "user_id": "live-test-user",
            "target_label": "A",
            "required_measures": [],
            "file_url": file_url,
        }

        response = client.post("/run-poc-flow", json=payload)
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "completed"

        optimization_result = data["data"]["optimization_result"]
        final_report = data["data"]["final_report"]

        assert optimization_result["expected_label"].strip() != ""
        assert optimization_result["total_cost"] >= 0
        assert optimization_result["expected_ep2_kwh_m2"] >= 0
        assert optimization_result["monthly_savings_eur"] >= 0
        assert optimization_result["expected_property_value_gain_eur"] >= 0
        assert isinstance(optimization_result["selected_measures"], list)

        assert final_report["title"].strip() != ""
        assert final_report["summary"].strip() != ""
        assert final_report["expected_label"].strip() != ""
        assert final_report["total_investment"] >= 0
        assert final_report["expected_ep2_kwh_m2"] == optimization_result["expected_ep2_kwh_m2"]
        assert final_report["monthly_savings_eur"] == optimization_result["monthly_savings_eur"]
        assert final_report["expected_property_value_gain_eur"] == optimization_result["expected_property_value_gain_eur"]
        assert isinstance(final_report["measures"], list)
        assert final_report["rationale"].strip() != ""
