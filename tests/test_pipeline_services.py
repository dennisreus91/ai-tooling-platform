from schemas import Constraints, WoningModel
from services.poc_flow_service import run_poc_flow


def test_run_poc_flow_end_to_end_without_llm():
    constraints = Constraints(target_label="B", required_measures=[])
    model = WoningModel.model_validate(
        {
            "prestatie": {"current_ep2_kwh_m2": 280, "current_label": "D"},
            "bouwdelen": {"dak": {"rc": 2.0}, "gevel": {"rc": 1.8}, "vloer": {"rc": 1.5}, "ramen": {"u_waarde": 2.8}},
            "installaties": {"pv": {"kwp": 0.0, "max_extra_kwp": 3.5}},
            "extractie_meta": {},
        }
    )

    result = run_poc_flow(constraints, model)

    assert result.final_report.current_label == "D"
    assert result.final_report.new_ep2_kwh_m2 <= 280
    assert len(result.scenarios) >= 4
    assert result.chosen_scenario.scenario_id
