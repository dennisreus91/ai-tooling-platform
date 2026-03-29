import os
import pytest

pytestmark = pytest.mark.live_gemini


def test_live_pipeline_step_by_step_skips_without_api_key():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
