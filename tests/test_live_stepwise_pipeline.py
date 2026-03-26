import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app import create_app
from gemini_service import (
    build_final_report,
    download_file_to_temp,
    extract_report_data,
    optimize_report,
    upload_case_file,
)
from validators import normalize_constraints, validate_extract


pytestmark = pytest.mark.live_gemini


FIXTURE_PATH = Path("tests/fixtures/sample_report.pdf")


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


def test_live_pipeline_step_by_step(monkeypatch):
    """
    Runs every pipeline step explicitly and validates each step output.

    This test is intentionally verbose so failures clearly show
    in which stage the live flow breaks.
    """
    assert FIXTURE_PATH.exists(), "Missing fixture: tests/fixtures/sample_report.pdf"

    monkeypatch.setenv("ALLOW_TEST_FILE_ENDPOINT", "true")

    with run_fixture_server() as port:
        file_url = f"http://127.0.0.1:{port}/test-fixtures/sample_report.pdf"

        # Step 1 + 2: intake + constraints normalization
        constraints = normalize_constraints(
            target_label="A",
            required_measures=[],
        )
        assert constraints.target_label == "A"
        assert constraints.required_measures == []

        # Step 3: file download
        local_path = download_file_to_temp(file_url)
        assert Path(local_path).exists()
        assert Path(local_path).stat().st_size > 0

        # Step 4: upload to Gemini
        uploaded_file = upload_case_file(local_path)
        uploaded_name = getattr(uploaded_file, "name", "")
        assert isinstance(uploaded_name, str)
        assert uploaded_name.strip() != ""

        # Step 5: extraction
        extracted_report = extract_report_data(uploaded_file)
        assert extracted_report.current_label.strip() != ""
        assert extracted_report.current_score >= 0
        assert extracted_report.current_ep2_kwh_m2 >= 0

        # Step 6: extraction validation
        validated_extract = validate_extract(extracted_report)
        assert validated_extract.current_label == extracted_report.current_label
        assert validated_extract.current_ep2_kwh_m2 == extracted_report.current_ep2_kwh_m2

        # Step 7: optimization
        optimization_result = optimize_report(
            uploaded_file=uploaded_file,
            constraints=constraints,
            extracted_report=validated_extract,
        )
        assert optimization_result.expected_label.strip() != ""
        assert optimization_result.total_cost >= 0
        assert optimization_result.expected_ep2_kwh_m2 >= 0
        assert optimization_result.monthly_savings_eur >= 0
        assert optimization_result.expected_property_value_gain_eur >= 0

        # Step 8: final report generation
        final_report = build_final_report(
            opt_result=optimization_result,
            extracted_report=validated_extract,
            constraints=constraints,
        )
        assert final_report.title.strip() != ""
        assert final_report.summary.strip() != ""
        assert final_report.rationale.strip() != ""

        # Step 9: output consistency checks
        assert final_report.expected_label == optimization_result.expected_label
        assert final_report.total_investment == optimization_result.total_cost
        assert final_report.expected_ep2_kwh_m2 == optimization_result.expected_ep2_kwh_m2
        assert final_report.monthly_savings_eur == optimization_result.monthly_savings_eur
        assert (
            final_report.expected_property_value_gain_eur
            == optimization_result.expected_property_value_gain_eur
        )
