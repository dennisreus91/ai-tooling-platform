from pathlib import Path

import pytest

from gemini_service import extract_woningmodel_data, upload_case_file

pytestmark = pytest.mark.live_gemini


def test_live_extract_sample_report(sample_report_path: Path):
    uploaded = upload_case_file(str(sample_report_path))
    woningmodel = extract_woningmodel_data(uploaded)

    data = woningmodel.model_dump()

    assert "prestatie" in data
    assert "extractie_meta" in data
    assert "confidence" in data["extractie_meta"]
