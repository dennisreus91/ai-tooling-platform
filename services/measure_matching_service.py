from __future__ import annotations

from typing import Any

from schemas import MeasureStatus
from services.config_service import get_measures_library


def _get_nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except (TypeError, ValueError):
        return None


def _compare_value(
    current: Any,
    target: Any,
    mode: str | None,
) -> tuple[str, str]:
    """
    Retourneert status + reason op basis van comparison_mode.
    Mogelijke hoofdstatussen hier:
    - sufficient
    - improvable
    - missing
    """
    if current is None:
        return "missing", "Geen actuele waarde gevonden in woningmodel."

    if mode == "equals":
        status = "sufficient" if current == target else "improvable"
        return status, f"Vergelijking op exactheid: huidige waarde '{current}' versus doelwaarde '{target}'."

    if mode == "min_gte":
        current_num = _safe_float(current)
        target_num = _safe_float(target)
        if current_num is None or target_num is None:
            return "missing", "Huidige of doelwaarde kon niet numeriek worden geïnterpreteerd."
        status = "sufficient" if current_num >= target_num else "improvable"
        return status, f"Vergelijking met ondergrens: huidige waarde {current_num} versus minimale doelwaarde {target_num}."

    if mode == "max_lte":
        current_num = _safe_float(current)
        target_num = _safe_float(target)
        if current_num is None or target_num is None:
            return "missing", "Huidige of doelwaarde kon niet numeriek worden geïnterpreteerd."
        status = "sufficient" if current_num <= target_num else "improvable"
        return status, f"Vergelijking met bovengrens: huidige waarde {current_num} versus maximale doelwaarde {target_num}."

    return "missing", f"Onbekende comparison_mode '{mode}' of onvoldoende informatie voor vergelijking."


def _determine_not_applicable(measure: dict[str, Any]) -> tuple[bool, str]:
    """
    Basisfilter voor maatregelen die niet in deze POC meegenomen mogen worden.
    """
    if not measure.get("label_relevant", False):
        return True, "Maatregel is niet labelrelevant binnen de POC-scope."

    if not measure.get("scenario_allowed", False):
        return True, "Maatregel is niet toegestaan voor scenario-opbouw binnen de POC-scope."

    return False, ""


def _apply_capacity_logic(
    woningmodel: dict[str, Any],
    measure: dict[str, Any],
    current_status: str,
    current_reason: str,
) -> tuple[str, str]:
    """
    Past capacity_logic toe indien aanwezig.
    Alleen overschrijven naar capacity_limited als er voldoende harde informatie is.
    """
    cap = measure.get("capacity_logic")
    if not cap:
        return current_status, current_reason

    field = cap.get("field")
    min_value = cap.get("min_value")
    behavior_if_missing = cap.get("behavior_if_missing", "ignore")

    if not field or min_value is None:
        return current_status, current_reason

    cap_current = _get_nested(woningmodel, field)
    cap_current_num = _safe_float(cap_current)
    min_value_num = _safe_float(min_value)

    if cap_current is None or cap_current_num is None or min_value_num is None:
        # In deze stap geen hard capacity_limited maken bij onbekende waarden.
        # Dat moet eventueel later als onzekerheid in scenarioanalyse terugkomen.
        if behavior_if_missing == "flag_uncertain":
            return current_status, current_reason + f" Capaciteit op '{field}' is onbekend en moet later als onzekerheid worden meegenomen."
        return current_status, current_reason

    if cap_current_num < min_value_num:
        return "capacity_limited", f"Capaciteitslimiet bereikt op '{field}': huidige waarde {cap_current_num}, minimale vereiste {min_value_num}."

    return current_status, current_reason


def _normalize_woningmodel_input(woningmodel: Any) -> dict[str, Any]:
    """
    Ondersteun zowel dict-input als Pydantic model input.
    """
    if isinstance(woningmodel, dict):
        return woningmodel
    if hasattr(woningmodel, "model_dump"):
        return woningmodel.model_dump()
    raise TypeError("match_measures verwacht een dict of een Pydantic-model met model_dump().")


def match_measures(woningmodel: Any) -> list[MeasureStatus]:
    """
    Vergelijk huidige woningstatus met maatregelenbibliotheek en bepaal per maatregel:
    - missing
    - improvable
    - sufficient
    - not_applicable
    - capacity_limited

    Deze functie is deterministisch en gebruikt alleen configuratie uit JSON.
    """
    woningdata = _normalize_woningmodel_input(woningmodel)
    library = get_measures_library()["measures"]

    statuses: list[MeasureStatus] = []

    for measure in library:
        measure_id = measure["id"]
        canonical_name = measure["canonical_name"]
        metric = measure.get("target_metric")
        target = measure.get("target_value")
        mode = measure.get("comparison_mode")
        allowed_statuses = set(measure.get("status_output_types", []))

        # 1. Eerst bepalen of maatregel buiten scope / niet toepasbaar is
        is_not_applicable, not_applicable_reason = _determine_not_applicable(measure)
        if is_not_applicable:
            status = "not_applicable"
            reason = not_applicable_reason
            current = _get_nested(woningdata, metric) if metric else None
        else:
            # 2. Waarde ophalen en hoofdvergelijking doen
            current = _get_nested(woningdata, metric) if metric else None
            status, reason = _compare_value(current, target, mode)

            # 3. Capaciteitslogica toepassen
            status, reason = _apply_capacity_logic(woningdata, measure, status, reason)

        # 4. Status begrenzen op wat deze maatregel mag teruggeven
        if allowed_statuses and status not in allowed_statuses:
            if "improvable" in allowed_statuses and status == "missing":
                # Voor sommige maatregelen is "missing" feitelijk een vorm van improvable
                status = "improvable"
                reason += " Status aangepast naar 'improvable' omdat 'missing' niet als toegestane maatregelstatus is geconfigureerd."
            elif "missing" in allowed_statuses:
                status = "missing"
                reason += " Status aangepast naar 'missing' volgens toegestane maatregelstatussen."
            elif "not_applicable" in allowed_statuses:
                status = "not_applicable"
                reason += " Status aangepast naar 'not_applicable' volgens toegestane maatregelstatussen."
            else:
                # Laat status dan ongemoeid, maar markeer reden
                reason += " Let op: status valt buiten de geconfigureerde status_output_types."

        statuses.append(
            MeasureStatus(
                measure_id=measure_id,
                canonical_name=canonical_name,
                status=status,
                current_value=current,
                target_value=target,
                reason=reason,
            )
        )

    return statuses
