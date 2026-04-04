from unittest.mock import patch

import pytest

from schemas import Constraints, MeasureOverview, MeasureStatus, ScenarioAdvice, WoningModel
from services.poc_flow_service import run_poc_flow


def _sample_model(ep2: float = 280, label: str = "D") -> WoningModel:
    return WoningModel.model_validate(
        {
            "prestatie": {"current_ep2_kwh_m2": ep2, "current_label": label},
            "woning": {"type": "tussenwoning", "gebruiksoppervlakte_m2": 110, "bouwjaar": 1985},
            "bouwdelen": {
                "dak": {"rc": 2.0},
                "gevel": {"rc": 1.8},
                "vloer": {"rc": 1.5},
                "ramen": {"u_waarde": 2.8, "kozijn_isolerend": False},
            },
            "installaties": {
                "verwarming": {"type": "hr_ketel", "rendement": 0.8},
                "ventilatie": {"type": "natuurlijke_ventilatie"},
                "pv": {"kwp": 0.0, "max_extra_kwp": 3.5},
                "elektra": {"max_aansluitwaarde_kw": 10.0},
            },
            "extractie_meta": {},
        }
    )


@patch("services.poc_flow_service.get_scenario_advice_with_gemini")
@patch("services.poc_flow_service.get_measure_gap_analysis_with_gemini")
def test_run_poc_flow_end_to_end_with_gemini_scenario_advice(mock_gap, mock_advice):
    constraints = Constraints(target_label="B", required_measures=[])
    model = _sample_model()

    mock_gap.return_value = (
        [MeasureStatus(measure_id="dakisolatie", canonical_name="Dakisolatie", status="missing", reason="Ontbreekt.")],
        MeasureOverview(
            missing=[MeasureStatus(measure_id="dakisolatie", canonical_name="Dakisolatie", status="missing", reason="Ontbreekt.")],
            improvable=[],
            combined=[MeasureStatus(measure_id="dakisolatie", canonical_name="Dakisolatie", status="missing", reason="Ontbreekt.")],
        ),
    )
    mock_advice.return_value = ScenarioAdvice(
        scenario_id="GEMINI_GEBALANCEERD",
        scenario_name="Gemini Gebalanceerd",
        expected_label="B",
        expected_ep2_kwh_m2=180.0,
        selected_measures=["dakisolatie", "zonnepanelen_pv"],
        logical_order=["dakisolatie", "zonnepanelen_pv"],
        total_investment_eur=12000.0,
        monthly_savings_eur=95.0,
        expected_property_value_gain_eur=7000.0,
        motivation="Beste balans richting doellabel en Trias.",
        assumptions=["Indicatieve POC-doorrekening."],
        uncertainties=["Geen officiële rekenkern."],
        methodiek_bronnen=["NTA 8800", "ISSO 82.1"],
    )

    result = run_poc_flow(constraints, model)

    assert result.final_report.current_label == "D"
    assert result.final_report.new_label == "B"
    assert result.scenario_advice.scenario_id == "GEMINI_GEBALANCEERD"
    assert len(result.measure_overview.combined) >= 1


@patch("services.poc_flow_service.get_scenario_advice_with_gemini")
@patch("services.poc_flow_service.get_measure_gap_analysis_with_gemini")
def test_run_poc_flow_rejects_missing_ep2_without_backup_defaults(mock_gap, mock_advice):
    mock_gap.return_value = ([], MeasureOverview(missing=[], improvable=[], combined=[]))
    mock_advice.return_value = ScenarioAdvice(
        scenario_id="x",
        scenario_name="x",
        expected_label="C",
        expected_ep2_kwh_m2=200,
        motivation="x",
        total_investment_eur=0,
        monthly_savings_eur=0,
        expected_property_value_gain_eur=0,
    )

    constraints = Constraints(target_label="C", required_measures=[])
    model = WoningModel.model_validate({"prestatie": {"current_ep2_kwh_m2": None, "current_label": None}})

    with pytest.raises(ValueError, match="missing_ep2_data"):
        run_poc_flow(constraints, model)
