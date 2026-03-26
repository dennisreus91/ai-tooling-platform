from pathlib import Path

import pytest

from gemini_service import extract_report_data, upload_case_file


pytestmark = pytest.mark.live_gemini


def test_live_extract_report_data_smoke():
    """
    Lightweight live test:
    - uploads a small fixture file to Gemini
    - runs extraction
    - checks that a valid ExtractedReport comes back
    """
    sample_path = Path("tests/fixtures/sample_report.pdf")
    assert sample_path.exists(), "Missing fixture: tests/fixtures/sample_report.pdf"

    uploaded = upload_case_file(str(sample_path))
    result = extract_report_data(uploaded)

    assert result is not None
    assert isinstance(result.current_label, str)
    assert result.current_label.strip() != ""
    assert result.current_score >= 0
    assert result.current_ep2_kwh_m2 >= 0
    assert isinstance(result.measures, list)
    assert isinstance(result.notes, list)
