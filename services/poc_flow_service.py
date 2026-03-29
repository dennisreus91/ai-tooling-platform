from __future__ import annotations

from schemas import Constraints, PocFlowResult, WoningModel
from services.measure_impact_service import screen_measure_impacts
from services.measure_matching_service import match_measures
from services.normalization_service import normalize_woningmodel
from services.report_generation_service import build_final_report
from services.scenario_builder_service import build_scenarios
from services.scenario_calculation_service import GeminiScenarioCalculator
from services.scenario_selection_service import choose_best_scenario
from validators import label_from_ep2


def run_poc_flow(constraints: Constraints, woningmodel: WoningModel) -> PocFlowResult:
    model = normalize_woningmodel(woningmodel)
    current_ep2 = float(model.prestatie.get("current_ep2_kwh_m2", 320.0))
    current_label = str(model.prestatie.get("current_label") or label_from_ep2(current_ep2))

    statuses = match_measures(model.model_dump())
    impacts = screen_measure_impacts(statuses)
    scenarios = build_scenarios(impacts)

    calculator = GeminiScenarioCalculator()
    results = [calculator.calculate(scenario, current_ep2) for scenario in scenarios]

    chosen = choose_best_scenario(results, constraints.target_label)
    scenario_map = {result.scenario_id: result for result in results}
    final_report = build_final_report(current_label, current_ep2, chosen, scenario_map[chosen.scenario_id])

    return PocFlowResult(
        constraints=constraints,
        woningmodel=model,
        measure_statuses=statuses,
        measure_impacts=impacts,
        scenarios=scenarios,
        scenario_results=results,
        chosen_scenario=chosen,
        final_report=final_report,
    )
