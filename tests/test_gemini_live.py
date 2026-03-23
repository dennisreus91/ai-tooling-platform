import os
from pathlib import Path

import pytest

from gemini_service import extract_report_data, upload_case_file


def _live_tests_enabled() -> bool:
    return os.getenv("RUN_GEMINI_LIVE_TESTS", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not _live_tests_enabled(),
    reason="Live Gemini tests are disabled. Set RUN_GEMINI_LIVE_TESTS=true to enable.",
)


def test_live_extract_report_data_smoke():
    """
    Lightweight live test:
    - uploads a small fixture file to Gemini
    - runs extraction
    - checks that a valid ExtractedReport comes back
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")

    sample_path = Path("tests/fixtures/sample_report.pdf")
    if not sample_path.exists():
        pytest.skip("tests/fixtures/sample_report.pdf not found")

    uploaded = upload_case_file(str(sample_path))
    result = extract_report_data(uploaded)

    assert result is not None
    assert isinstance(result.current_label, str)
    assert result.current_label.strip() != ""
    assert result.current_score >= 0
    assert isinstance(result.measures, list)
    assert isinstance(result.notes, list)
