from __future__ import annotations

from schemas import ChosenScenario, FinalReport, ScenarioResult


def build_final_report(
    current_label: str,
    current_ep2: float,
    chosen: ChosenScenario,
    scenario_result: ScenarioResult,
) -> FinalReport:
    """
    Bouw het eindrapport op basis van:
    - huidige situatie
    - gekozen scenario
    - scenarioresultaat

    De rapportlaag mag geen nieuwe maatregelen of uitkomsten verzinnen.
    De output moet uitsluitend gebaseerd zijn op de reeds gekozen en doorgerekende scenario-uitkomst.
    """

    if chosen.scenario_id != scenario_result.scenario_id:
        raise ValueError(
            "ChosenScenario en ScenarioResult horen niet bij hetzelfde scenario."
        )

    measures = list(scenario_result.selected_measures or [])
    logical_order = list(scenario_result.selected_measures or [])

    summary = (
        f"Indicatief labelsprongadvies richting scenario '{chosen.scenario_name}'. "
        f"Huidige situatie: label {current_label} met EP2 van {current_ep2:.1f} kWh/m². "
        f"Verwachte uitkomst: label {scenario_result.expected_label} met EP2 van "
        f"{scenario_result.expected_ep2_kwh_m2:.1f} kWh/m²."
    )

    if not measures:
        summary += " Er zijn geen concrete maatregelen in het scenario opgenomen."

    poc_disclaimer = (
        "Dit rapport is een POC-scenario-inschatting op basis van Vabi-extractie, "
        "JSON-configuratie en Gemini-gestuurde scenarioanalyse. "
        "Het betreft geen officiële energielabelregistratie of gecertificeerde NTA 8800-berekening."
    )

    return FinalReport(
        title="POC Labelsprongadvies",
        summary=summary,
        current_label=current_label,
        current_ep2_kwh_m2=current_ep2,
        chosen_scenario=chosen.scenario_name,
        measures=measures,
        logical_order=logical_order,
        total_investment_eur=scenario_result.total_investment_eur,
        new_label=scenario_result.expected_label,
        new_ep2_kwh_m2=scenario_result.expected_ep2_kwh_m2,
        monthly_savings_eur=scenario_result.monthly_savings_eur,
        expected_property_value_gain_eur=scenario_result.expected_property_value_gain_eur,
        motivation=chosen.reason,
        assumptions=list(scenario_result.assumptions or []),
        uncertainties=list(scenario_result.uncertainties or []),
        poc_disclaimer=poc_disclaimer,
    )
