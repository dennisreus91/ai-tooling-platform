from __future__ import annotations

from typing import Any

from schemas import ChosenScenario, ScenarioResult
from services.config_service import get_label_boundaries


def _label_rank(label: str) -> int:
    """
    Deterministische labelrang op basis van labelgrenzen.json.
    Lager getal = beter label.
    """
    config = get_label_boundaries()
    ranks = config.get("label_rank", {})
    return int(ranks.get(label, 999))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except (TypeError, ValueError):
        return default


def _measure_count(result: ScenarioResult) -> int:
    measures = getattr(result, "selected_measures", None) or []
    return len(measures)


def _scenario_logic_penalty(result: ScenarioResult) -> float:
    """
    Eenvoudige plausibiliteits-/logicascore op basis van aannames en onzekerheden.
    Hogere penalty = minder logisch / meer onzeker.
    Dit blijft een POC-benadering; echte technische plausibiliteit hoort idealiter
    deels al eerder in scenario-opbouw te zijn afgevangen.
    """
    assumptions = getattr(result, "assumptions", []) or []
    uncertainties = getattr(result, "uncertainties", []) or []

    penalty = 0.0

    # Meer onzekerheden = iets minder voorkeur
    penalty += min(len(uncertainties) * 0.2, 2.0)

    # Specifieke signalen die duiden op beperktere logica of onzekerheid
    uncertainty_text = " ".join(str(x).lower() for x in uncertainties)
    if "onzeker" in uncertainty_text:
        penalty += 0.2
    if "capaciteit" in uncertainty_text:
        penalty += 0.3
    if "niet officieel" in uncertainty_text or "poc" in uncertainty_text:
        penalty += 0.1

    # Veel maatregelen = iets minder aantrekkelijk dan compacte logische route
    penalty += max(0, _measure_count(result) - 3) * 0.05

    return round(penalty, 3)


def _feasible_sort_key(result: ScenarioResult) -> tuple:
    """
    Sorteerbare sleutel voor scenario's die het doel-label halen.
    Voorkeur:
    1. laagste investering
    2. laagste logica-penalty
    3. minste maatregelen
    4. hoogste maandbesparing
    """
    return (
        _safe_float(result.total_investment_eur, default=999999.0),
        _scenario_logic_penalty(result),
        _measure_count(result),
        -_safe_float(result.monthly_savings_eur, default=0.0),
    )


def _fallback_sort_key(result: ScenarioResult) -> tuple:
    """
    Sorteerbare sleutel voor scenario's die het doel-label niet halen.
    Voorkeur:
    1. beste label (laagste rank)
    2. laagste investering
    3. laagste logica-penalty
    4. hoogste maandbesparing
    """
    return (
        _label_rank(result.expected_label),
        _safe_float(result.total_investment_eur, default=999999.0),
        _scenario_logic_penalty(result),
        -_safe_float(result.monthly_savings_eur, default=0.0),
    )


def choose_best_scenario(results: list[ScenarioResult], target_label: str) -> ChosenScenario:
    """
    Kies het beste scenario volgens de regels uit de energielabel-tool:

    Primaire regel:
    - kies het goedkoopste scenario dat het doel-label haalt

    Secundaire regels:
    - logische uitvoeringsvolgorde / plausibiliteit
    - beperkt aantal maatregelen
    - hogere maandbesparing

    Fallback:
    - als geen scenario het doel haalt, kies het scenario dat er het dichtst bij komt
      met een logische en betaalbare uitkomst
    """
    if not results:
        raise ValueError("choose_best_scenario ontving geen scenarioresultaten.")

    target_rank = _label_rank(target_label)
    feasible = [r for r in results if _label_rank(r.expected_label) <= target_rank]

    if feasible:
        ordered = sorted(feasible, key=_feasible_sort_key)
        selected = ordered[0]

        reason = (
            "Gekozen als goedkoopste logische scenario dat het doel-label haalt, "
            "met aanvullende weging op plausibiliteit, beperkt aantal maatregelen "
            "en maandbesparing."
        )

        return ChosenScenario(
            scenario_id=selected.scenario_id,
            scenario_name=selected.scenario_name,
            reason=reason,
            goal_achieved=True,
        )

    ordered = sorted(results, key=_fallback_sort_key)
    selected = ordered[0]

    reason = (
        "Geen scenario haalde het doel-label. Gekozen is het scenario dat het dichtst "
        "bij het doel komt, met aanvullende weging op investering, plausibiliteit "
        "en maandbesparing."
    )

    return ChosenScenario(
        scenario_id=selected.scenario_id,
        scenario_name=selected.scenario_name,
        reason=reason,
        goal_achieved=False,
    )
