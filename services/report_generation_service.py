from __future__ import annotations

from schemas import FinalReport, ScenarioAdvice


def build_final_report(
    current_label: str,
    current_ep2: float,
    scenario_advice: ScenarioAdvice,
) -> FinalReport:
    measures = list(scenario_advice.selected_measures or [])
    logical_order = list(scenario_advice.logical_order or measures)

    summary = (
        f"Indicatief labelsprongadvies richting scenario '{scenario_advice.scenario_name}'. "
        f"Huidige situatie: label {current_label} met EP2 van {current_ep2:.1f} kWh/m². "
        f"Verwachte uitkomst: label {scenario_advice.expected_label} met EP2 van "
        f"{scenario_advice.expected_ep2_kwh_m2:.1f} kWh/m²."
    )

    poc_disclaimer = (
        "Dit rapport is een Gemini-heavy POC-scenario-inschatting op basis van Vabi-extractie, "
        "JSON-configuratie en methodiekcontext (ISSO 82.1/82.2, NTA 8800, RVO voorbeeldwoningen). "
        "Het betreft geen officiële energielabelregistratie of gecertificeerde NTA 8800-berekening."
    )

    return FinalReport(
        title="POC Labelsprongadvies",
        summary=summary,
        current_label=current_label,
        current_ep2_kwh_m2=current_ep2,
        chosen_scenario=scenario_advice.scenario_name,
        measures=measures,
        logical_order=logical_order,
        total_investment_eur=scenario_advice.total_investment_eur,
        new_label=scenario_advice.expected_label,
        new_ep2_kwh_m2=scenario_advice.expected_ep2_kwh_m2,
        monthly_savings_eur=scenario_advice.monthly_savings_eur,
        expected_property_value_gain_eur=scenario_advice.expected_property_value_gain_eur,
        motivation=scenario_advice.motivation,
        assumptions=list(scenario_advice.assumptions or []),
        uncertainties=list(scenario_advice.uncertainties or []),
        poc_disclaimer=poc_disclaimer,
    )
