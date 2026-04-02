import json
from pathlib import Path

import pytest

from gemini_service import extract_woningmodel_data, get_scenario_advice_with_gemini, upload_case_file
from schemas import Constraints, MeasureOverview
from services.measure_matching_service import match_measures
from services.normalization_service import normalize_woningmodel
from services.poc_flow_service import run_poc_flow

pytestmark = [pytest.mark.live_gemini, pytest.mark.stepwise_live]


def test_live_stepwise_pipeline(sample_report_path: Path):
    print("\n[STEP 1] sample_report.pdf aanwezig")
    assert sample_report_path.exists()

    print("\n[STEP 2] upload naar Gemini")
    uploaded = upload_case_file(str(sample_report_path))
    assert uploaded is not None

    print("\n[STEP 3] extractie naar WoningModel")
    woningmodel = extract_woningmodel_data(uploaded)
    assert woningmodel.extractie_meta is not None

    print("\n[STEP 4] normalisatie")
    normalized = normalize_woningmodel(woningmodel)

    print("\n[STEP 5] maatregelmatching")
    statuses = match_measures(normalized)
    assert len(statuses) > 0

    print("\n[STEP 6] Gemini scenario advice")
    overview = MeasureOverview(
        missing=[s for s in statuses if s.status == "missing"],
        improvable=[s for s in statuses if s.status == "improvable"],
        combined=[s for s in statuses if s.status in {"missing", "improvable"}],
    )
    advice = get_scenario_advice_with_gemini(
        constraints=Constraints(target_label="B", required_measures=[]),
        woningmodel=normalized,
        measure_overview=overview,
    )
    print(json.dumps(advice.model_dump(), indent=2, ensure_ascii=False)[:4000])

    print("\n[STEP 7] run volledige flow")
    result = run_poc_flow(Constraints(target_label="B", required_measures=[]), woningmodel)
    assert result.final_report.new_label
