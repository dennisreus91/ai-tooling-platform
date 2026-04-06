from __future__ import annotations

import os

from schemas import FinalReport, ScenarioAdvice, WoningModel

DEFAULT_GAS_PRICE_EUR_PER_M3 = 1.45
DEFAULT_ELECTRICITY_PRICE_EUR_PER_KWH = 0.32


def _read_price_from_env(name: str, fallback: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    try:
        value = float(str(raw).replace(",", ".").strip())
    except (TypeError, ValueError):
        return fallback
    return value if value > 0.0 else fallback


def _calculate_monthly_saving_eur(
    woningmodel: WoningModel,
    scenario_advice: ScenarioAdvice,
) -> float | None:
    current_gas = woningmodel.maatwerkadvies.gasverbruik_m3
    current_electricity = woningmodel.maatwerkadvies.elektriciteitsverbruik_kwh
    expected_gas = scenario_advice.expected_gasverbruik_m3
    expected_electricity = scenario_advice.expected_elektriciteitsverbruik_kwh

    if None in (current_gas, current_electricity, expected_gas, expected_electricity):
        return None

    gas_price = _read_price_from_env("DEFAULT_GAS_PRICE_EUR_PER_M3", DEFAULT_GAS_PRICE_EUR_PER_M3)
    electricity_price = _read_price_from_env(
        "DEFAULT_ELECTRICITY_PRICE_EUR_PER_KWH",
        DEFAULT_ELECTRICITY_PRICE_EUR_PER_KWH,
    )

    yearly_current_cost = (float(current_gas) * gas_price) + (float(current_electricity) * electricity_price)
    yearly_expected_cost = (float(expected_gas) * gas_price) + (float(expected_electricity) * electricity_price)
    monthly_saving = max((yearly_current_cost - yearly_expected_cost) / 12.0, 0.0)
    return round(monthly_saving, 2)


def build_final_report(
    current_label: str,
    current_ep2: float,
    woningmodel: WoningModel,
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

    calculated_monthly_saving = _calculate_monthly_saving_eur(woningmodel, scenario_advice)
    monthly_savings_eur = (
        calculated_monthly_saving if calculated_monthly_saving is not None else scenario_advice.monthly_savings_eur
    )

    assumptions = list(scenario_advice.assumptions or [])
    if calculated_monthly_saving is not None:
        assumptions.append(
            "monthly_savings_eur deterministisch berekend uit (huidig - verwacht) gas/elektriciteitsverbruik met standaard energieprijzen uit environment variabelen of fallback-defaults."
        )
    else:
        assumptions.append(
            "monthly_savings_eur overgenomen uit scenario_advice omdat huidig/verwacht verbruik incompleet was voor deterministische doorrekening."
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
        monthly_savings_eur=monthly_savings_eur,
        expected_property_value_gain_eur=scenario_advice.expected_property_value_gain_eur,
        motivation=scenario_advice.motivation,
        assumptions=assumptions,
        uncertainties=list(scenario_advice.uncertainties or []),
        poc_disclaimer=poc_disclaimer,
    )
