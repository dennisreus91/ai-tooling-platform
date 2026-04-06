from schemas import ScenarioAdvice, WoningModel
from services.report_generation_service import build_final_report


def _scenario_advice(**overrides) -> ScenarioAdvice:
    payload = {
        "scenario_id": "S1",
        "scenario_name": "Scenario 1",
        "expected_label": "B",
        "expected_ep2_kwh_m2": 180.0,
        "selected_measures": ["dakisolatie"],
        "logical_order": ["dakisolatie"],
        "total_investment_eur": 5000.0,
        "monthly_savings_eur": 75.0,
        "expected_property_value_gain_eur": 3000.0,
        "motivation": "Test",
    }
    payload.update(overrides)
    return ScenarioAdvice.model_validate(payload)


def test_build_final_report_uses_deterministic_usage_based_monthly_saving(monkeypatch):
    monkeypatch.setenv("DEFAULT_GAS_PRICE_EUR_PER_M3", "2.0")
    monkeypatch.setenv("DEFAULT_ELECTRICITY_PRICE_EUR_PER_KWH", "0.5")
    woningmodel = WoningModel.model_validate(
        {
            "prestatie": {"current_ep2_kwh_m2": 280.0, "current_label": "D"},
            "maatwerkadvies": {"gasverbruik_m3": 1000.0, "elektriciteitsverbruik_kwh": 3000.0},
            "extractie_meta": {},
        }
    )
    advice = _scenario_advice(expected_gasverbruik_m3=700.0, expected_elektriciteitsverbruik_kwh=2500.0)

    report = build_final_report("D", 280.0, woningmodel, advice)

    assert report.monthly_savings_eur == 70.83
    assert report.expected_property_value_gain_pct == 4.08


def test_build_final_report_falls_back_to_scenario_monthly_saving_when_usage_incomplete():
    woningmodel = WoningModel.model_validate(
        {
            "prestatie": {"current_ep2_kwh_m2": 280.0, "current_label": "D"},
            "maatwerkadvies": {"gasverbruik_m3": 1000.0, "elektriciteitsverbruik_kwh": None},
            "extractie_meta": {},
        }
    )
    advice = _scenario_advice(expected_gasverbruik_m3=700.0, expected_elektriciteitsverbruik_kwh=2500.0)

    report = build_final_report("D", 280.0, woningmodel, advice)

    assert report.monthly_savings_eur == 75.0
    assert report.expected_property_value_gain_pct == 4.08
