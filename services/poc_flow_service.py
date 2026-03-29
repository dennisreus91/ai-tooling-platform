from __future__ import annotations

from schemas import Constraints, PocFlowResult, WoningModel
from services.measure_impact_service import screen_measure_impacts
from services.measure_matching_service import match_measures
from services.normalization_service import normalize_woningmodel
from services.report_generation_service import build_final_report
from services.scenario_builder_service import build_scenarios
from services.scenario_calculation_service import GeminiScenarioCalculator
from services.scenario_selection_service import choose_best_scenario
from services.config_service import get_label_boundaries


def _label_from_ep2(ep2: float) -> str:
    """
    Deterministische labelmapping op basis van labelgrenzen.json.
    """
    config = get_label_boundaries()
    boundaries = config.get("boundaries", [])

    for boundary in boundaries:
        min_val = boundary.get("ep2_min_inclusive")
        max_val = boundary.get("ep2_max_exclusive")

        lower_ok = True if min_val is None else ep2 >= float(min_val)
        upper_ok = True if max_val is None else ep2 < float(max_val)

        if lower_ok and upper_ok:
            return boundary["label"]

    raise ValueError(f"Geen labelgrens gevonden voor EP2={ep2}")


def run_poc_flow(constraints: Constraints, woningmodel: WoningModel) -> PocFlowResult:
    """
    Orchestratie van de POC-flow na extractie.

    Verwachte volgorde:
    1. normalisatie van woningmodel
    2. maatregelmatching
    3. maatregel-impact screening
    4. scenario-opbouw
    5. scenario-doorrekening
    6. scenario-selectie
    7. rapportage

    Deze service verwacht een reeds geëxtraheerd WoningModel als input.
    De extractiestap zelf hoort in extraction_service.py of in een bovenliggende orchestrationlaag.
    """
    # 1. Normalisatie
    model = normalize_woningmodel(woningmodel)

    current_ep2 = float(model.prestatie.get("current_ep2_kwh_m2", 320.0))
    current_label = str(model.prestatie.get("current_label") or _label_from_ep2(current_ep2))

    # 2. Maatregelmatching
    statuses = match_measures(model)

    # 3. Maatregel-impact screening
    impacts = screen_measure_impacts(statuses)

    # 4. Scenario-opbouw
    scenarios = build_scenarios(impacts)
    if not scenarios:
        raise ValueError("Er konden geen scenario's worden opgebouwd op basis van de huidige maatregelstatus en impactscreening.")

    # 5. Scenario-doorrekening
    calculator = GeminiScenarioCalculator()
    results = [
        calculator.calculate(
            scenario=scenario,
            current_ep2=current_ep2,
            current_label=current_label,
        )
        for scenario in scenarios
    ]
    if not results:
        raise ValueError("Er zijn geen scenarioresultaten gegenereerd.")

    # 6. Scenario-selectie
    chosen = choose_best_scenario(results, constraints.target_label)

    scenario_map = {result.scenario_id: result for result in results}
    chosen_result = scenario_map.get(chosen.scenario_id)
    if chosen_result is None:
        raise ValueError(
            f"Gekozen scenario '{chosen.scenario_id}' is niet teruggevonden in scenarioresultaten."
        )

    # 7. Rapportage
    final_report = build_final_report(
        current_label=current_label,
        current_ep2=current_ep2,
        chosen=chosen,
        scenario_result=chosen_result,
    )

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
