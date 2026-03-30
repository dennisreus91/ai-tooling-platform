import json
from pathlib import Path

import pytest

from gemini_service import upload_case_file, extract_woningmodel_data
from services.normalization_service import normalize_woningmodel
from services.measure_matching_service import match_measures
from services.measure_impact_service import screen_measure_impacts
from services.scenario_builder_service import build_scenarios
from services.scenario_calculation_service import GeminiScenarioCalculator
from services.scenario_selection_service import choose_best_scenario
from services.report_generation_service import build_final_report
from schemas import Constraints

pytestmark = pytest.mark.live_gemini


def test_live_stepwise_pipeline(sample_report_path: Path):
    print("\n[STEP 1] sample_report.pdf aanwezig")
    assert sample_report_path.exists()

    print(f"[INFO] sample report: {sample_report_path}")

    print("\n[STEP 2] upload naar Gemini")
    uploaded = upload_case_file(str(sample_report_path))
    assert uploaded is not None
    print(f"[INFO] uploaded file: {uploaded}")

    print("\n[STEP 3] extractie naar WoningModel")
    woningmodel = extract_woningmodel_data(uploaded)
    woningmodel_dict = woningmodel.model_dump()
    print(json.dumps(woningmodel_dict, indent=2, ensure_ascii=False)[:4000])

    assert "prestatie" in woningmodel_dict
    assert "extractie_meta" in woningmodel_dict
    assert "confidence" in woningmodel_dict["extractie_meta"]

    print("\n[STEP 4] normalisatie")
    normalized = normalize_woningmodel(woningmodel)
    normalized_dict = normalized.model_dump()
    print(json.dumps(normalized_dict, indent=2, ensure_ascii=False)[:4000])

    assert normalized.extractie_meta is not None

    print("\n[STEP 5] maatregelmatching")
    statuses = match_measures(normalized)
    print(f"[INFO] aantal maatregelstatussen: {len(statuses)}")
    assert len(statuses) > 0

    status_preview = [s.model_dump() for s in statuses[:10]]
    print(json.dumps(status_preview, indent=2, ensure_ascii=False))

    print("\n[STEP 6] impactscreening")
    impacts = screen_measure_impacts(statuses)
    print(f"[INFO] aantal impacts: {len(impacts)}")
    assert len(impacts) > 0

    impact_preview = [i.model_dump() for i in impacts[:10]]
    print(json.dumps(impact_preview, indent=2, ensure_ascii=False))

    print("\n[STEP 7] scenario-opbouw")
    scenarios = build_scenarios(impacts)
    print(f"[INFO] aantal scenario's: {len(scenarios)}")
    assert len(scenarios) >= 1

    scenario_preview = [s.model_dump() for s in scenarios]
    print(json.dumps(scenario_preview, indent=2, ensure_ascii=False))

    print("\n[STEP 8] scenario-doorrekening")
    constraints = Constraints(target_label="B", required_measures=[])
    current_ep2 = normalized.prestatie.current_ep2_kwh_m2 or 320.0
    current
