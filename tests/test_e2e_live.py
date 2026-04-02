from pathlib import Path

import pytest

from gemini_service import extract_woningmodel_data, upload_case_file
from schemas import Constraints
from services.poc_flow_service import run_poc_flow

pytestmark = [pytest.mark.live_gemini, pytest.mark.e2e_live]


def test_live_e2e_pipeline(sample_report_path: Path):
    uploaded = upload_case_file(str(sample_report_path))
    woningmodel = extract_woningmodel_data(uploaded)

    constraints = Constraints(target_label="B", required_measures=[])
    result = run_poc_flow(constraints, woningmodel)

    assert result.final_report is not None
    assert result.final_report.current_label
    assert result.final_report.new_label
    assert result.final_report.new_ep2_kwh_m2 is not None
    assert result.scenario_advice.scenario_id
    assert result.final_report.poc_disclaimer
