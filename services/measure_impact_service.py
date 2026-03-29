from __future__ import annotations

from typing import Any

from schemas import MeasureImpact, MeasureStatus
from services.config_service import get_measures_library


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except (TypeError, ValueError):
        return None


def _estimate_investment(measure: dict[str, Any]) -> float:
    """
    Voor de screening gebruiken we een indicatieve investering.
    Prioriteit:
    1. investment_per_unit_eur
    2. midden van investment_bandwidth_eur
    3. fallback 1000
    """
    per_unit = _safe_float(measure.get("investment_per_unit_eur"))
    if per_unit is not None:
        return round(per_unit, 2)

    bandwidth = measure.get("investment_bandwidth_eur", {})
    min_val = _safe_float(bandwidth.get("min"))
    max_val = _safe_float(bandwidth.get("max"))

    if min_val is not None and max_val is not None:
        return round((min_val + max_val) / 2.0, 2)

    return 1000.0


def _estimate_ep2_reduction(status: MeasureStatus, measure: dict[str, Any]) -> float:
    """
    Indicatieve screening voor maatregelimpact.
    GEEN officiële of definitieve berekening.
    Deze waarde dient alleen als prioriteringsanker voor scenario-opbouw.
    """
    trias_step = measure.get("trias_step")
    impact_path = measure.get("impact_path", [])
    current_value = status.current_value
    target_value = status.target_value
    comparison_mode = measure.get("comparison_mode")

    # Basisimpact per trias-stap
    if trias_step == 1:
        base = 14.0
    elif trias_step == 2:
        base = 18.0
    else:
        base = 6.0

    # Extra nuance op basis van impact_path
    if isinstance(impact_path, list):
        if any("lagere warmtebehoefte" in str(x).lower() for x in impact_path):
            base += 4.0
        if any("lagere ep2" in str(x).lower() for x in impact_path):
            base += 2.0
        if any("sterke" in str(x).lower() or "fors" in str(x).lower() for x in impact_path):
            base += 3.0

    # Als er een duidelijke delta is, gebruik die om de screening iets te verfijnen
    current_num = _safe_float(current_value)
    target_num = _safe_float(target_value)

    if current_num is not None and target_num is not None:
        if comparison_mode == "min_gte":
            delta = max(0.0, target_num - current_num)
            base += min(delta * 1.5, 12.0)
        elif comparison_mode == "max_lte":
            delta = max(0.0, current_num - target_num)
            base += min(delta * 6.0, 12.0)

    # Beperk screeningimpact tot plausibele bandbreedte voor deze fase
    return round(min(max(base, 2.0), 35.0), 2)


def _logic_score(status: MeasureStatus, measure: dict[str, Any]) -> float:
    """
    Indicatieve logische prioriteit voor scenario-opbouw.
    Hogere score = eerder kandidaat voor scenario’s.
    """
    score = 0.5

    trias_step = measure.get("trias_step")
    priority = _safe_float(measure.get("calculation_priority")) or 99

    # Trias-voorkeur
    if trias_step == 1:
        score += 0.20
    elif trias_step == 2:
        score += 0.15
    elif trias_step == 3:
        score += 0.05

    # Lagere calculation_priority = eerder logisch
    if priority <= 5:
        score += 0.15
    elif priority <= 10:
        score += 0.10
    else:
        score += 0.05

    # Missing krijgt iets hogere prioriteit dan improvable
    if status.status == "missing":
        score += 0.10
    elif status.status == "improvable":
        score += 0.05

    # Dependencies maken maatregel iets minder direct inzetbaar in screening
    if measure.get("dependencies"):
        score -= 0.05

    return round(min(max(score, 0.0), 1.0), 2)


def screen_measure_impacts(statuses: list[MeasureStatus]) -> list[MeasureImpact]:
    """
    Screeninglaag voor maatregelimpact.

    Doel:
    - ontbrekende of verbeterbare maatregelen indicatief prioriteren
    - grove EP2-impact en investering schatten
    - input leveren voor scenario-opbouw

    Niet bedoeld voor:
    - officiële doorrekening
    - definitieve labelbepaling
    - scenarioselectie op zichzelf
    """
    library = {m["id"]: m for m in get_measures_library()["measures"]}
    impacts: list[MeasureImpact] = []

    for status in statuses:
        if status.status not in {"missing", "improvable"}:
            continue

        measure = library.get(status.measure_id)
        if not measure:
            continue

        estimated_investment = _estimate_investment(measure)
        estimated_ep2_reduction = _estimate_ep2_reduction(status, measure)
        logic_score = _logic_score(status, measure)

        assumptions = [
            "Dit is een indicatieve maatregel-screening op basis van de maatregelenbibliotheek.",
            "De weergegeven EP2-reductie is alleen bedoeld voor prioritering richting scenario-opbouw."
        ]

        uncertainties = [
            "Definitieve EP2-effecten vereisen scenario-doorrekening met Gemini of later een softwarekoppeling zoals Vabi/Uniec.",
            "Werkelijke investering hangt af van hoeveelheid, woningtype, uitvoeringskeuze en projectspecifieke omstandigheden."
        ]

        impacts.append(
            MeasureImpact(
                measure_id=status.measure_id,
                canonical_name=status.canonical_name,
                estimated_ep2_reduction=estimated_ep2_reduction,
                estimated_investment_eur=estimated_investment,
                logic_score=logic_score,
                assumptions=assumptions,
                uncertainties=uncertainties,
            )
        )

    return impacts
