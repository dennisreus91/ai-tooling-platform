from __future__ import annotations

from copy import deepcopy
from typing import Any

from schemas import WoningModel
from services.config_service import get_vabi_mapping, get_woning_schema


def _ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _set_nested(container: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = container
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _get_nested(container: dict[str, Any], path: str) -> Any:
    current: Any = container
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _build_null_safe_template_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Bouw een null-safe basisobject vanuit woningmodel_schema.json.
    Alleen object- en scalarniveaus die voor extractie relevant zijn.
    """
    result: dict[str, Any] = {}
    properties = schema.get("properties", {})

    for key, prop in properties.items():
        prop_type = prop.get("type")

        if prop_type == "object":
            result[key] = _build_null_safe_template_from_schema(prop)
        elif isinstance(prop_type, list):
            if "object" in prop_type:
                result[key] = _build_null_safe_template_from_schema(prop)
            else:
                result[key] = None
        elif prop_type == "array":
            result[key] = []
        else:
            result[key] = None

    return result


def _ensure_extractie_meta(data: dict[str, Any]) -> None:
    if "extractie_meta" not in data or not isinstance(data["extractie_meta"], dict):
        data["extractie_meta"] = {}

    meta = data["extractie_meta"]
    meta.setdefault("confidence", 0.0)
    meta.setdefault("missing_fields", [])
    meta.setdefault("assumptions", [])
    meta.setdefault("uncertainties", [])


def _append_unique(lst: list[str], value: str) -> None:
    if value not in lst:
        lst.append(value)


def _apply_minimum_structure(data: dict[str, Any]) -> dict[str, Any]:
    """
    Merge ruwe payload op een null-safe basisschema.
    """
    schema = get_woning_schema()
    base = _build_null_safe_template_from_schema(schema)

    def merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                merge(dst[key], value)
            else:
                dst[key] = value
        return dst

    return merge(base, data)


def _collect_missing_fields(data: dict[str, Any]) -> None:
    """
    Markeer kritieke velden als missing wanneer ze nog leeg zijn.
    """
    _ensure_extractie_meta(data)
    meta = data["extractie_meta"]

    critical_fields = [
        "prestatie.current_ep2_kwh_m2",
        "prestatie.current_label",
        "woning.gebruiksoppervlakte_m2",
        "woning.type",
        "woning.bouwjaar",
        "installaties.verwarming.type",
        "installaties.ventilatie.type",
    ]

    for field in critical_fields:
        if _get_nested(data, field) is None:
            _append_unique(meta["missing_fields"], field)


def _validate_against_mapping_structure(data: dict[str, Any]) -> None:
    """
    Gebruik vabi_mapping.json niet als parser, maar wel als controle dat
    belangrijke target_fields conceptueel in het model thuishoren.
    """
    _ensure_extractie_meta(data)
    meta = data["extractie_meta"]

    mapping = get_vabi_mapping()
    rules = mapping.get("rules", [])

    for rule in rules:
        target_field = rule.get("target_field")
        required_for = rule.get("required_for", [])
        fallback_behavior = rule.get("fallback_behavior", "null_allowed")

        if not target_field:
            continue

        value = _get_nested(data, target_field)

        if value is None and required_for:
            if fallback_behavior in (
                "use_assumption_rules_and_mark_uncertain",
                "derive_from_ep2_if_missing",
            ):
                _append_unique(
                    meta["uncertainties"],
                    f"{target_field}: niet gevonden in extractie; vervolglaag moet fallback of afleiding toepassen.",
                )


def extract_woningmodel_from_payload(payload: dict[str, Any]) -> WoningModel:
    """
    Zet een ruwe payload (bijv. Gemini-output of tussengevormde extractie)
    om naar een null-safe WoningModel.

    Deze functie doet in de POC:
    - null-safe structuur aanbrengen via woningmodel_schema.json
    - extractie_meta garanderen
    - kritieke missende velden markeren
    - onzekerheden registreren op basis van vabi_mapping.json
    - daarna valideren tegen WoningModel

    Deze functie doet NIET:
    - echte documentextractie uit Vabi-bestanden
    - aannameregels toepassen
    - terminologie-normalisatie
    Dat gebeurt in vervolgstappen zoals normalization_service.py.
    """
    if not isinstance(payload, dict):
        raise ValueError("extract_woningmodel_from_payload verwacht een dictionary payload.")

    raw = deepcopy(payload)
    structured = _apply_minimum_structure(raw)
    _ensure_extractie_meta(structured)
    _collect_missing_fields(structured)
    _validate_against_mapping_structure(structured)

    return WoningModel.model_validate(structured)
