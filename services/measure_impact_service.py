from __future__ import annotations

from schemas import MeasureImpact, MeasureStatus
from services.config_service import load_json


def screen_measure_impacts(statuses: list[MeasureStatus]) -> list[MeasureImpact]:
    library = {m["id"]: m for m in load_json("data/maatregelenbibliotheek.json")["measures"]}
    impacts: list[MeasureImpact] = []
    for status in statuses:
        if status.status not in {"missing", "improvable"}:
            continue
        measure = library[status.measure_id]
        invest = float(measure.get("investment_per_unit_eur", 1000))
        factor = 12.0 if measure.get("trias_step") == 1 else 18.0 if measure.get("trias_step") == 2 else 6.0
        impacts.append(
            MeasureImpact(
                measure_id=status.measure_id,
                canonical_name=status.canonical_name,
                estimated_ep2_reduction=factor,
                estimated_investment_eur=invest,
                logic_score=0.75,
                assumptions=["Indicatieve screening op bibliotheek-niveau."],
                uncertainties=["Definitieve EP2-effecten vereisen detailberekening."],
            )
        )
    return impacts
