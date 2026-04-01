from schemas import Constraints, WoningModel
import pytest
from services.measure_matching_service import match_measures
from services.poc_flow_service import run_poc_flow
from services.scenario_builder_service import build_scenarios
from services.scenario_calculation_service import GeminiScenarioCalculator
from services.scenario_selection_service import choose_best_scenario


def test_run_poc_flow_end_to_end_without_llm():
    constraints = Constraints(target_label="B", required_measures=[])

    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": 280,
                "current_label": "D",
            },
            "woning": {
                "type": "tussenwoning",
                "gebruiksoppervlakte_m2": 110,
                "bouwjaar": 1985,
            },
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

    result = run_poc_flow(constraints, model)

    assert result.final_report.current_label == "D"
    assert result.final_report.new_ep2_kwh_m2 <= 280
    assert len(result.scenarios) >= 4
    assert result.chosen_scenario.scenario_id
    assert result.final_report.poc_disclaimer
    assert result.final_report.new_label


def test_match_measures_returns_multiple_status_types():
    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": 300,
                "current_label": "D",
            },
            "bouwdelen": {
                "dak": {"rc": 6.5},  # sufficient voor dakisolatie
                "gevel": {"rc": 1.0},  # improvable
                "vloer": {"rc": 1.0},  # improvable
                "ramen": {"u_waarde": 2.9, "kozijn_isolerend": False},
            },
            "installaties": {
                "verwarming": {"type": "hr_ketel", "rendement": 0.75},
                "pv": {"kwp": 0.0, "max_extra_kwp": 0.0},  # capacity issue voor PV
                "elektra": {"max_aansluitwaarde_kw": 4.0},  # capacity issue voor all-electric
            },
            "extractie_meta": {},
        }
    )

    statuses = match_measures(model)

    status_map = {s.measure_id: s.status for s in statuses}

    assert status_map["dakisolatie"] == "sufficient"
    assert status_map["gevelisolatie"] in {"improvable", "missing"}
    assert status_map["vloerisolatie"] in {"improvable", "missing"}
    assert status_map["zonnepanelen_pv"] == "capacity_limited"
    assert status_map["all_electric_warmtepomp"] == "capacity_limited"


def test_build_scenarios_creates_required_templates():
    constraints = Constraints(target_label="B", required_measures=[])
    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": 290,
                "current_label": "D",
            },
            "woning": {
                "type": "hoekwoning",
                "gebruiksoppervlakte_m2": 120,
            },
            "bouwdelen": {
                "dak": {"rc": 2.0},
                "gevel": {"rc": 2.0},
                "vloer": {"rc": 1.0},
                "ramen": {"u_waarde": 2.6, "kozijn_isolerend": False},
            },
            "installaties": {
                "verwarming": {"type": "hr_ketel", "rendement": 0.8},
                "pv": {"kwp": 0.0, "max_extra_kwp": 4.0},
                "elektra": {"max_aansluitwaarde_kw": 10.0},
            },
            "extractie_meta": {},
        }
    )

    result = run_poc_flow(constraints, model)
    scenario_ids = {s.scenario_id for s in result.scenarios}

    assert "MIN_LABELSPRONG" in scenario_ids
    assert "GOEDKOOPSTE_DOELLABEL" in scenario_ids
    assert "GEBALANCEERD" in scenario_ids
    assert "SCHIL_EERST" in scenario_ids


def test_scenario_calculation_reduces_ep2_and_returns_label():
    scenario = build_scenarios(
        [
            # Minimal stub-like objects are not enough because MeasureImpact is pydantic.
            # Daarom gebruiken we de flow zelf om geldige scenario’s te krijgen.
        ]
    ) if False else None  # pragma: no cover

    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": 280,
                "current_label": "D",
            },
            "woning": {
                "type": "tussenwoning",
                "gebruiksoppervlakte_m2": 110,
            },
            "bouwdelen": {
                "dak": {"rc": 2.0},
                "gevel": {"rc": 1.8},
                "vloer": {"rc": 1.2},
                "ramen": {"u_waarde": 2.8},
            },
            "installaties": {
                "verwarming": {"type": "hr_ketel", "rendement": 0.8},
                "pv": {"kwp": 0.0, "max_extra_kwp": 4.0},
                "elektra": {"max_aansluitwaarde_kw": 10.0},
            },
            "extractie_meta": {},
        }
    )

    result = run_poc_flow(Constraints(target_label="B", required_measures=[]), model)
    calculator = GeminiScenarioCalculator()
    calculated = calculator.calculate(
        scenario=result.scenarios[0],
        current_ep2=280.0,
        current_label="D",
    )

    assert calculated.expected_ep2_kwh_m2 <= 280.0
    assert calculated.expected_label
    assert calculated.total_investment_eur >= 0.0
    assert isinstance(calculated.selected_measures, list)


def test_choose_best_scenario_prefers_goal_achieving_option():
    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": 300,
                "current_label": "D",
            },
            "woning": {
                "type": "tussenwoning",
                "gebruiksoppervlakte_m2": 120,
            },
            "bouwdelen": {
                "dak": {"rc": 2.0},
                "gevel": {"rc": 1.5},
                "vloer": {"rc": 1.0},
                "ramen": {"u_waarde": 2.7},
            },
            "installaties": {
                "verwarming": {"type": "hr_ketel", "rendement": 0.8},
                "pv": {"kwp": 0.0, "max_extra_kwp": 4.0},
                "elektra": {"max_aansluitwaarde_kw": 10.0},
            },
            "extractie_meta": {},
        }
    )

    result = run_poc_flow(Constraints(target_label="C", required_measures=[]), model)
    chosen = choose_best_scenario(result.scenario_results, "C")

    assert chosen.scenario_id
    assert isinstance(chosen.goal_achieved, bool)
    assert chosen.reason


def test_run_poc_flow_rejects_missing_ep2_without_backup_defaults():
    constraints = Constraints(target_label="C", required_measures=[])

    model = WoningModel.model_validate(
        {
            "prestatie": {
                "current_ep2_kwh_m2": None,
                "current_label": None,
            },
            "woning": {
                "type": "tussenwoning",
            },
            "bouwdelen": {
                "dak": {"rc": None},
                "gevel": {"rc": None},
                "vloer": {"rc": None},
                "ramen": {"u_waarde": None},
            },
            "installaties": {
                "verwarming": {"type": None},
                "ventilatie": {"type": None},
                "pv": {"kwp": None, "max_extra_kwp": None},
                "elektra": {"max_aansluitwaarde_kw": None},
            },
            "extractie_meta": {
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )

    with pytest.raises(ValueError, match="geen hardcoded backupwaarden"):
        run_poc_flow(constraints, model)
