import os
import pytest

pytestmark = pytest.mark.live_gemini


def test_live_extract_skips_without_api_key():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
