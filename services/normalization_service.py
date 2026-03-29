from __future__ import annotations

from copy import deepcopy
from typing import Any

from schemas import WoningModel
from services.config_service import (
    get_assumption_rules,
)


def _ensure_extractie_meta(model: WoningModel) -> None:
    """
    Zorgt dat extractie_meta altijd de vereiste lijsten/velden bevat.
    """
    if model.extractie_meta is None:
        model.extractie_meta = {}

    model.extractie_meta.setdefault("confidence", 1.0)
    model.extractie_meta.setdefault("missing_fields", [])
    model.extractie_meta.setdefault("assumptions", [])
    model.extractie_meta.setdefault("uncertainties", [])


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


def _apply_assumption_rules(data: dict[str, Any], model: WoningModel) -> None:
    """
    Past conservatieve fallbackregels toe vanuit aannameregels.json.
    """
    assumption_rules = get_assumption_rules()
    rules = assumption_rules.get("rules", [])

    for rule in rules:
        field = rule.get("field")
        fallback = rule.get("fallback")
        reason = rule.get("reason", "Fallback toegepast.")
        uncertainty_level = rule.get("uncertainty_level", "medium")
        confidence_penalty = float(rule.get("confidence_penalty", 0.0))
        report_as_assumption = bool(rule.get("report_as_assumption", True))

        if not field:
            continue

        current_value = _get_nested(data, field)

        if current_value is None:
            _set_nested(data, field, fallback)
            _append_unique(model.extractie_meta["missing_fields"], field)

            if report_as_assumption:
                _append_unique(
                    model.extractie_meta["assumptions"],
                    f"{field}: fallback '{fallback}' toegepast. Reden: {reason}",
                )

            _append_unique(
                model.extractie_meta["uncertainties"],
                f"{field}: waarde ontbrak, conservatieve aanname toegepast ({uncertainty_level}).",
            )

            current_confidence = float(model.extractie_meta.get("confidence", 1.0))
            model.extractie_meta["confidence"] = max(
                0.0, round(current_confidence - confidence_penalty, 4)
            )


def _normalize_numeric_fields(data: dict[str, Any], model: WoningModel) -> None:
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
            numeric_value = float(value)
            if path.endswith("bouwjaar"):
                numeric_value = int(numeric_value)
            _set_nested(data, path, numeric_value)
        except (TypeError, ValueError):
            _set_nested(data, path, None)
            _append_unique(
                model.extractie_meta["uncertainties"],
                f"{path}: niet parsebaar naar numerieke waarde; op null gezet.",
            )
            _append_unique(model.extractie_meta["missing_fields"], path)

            current_confidence = float(model.extractie_meta.get("confidence", 1.0))
            model.extractie_meta["confidence"] = max(
                0.0, round(current_confidence - 0.05, 4)
            )


def _normalize_boolean_fields(data: dict[str, Any], model: WoningModel) -> None:
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
        if value is None:
            continue

        if isinstance(value, bool):
            continue

        if isinstance(value, str):
            normalized = bool_map.get(value.strip().lower())
            if normalized is not None:
                _set_nested(data, path, normalized)
                continue

        _set_nested(data, path, None)
        _append_unique(
            model.extractie_meta["uncertainties"],
            f"{path}: boolean waarde niet eenduidig parseerbaar; op null gezet.",
        )
        _append_unique(model.extractie_meta["missing_fields"], path)

        current_confidence = float(model.extractie_meta.get("confidence", 1.0))
        model.extractie_meta["confidence"] = max(
            0.0, round(current_confidence - 0.03, 4)
        )


def _normalize_enums(data: dict[str, Any], model: WoningModel) -> None:
    """
    Normaliseer terminologie zodat deze beter aansluit op maatregelenbibliotheek.json.
    """
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

    heating_path = "installaties.verwarming.type"
    ventilation_path = "installaties.ventilatie.type"

    heating_value = _get_nested(data, heating_path)
    if isinstance(heating_value, str):
        normalized = heating_map.get(heating_value.strip().lower())
        if normalized:
            _set_nested(data, heating_path, normalized)

    ventilation_value = _get_nested(data, ventilation_path)
    if isinstance(ventilation_value, str):
        normalized = ventilation_map.get(ventilation_value.strip().lower())
        if normalized:
            _set_nested(data, ventilation_path, normalized)


def _deduplicate_meta(model: WoningModel) -> None:
    model.extractie_meta["missing_fields"] = sorted(
        set(model.extractie_meta.get("missing_fields", []))
    )
    model.extractie_meta["assumptions"] = sorted(
        set(model.extractie_meta.get("assumptions", []))
    )
    model.extractie_meta["uncertainties"] = sorted(
        set(model.extractie_meta.get("uncertainties", []))
    )


def normalize_woningmodel(model: WoningModel) -> WoningModel:
    """
    Normaliseer het woningmodel zodat:
    - numerieke en boolean velden schoon zijn
    - terminologie aansluit op de maatregelenbibliotheek
    - fallbackregels uit aannameregels.json worden toegepast
    - assumptions, missing_fields en uncertainties expliciet worden vastgelegd
    """
    _ensure_extractie_meta(model)

    # Werk op een gewone dict-structuur om nested paths generiek te kunnen behandelen
    data = deepcopy(model.model_dump() if hasattr(model, "model_dump") else dict(model))

    _normalize_numeric_fields(data, model)
    _normalize_boolean_fields(data, model)
    _normalize_enums(data, model)
    _apply_assumption_rules(data, model)
    _deduplicate_meta(model)

    # Synchroniseer terug naar model
    for key, value in data.items():
        setattr(model, key, value)

    # Confidence clamp
    confidence = float(model.extractie_meta.get("confidence", 1.0))
    model.extractie_meta["confidence"] = max(0.0, min(1.0, confidence))

    return model
