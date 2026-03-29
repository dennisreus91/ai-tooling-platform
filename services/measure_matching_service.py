from __future__ import annotations

from typing import Any

from schemas import MeasureStatus
from services.config_service import load_json


def _get_nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def match_measures(woningmodel: dict[str, Any]) -> list[MeasureStatus]:
    library = load_json("data/maatregelenbibliotheek.json")["measures"]
    statuses: list[MeasureStatus] = []

    for measure in library:
        metric = measure.get("target_metric")
        current = _get_nested(woningmodel, metric)
        target = measure.get("target_value")
        mode = measure.get("comparison_mode")

        status = "missing"
        reason = "Geen actuele waarde gevonden in woningmodel."

        if current is not None:
            if mode == "equals":
                status = "sufficient" if current == target else "improvable"
            elif mode == "min_gte":
                status = "sufficient" if float(current) >= float(target) else "improvable"
            elif mode == "max_lte":
                status = "sufficient" if float(current) <= float(target) else "improvable"

            reason = f"Vergelijking op {metric} met mode {mode}."

        cap = measure.get("capacity_logic")
        if cap:
            cap_current = _get_nested(woningmodel, cap["field"])
            if cap_current is not None and float(cap_current) < float(cap["min_value"]):
                status = "capacity_limited"
                reason = f"Capaciteitslimiet op {cap['field']}."

        statuses.append(
            MeasureStatus(
                measure_id=measure["id"],
                canonical_name=measure["canonical_name"],
                status=status,
                current_value=current,
                target_value=target,
                reason=reason,
            )
        )
    return statuses
