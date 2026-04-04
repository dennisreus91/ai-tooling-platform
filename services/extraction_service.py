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


def _coerce_optional_float_in_path(container: dict[str, Any], path: str) -> None:
    value = _get_nested(container, path)
    if value is None:
        return
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str):
        try:
            _set_nested(container, path, float(value.replace(",", ".").strip()))
            return
        except (TypeError, ValueError):
            _set_nested(container, path, None)
            return
    _set_nested(container, path, None)


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
    if not isinstance(meta.get("confidence"), (int, float)):
        meta["confidence"] = 0.0
    for key in ("missing_fields", "assumptions", "uncertainties"):
        if not isinstance(meta.get(key), list):
            meta[key] = []


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


def _coerce_known_field_shapes(data: dict[str, Any]) -> None:
    """
    Null-safe coercie voor velden met bekende vormverschillen uit LLM-output.
    """
    summary_value = data.get("samenvatting_huidige_maatregelen")
    if summary_value is None:
        data["samenvatting_huidige_maatregelen"] = []
    elif isinstance(summary_value, list):
        data["samenvatting_huidige_maatregelen"] = [str(item) for item in summary_value]
    elif isinstance(summary_value, str):
        text = summary_value.strip()
        data["samenvatting_huidige_maatregelen"] = [text] if text else []
    elif isinstance(summary_value, dict):
        flattened: list[str] = []
        for key, value in summary_value.items():
            flattened.append(f"{key}: {value}")
        data["samenvatting_huidige_maatregelen"] = flattened
    else:
        data["samenvatting_huidige_maatregelen"] = [str(summary_value)]

    maatregelen_value = data.get("maatregelen")
    if maatregelen_value is None:
        data["maatregelen"] = []
    elif isinstance(maatregelen_value, dict):
        data["maatregelen"] = [maatregelen_value]
    elif isinstance(maatregelen_value, list):
        normalized_measures: list[dict[str, Any]] = []
        for item in maatregelen_value:
            if isinstance(item, dict):
                normalized_measures.append(item)
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    normalized_measures.append({"maatregel_naam_origineel": text})
        data["maatregelen"] = normalized_measures
    else:
        data["maatregelen"] = []

    if not data["maatregelen"] and data.get("samenvatting_huidige_maatregelen"):
        data["maatregelen"] = [
            {"maatregel_naam_origineel": measure}
            for measure in data["samenvatting_huidige_maatregelen"]
            if isinstance(measure, str) and measure.strip()
        ]

    for measure in data["maatregelen"]:
        quantity_value = measure.get("quantity_value")
        if isinstance(quantity_value, str):
            try:
                measure["quantity_value"] = float(quantity_value.replace(",", ".").strip())
            except (TypeError, ValueError):
                measure["quantity_value"] = None
        elif quantity_value is not None and not isinstance(quantity_value, (int, float)):
            measure["quantity_value"] = None

        quantity_unit = measure.get("quantity_unit")
        if quantity_unit is not None and not isinstance(quantity_unit, str):
            measure["quantity_unit"] = str(quantity_unit)

        quantity_source_field = measure.get("quantity_source_field")
        if quantity_source_field is not None and not isinstance(quantity_source_field, str):
            measure["quantity_source_field"] = str(quantity_source_field)

        quantity_confidence = measure.get("quantity_confidence")
        if quantity_confidence is None:
            measure["quantity_confidence"] = 0.0
        else:
            try:
                measure["quantity_confidence"] = max(0.0, min(1.0, float(quantity_confidence)))
            except (TypeError, ValueError):
                measure["quantity_confidence"] = 0.0

        values = measure.get("maatregel_waarden")
        if values is None:
            measure["maatregel_waarden"] = []
            continue
        if isinstance(values, dict):
            values = [values]
        if not isinstance(values, list):
            measure["maatregel_waarden"] = []
            continue

        normalized_values: list[dict[str, Any]] = []
        for raw_value in values:
            if not isinstance(raw_value, dict):
                continue

            entry = dict(raw_value)
            numeric = entry.get("waarde")
            if isinstance(numeric, str):
                try:
                    entry["waarde"] = float(numeric.replace(",", ".").strip())
                except (TypeError, ValueError):
                    entry["waarde"] = None
            elif not isinstance(numeric, (int, float)) and numeric is not None:
                entry["waarde"] = None

            unit = entry.get("eenheid")
            if unit is not None and not isinstance(unit, str):
                entry["eenheid"] = str(unit)

            conf = entry.get("confidence")
            if conf is None:
                entry["confidence"] = 0.0
            else:
                try:
                    entry["confidence"] = max(0.0, min(1.0, float(conf)))
                except (TypeError, ValueError):
                    entry["confidence"] = 0.0

            normalized_values.append(entry)

        measure["maatregel_waarden"] = normalized_values

    for path in (
        "bouwdelen.dak.oppervlakte_m2",
        "bouwdelen.gevel.oppervlakte_m2",
        "bouwdelen.vloer.oppervlakte_m2",
        "bouwdelen.ramen.oppervlakte_m2",
    ):
        _coerce_optional_float_in_path(data, path)


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
        "woning.aantal_bouwlagen",
        "woning.daktype",
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
    _coerce_known_field_shapes(structured)
    _ensure_extractie_meta(structured)
    _collect_missing_fields(structured)
    _validate_against_mapping_structure(structured)

    return WoningModel.model_validate(structured)
