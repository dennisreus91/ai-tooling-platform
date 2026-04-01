from __future__ import annotations

from copy import deepcopy
from typing import Any

from schemas import ExtractieMeta, WoningModel
from services.config_service import get_assumption_rules


def _append_unique(lst: list[str], value: str) -> None:
    if value not in lst:
        lst.append(value)


def _get_nested(container: dict[str, Any], path: str) -> Any:
    current: Any = container
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested(container: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = container
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _ensure_extractie_meta(model: WoningModel) -> ExtractieMeta:
    if model.extractie_meta is None:
        model.extractie_meta = ExtractieMeta()

    model.extractie_meta.missing_fields = list(model.extractie_meta.missing_fields or [])
    model.extractie_meta.assumptions = list(model.extractie_meta.assumptions or [])
    model.extractie_meta.uncertainties = list(model.extractie_meta.uncertainties or [])
    return model.extractie_meta


def _apply_assumption_rules(data: dict[str, Any], meta: ExtractieMeta) -> None:
    assumption_rules = get_assumption_rules()
    rules = assumption_rules.get("rules", [])

    for rule in rules:
        field = rule.get("field")
        reason = rule.get("reason", "Fallback toegepast.")
        uncertainty_level = rule.get("uncertainty_level", "medium")
        confidence_penalty = float(rule.get("confidence_penalty", 0.0))
        report_as_assumption = bool(rule.get("report_as_assumption", True))

        if not field:
            continue

        current_value = _get_nested(data, field)
        if current_value is not None:
            continue

        _append_unique(meta.missing_fields, field)

        if report_as_assumption:
            _append_unique(
                meta.assumptions,
                f"{field}: geen fallback toegepast. Reden: {reason}",
            )

        _append_unique(
            meta.uncertainties,
            f"{field}: waarde ontbrak; geen hardcoded backup gebruikt ({uncertainty_level}).",
        )
        meta.confidence = max(0.0, round(float(meta.confidence) - confidence_penalty, 4))


def _normalize_numeric_fields(data: dict[str, Any], meta: ExtractieMeta) -> None:
    numeric_paths = [
        "prestatie.current_ep2_kwh_m2",
        "woning.gebruiksoppervlakte_m2",
        "woning.bouwjaar",
        "bouwdelen.dak.rc",
        "bouwdelen.gevel.rc",
        "bouwdelen.vloer.rc",
        "bouwdelen.ramen.u_waarde",
        "bouwdelen.luchtdichting.qv10",
        "installaties.verwarming.rendement",
        "installaties.afgifte.max_aanvoer_temp_c",
        "installaties.regeling.klasse",
        "installaties.tapwater.rendement",
        "installaties.pv.kwp",
        "installaties.pv.max_extra_kwp",
        "installaties.elektra.max_aansluitwaarde_kw",
    ]

    for path in numeric_paths:
        value = _get_nested(data, path)
        if value is None:
            continue

        try:
            if isinstance(value, str):
                value = value.replace(",", ".").strip()
            numeric_value: int | float = float(value)
            if path.endswith("bouwjaar"):
                numeric_value = int(numeric_value)
            _set_nested(data, path, numeric_value)
        except (TypeError, ValueError):
            _set_nested(data, path, None)
            _append_unique(meta.uncertainties, f"{path}: niet parsebaar naar numerieke waarde; op null gezet.")
            _append_unique(meta.missing_fields, path)
            meta.confidence = max(0.0, round(float(meta.confidence) - 0.05, 4))


def _normalize_boolean_fields(data: dict[str, Any], meta: ExtractieMeta) -> None:
    bool_map = {
        "ja": True,
        "nee": False,
        "yes": True,
        "no": False,
        "true": True,
        "false": False,
        "aanwezig": True,
        "niet aanwezig": False,
    }

    boolean_paths = [
        "bouwdelen.ramen.kozijn_isolerend",
        "installaties.regeling.waterzijdig_ingeregeld",
        "installaties.ventilatie.vraaggestuurd",
        "installaties.ventilatie.inregeling_ok",
        "installaties.tapwater.zonneboiler",
        "installaties.tapwater.douche_wtw",
    ]

    for path in boolean_paths:
        value = _get_nested(data, path)
        if value is None or isinstance(value, bool):
            continue

        if isinstance(value, str):
            normalized = bool_map.get(value.strip().lower())
            if normalized is not None:
                _set_nested(data, path, normalized)
                continue

        _set_nested(data, path, None)
        _append_unique(meta.uncertainties, f"{path}: boolean waarde niet eenduidig parseerbaar; op null gezet.")
        _append_unique(meta.missing_fields, path)
        meta.confidence = max(0.0, round(float(meta.confidence) - 0.03, 4))


def _normalize_enums(data: dict[str, Any]) -> None:
    heating_map = {
        "all-electric": "all_electric_warmtepomp",
        "all electric": "all_electric_warmtepomp",
        "all-electric warmtepomp": "all_electric_warmtepomp",
        "elektrische warmtepomp": "all_electric_warmtepomp",
        "hybride": "hybride_warmtepomp",
        "hybride warmtepomp": "hybride_warmtepomp",
        "hr-ketel": "hr_ketel",
        "hr ketel": "hr_ketel",
        "cv-ketel": "hr_ketel",
        "cv ketel": "hr_ketel",
    }
    ventilation_map = {
        "balans": "balansventilatie",
        "wtw": "balans_wtw",
        "balansventilatie": "balansventilatie",
        "balansventilatie met wtw": "balans_wtw",
        "mechanisch": "mechanische_ventilatie",
        "natuurlijk": "natuurlijke_ventilatie",
    }

    heating_value = _get_nested(data, "installaties.verwarming.type")
    if isinstance(heating_value, str):
        normalized = heating_map.get(heating_value.strip().lower())
        if normalized:
            _set_nested(data, "installaties.verwarming.type", normalized)

    ventilation_value = _get_nested(data, "installaties.ventilatie.type")
    if isinstance(ventilation_value, str):
        normalized = ventilation_map.get(ventilation_value.strip().lower())
        if normalized:
            _set_nested(data, "installaties.ventilatie.type", normalized)


def normalize_woningmodel(model: WoningModel) -> WoningModel:
    meta = _ensure_extractie_meta(model)
    data = deepcopy(model.model_dump())

    _normalize_numeric_fields(data, meta)
    _normalize_boolean_fields(data, meta)
    _normalize_enums(data)
    _apply_assumption_rules(data, meta)

    meta.missing_fields = sorted(set(meta.missing_fields))
    meta.assumptions = sorted(set(meta.assumptions))
    meta.uncertainties = sorted(set(meta.uncertainties))
    meta.confidence = max(0.0, min(1.0, float(meta.confidence)))

    data["extractie_meta"] = meta.model_dump()
    return WoningModel.model_validate(data)
