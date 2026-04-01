from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schemas import ScenarioDefinition, ScenarioResult
from services.config_service import (
    get_label_boundaries,
    get_measures_library,
    get_value_impact,
)


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _label_rank(label: str) -> int:
    config = get_label_boundaries()
    ranks = config.get("label_rank", {})
    return int(ranks.get(label, 999))


def _estimate_measure_ep2_reduction(measure: dict[str, Any]) -> float:
    """
    POC-heuristiek per maatregel.
    Niet de definitieve waarheid, maar beter onderbouwd dan een vaste factor per maatregel.
    """
    trias_step = measure.get("trias_step")
    impact_path = measure.get("impact_path", [])
    comparison_mode = measure.get("comparison_mode")
    category = measure.get("category", "")

    # Basis per Trias-stap
    if trias_step == 1:
        base = 10.0
    elif trias_step == 2:
        base = 14.0
    else:
        base = 4.0

    # Category nuance
    if category in {"schil", "glas"}:
        base += 3.0
    elif category in {"duurzame_installatie", "duurzame_opwek"}:
        base += 4.0
    elif category in {"efficient_fossiel", "regeling", "ventilatie"}:
        base += 1.5

    # Impact path nuance
    if isinstance(impact_path, list):
        joined = " ".join(str(x).lower() for x in impact_path)

        if "sterke" in joined or "fors" in joined or "major" in joined:
            base += 3.0
        if "lagere warmtebehoefte" in joined:
            base += 2.0
        if "lagere ep2" in joined:
            base += 1.5
        if "kleine ep2-reductie" in joined or "small" in joined:
            base -= 1.0
        if "enabler" in joined:
            base -= 1.5

    # Comparison nuance
    if comparison_mode in {"max_lte", "min_gte"}:
        base += 1.0

    return round(max(base, 1.0), 2)


def _estimate_measure_investment(measure: dict[str, Any]) -> float:
    per_unit = _safe_float(measure.get("investment_per_unit_eur"))
    if per_unit is not None and per_unit > 0:
        return round(per_unit, 2)

    bandwidth = measure.get("investment_bandwidth_eur", {})
    low = _safe_float(bandwidth.get("min"))
    high = _safe_float(bandwidth.get("max"))
    if low is not None and high is not None and low > 0 and high > 0:
        return round((low + high) / 2.0, 2)

    return 0.0


def _estimate_monthly_saving(total_reduction_ep2: float, measure_count: int) -> float:
    """
    Indicatieve maandbesparing voor rapportage.
    """
    base = total_reduction_ep2 * 1.2
    bonus = measure_count * 3.0
    return round(max(base + bonus, 0.0), 2)


def _estimate_property_value_gain(current_label: str, new_label: str) -> float:
    """
    Indicatieve waardestijging zonder actuele woningwaarde-input:
    gebruik flat adjustment op labelsprong.
    """
    config = get_value_impact()
    jump_table = config.get("label_jump_flat_adjustment_eur", {})

    current_rank = _label_rank(current_label)
    new_rank = _label_rank(new_label)

    if current_rank == 999 or new_rank == 999:
        return 0.0

    jump = max(0, current_rank - new_rank)  # beter label = lagere rank
    if jump <= 0:
        return 0.0

    # als sprong groter is dan tabel, neem hoogste beschikbare
    if str(jump) in jump_table:
        return float(jump_table[str(jump)])

    numeric_keys = sorted(int(k) for k in jump_table.keys()) if jump_table else []
    if not numeric_keys:
        return 0.0

    max_key = max(numeric_keys)
    return float(jump_table[str(max_key)])


class ScenarioCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        scenario: ScenarioDefinition,
        current_ep2: float,
        current_label: str | None = None,
    ) -> ScenarioResult:
        raise NotImplementedError


class GeminiScenarioCalculator(ScenarioCalculator):
    """
    Tijdelijke POC-calculator.

    Deze klasse gebruikt nog geen echte Gemini API-call, maar is inhoudelijk opgezet
    als vervangbare calculatorlaag. De heuristiek gebruikt de maatregelenbibliotheek
    en deterministische labelmapping. Later kan deze klasse vervangen of uitgebreid worden
    met echte Gemini-doorrekening op basis van methodiekdocumenten en scenario-context.
    """

    def __init__(self) -> None:
        library = get_measures_library()["measures"]
        self.measure_index = {m["id"]: m for m in library}

    def calculate(
        self,
        scenario: ScenarioDefinition,
        current_ep2: float,
        current_label: str | None = None,
    ) -> ScenarioResult:
        selected_measures = scenario.ordered_measure_ids or scenario.measure_ids
        current_ep2_numeric = _safe_float(current_ep2)
        if current_ep2_numeric is None:
            raise ValueError(
                "current_ep2_kwh_m2 ontbreekt of is ongeldig; scenario-calculatie gebruikt geen backupwaarde."
            )
        current_ep2 = current_ep2_numeric

        if current_label is None:
            current_label = _label_from_ep2(current_ep2)

        total_reduction = 0.0
        total_investment = 0.0
        assumptions: list[str] = []
        uncertainties: list[str] = []

        for measure_id in selected_measures:
            measure = self.measure_index.get(measure_id)
            if not measure:
                uncertainties.append(
                    f"Maatregel '{measure_id}' ontbreekt in maatregelenbibliotheek en is overgeslagen in de POC-doorrekening."
                )
                continue

            total_reduction += _estimate_measure_ep2_reduction(measure)
            estimated_investment = _estimate_measure_investment(measure)
            total_investment += estimated_investment
            if estimated_investment == 0.0:
                uncertainties.append(
                    f"Maatregel '{measure['canonical_name']}' heeft geen investering in de bibliotheek; geen vervangende backupwaarde toegepast."
                )

            assumptions.append(
                f"Maatregel '{measure['canonical_name']}' is indicatief doorgerekend op basis van bibliotheekkenmerken zoals trias_step, category en impact_path."
            )

        # zachte afnemende meeropbrengst bij grotere pakketten
        diminishing_factor = 1.0
        if len(selected_measures) >= 4:
            diminishing_factor = 0.92
        if len(selected_measures) >= 6:
            diminishing_factor = 0.88

        total_reduction = round(total_reduction * diminishing_factor, 2)

        # voorkom onrealistisch lage EP2 in de POC
        new_ep2 = round(max(-5.0, current_ep2 - total_reduction), 2)
        new_label = _label_from_ep2(new_ep2)

        monthly_savings = _estimate_monthly_saving(total_reduction, len(selected_measures))
        property_value_gain = _estimate_property_value_gain(current_label, new_label)

        assumptions.append(
            "Scenario-doorrekening is uitgevoerd met de tijdelijke Gemini-POC-calculatorlaag en niet met een officiële NTA 8800 rekenkern of Vabi/Uniec-koppeling."
        )
        assumptions.append(
            "Labeltoekenning is deterministisch gevalideerd op basis van labelgrenzen.json."
        )

        uncertainties.append(
            "De EP2-reductie is een POC-inschatting en niet de uitkomst van een officiële softwareberekening."
        )
        uncertainties.append(
            "Werkelijke investering, besparing en labelsprong zijn afhankelijk van projectspecifieke woningdata, oppervlaktes en installatiedetails."
        )

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            expected_ep2_kwh_m2=new_ep2,
            expected_label=new_label,
            selected_measures=selected_measures,
            total_investment_eur=round(total_investment, 2),
            monthly_savings_eur=monthly_savings,
            expected_property_value_gain_eur=round(property_value_gain, 2),
            assumptions=assumptions,
            uncertainties=uncertainties,
        )
