from __future__ import annotations

from schemas import ChosenScenario, FinalReport, ScenarioResult


def build_final_report(current_label: str, current_ep2: float, chosen: ChosenScenario, scenario_result: ScenarioResult) -> FinalReport:
    return FinalReport(
        title="POC Labelsprongadvies",
        summary="Indicatief advies op basis van Vabi-extractie en scenariovergelijking.",
        current_label=current_label,
        current_ep2_kwh_m2=current_ep2,
        chosen_scenario=chosen.scenario_name,
        measures=scenario_result.selected_measures,
        logical_order=scenario_result.selected_measures,
        total_investment=scenario_result.total_investment_eur,
        new_label=scenario_result.expected_label,
        new_ep2_kwh_m2=scenario_result.expected_ep2_kwh_m2,
        monthly_savings_eur=scenario_result.monthly_savings_eur,
        expected_property_value_gain_eur=scenario_result.expected_property_value_gain_eur,
        motivation=chosen.reason,
        assumptions=scenario_result.assumptions,
        uncertainties=scenario_result.uncertainties,
        poc_disclaimer="Dit rapport is een POC-scenario-inschatting en geen officiële energielabelregistratie.",
    )
