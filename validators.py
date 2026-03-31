from __future__ import annotations

from typing import Any, List

from pydantic import ValidationError

from schemas import Constraints, ExtractedReport, Measure, WoningModel
from services.config_service import get_label_boundaries


_ALLOWED_TARGET_LABELS = {
    "next_step": "next_step",
    "nextstep": "next_step",
    "next-step": "next_step",
    "a": "A",
    "b": "B",
    "c": "C",
    "d": "D",
    "e": "E",
    "f": "F",
    "g": "G",
}


def _normalize_target_label(target_label: str) -> str:
    if not isinstance(target_label, str):
        raise ValueError("target_label must be a string.")

    value = target_label.strip().lower()
    if value not in _ALLOWED_TARGET_LABELS:
        raise ValueError("target_label must be one of: next_step, A, B, C, D, E, F, G.")
    return _ALLOWED_TARGET_LABELS[value]


def _normalize_required_measures(required_measures: str | list[str] | None) -> List[str]:
    if required_measures is None:
        return []

    candidates = [required_measures] if isinstance(required_measures, str) else required_measures
    if not isinstance(candidates, list):
        raise ValueError("required_measures must be a string, a list of strings, or null.")

    normalized: List[str] = []
    seen: set[str] = set()

    for item in candidates:
        if not isinstance(item, str):
            raise ValueError("required_measures must only contain strings.")
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(cleaned)

    return normalized


def normalize_constraints(target_label: str, required_measures: str | list[str] | None) -> Constraints:
    return Constraints(
        target_label=_normalize_target_label(target_label),
        required_measures=_normalize_required_measures(required_measures),
    )


def validate_extract(data: dict | ExtractedReport) -> ExtractedReport:
    """
    Legacy/compatibility validatie voor oudere ExtractedReport-flow.
    Houdt de bestaande validatie in stand, maar blijft strikt deterministisch.
    """
    try:
        report = data if isinstance(data, ExtractedReport) else ExtractedReport.model_validate(data)
    except ValidationError as exc:
        has_ep2_error = any(err.get("loc") == ("current_ep2_kwh_m2",) for err in exc.errors())
        if has_ep2_error:
            raise ValueError("missing_ep2_data: current_ep2_kwh_m2 ontbreekt of is ongeldig.") from exc
        raise ValueError(f"invalid_extracted_report: {exc}") from exc

    valid_measures: List[Measure] = []
    notes = list(report.notes)

    for raw_measure in report.measures:
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure.model_validate(raw_measure)

        if measure.cost < 0:
            notes.append(f"Measure '{measure.name}' was discarded because cost was negative.")
            continue

        if measure.score_gain <= 0:
            notes.append(f"Measure '{measure.name}' was discarded because score_gain was not positive.")
            continue

        valid_measures.append(measure)

    return ExtractedReport(
        current_label=report.current_label,
        current_score=report.current_score,
        current_ep2_kwh_m2=report.current_ep2_kwh_m2,
        measures=valid_measures,
        notes=notes,
    )


def validate_woningmodel(data: dict[str, Any] | WoningModel) -> WoningModel:
    """
    Validatie voor het flexibele woningmodel.
    Deze validatie moet null-safe blijven:
    ontbrekende inhoudelijke velden mogen geen harde fout geven,
    maar technische structuurfouten wel.
    """
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    if isinstance(data, dict):
        meta = data.setdefault("extractie_meta", {})
        confidence = meta.get("confidence")
        if confidence is not None:
            try:
                confidence_f = float(confidence)
                meta["confidence"] = max(0.0, min(1.0, confidence_f))
            except (TypeError, ValueError):
                meta["confidence"] = 0.0

    try:
        model = data if isinstance(data, WoningModel) else WoningModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid_woningmodel: {exc}") from exc

    # Deduplicatie van extractiemeta
    model.extractie_meta.missing_fields = _dedupe(model.extractie_meta.missing_fields)
    model.extractie_meta.assumptions = _dedupe(model.extractie_meta.assumptions)
    model.extractie_meta.uncertainties = _dedupe(model.extractie_meta.uncertainties)
    model.extractie_meta.source_sections_found = _dedupe(model.extractie_meta.source_sections_found)

    # Confidence clamp
    if model.extractie_meta.confidence < 0:
        model.extractie_meta.confidence = 0.0
    elif model.extractie_meta.confidence > 1:
        model.extractie_meta.confidence = 1.0

    # Minimale inhoudelijke checks zonder hard te falen op missende velden
    if model.prestatie.current_ep2_kwh_m2 is None:
        if "prestatie.current_ep2_kwh_m2" not in model.extractie_meta.missing_fields:
            model.extractie_meta.missing_fields.append("prestatie.current_ep2_kwh_m2")

    if model.prestatie.current_label is None and model.prestatie.current_ep2_kwh_m2 is None:
        model.extractie_meta.uncertainties.append(
            "Zowel current_label als current_ep2_kwh_m2 ontbreken; labelduiding vereist aannames of latere afleiding."
        )

    # Opnieuw dedupliceren na aanvulling
    model.extractie_meta.missing_fields = _dedupe(model.extractie_meta.missing_fields)
    model.extractie_meta.uncertainties = _dedupe(model.extractie_meta.uncertainties)

    return model


def _get_label_rank_map() -> dict[str, int]:
    config = get_label_boundaries()
    ranks = config.get("label_rank")
    if not isinstance(ranks, dict) or not ranks:
        raise ValueError("labelgrenzen.json bevat geen geldige label_rank mapping.")
    return ranks


def _get_label_boundaries() -> list[dict[str, Any]]:
    config = get_label_boundaries()
    boundaries = config.get("boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        raise ValueError("labelgrenzen.json bevat geen geldige boundaries.")
    return boundaries


def label_from_ep2(ep2_value: float) -> str:
    """
    Deterministische labelmapping op basis van labelgrenzen.json.
    """
    try:
        ep2 = float(ep2_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("label_from_ep2 verwacht een numerieke EP2-waarde.") from exc

    boundaries = _get_label_boundaries()

    for rule in boundaries:
        min_v = rule.get("ep2_min_inclusive")
        max_v = rule.get("ep2_max_exclusive")

        lower_ok = True if min_v is None else ep2 >= float(min_v)
        upper_ok = True if max_v is None else ep2 < float(max_v)

        if lower_ok and upper_ok:
            return str(rule["label"])

    raise ValueError(f"Geen labelgrens gevonden voor EP2-waarde {ep2}.")


def label_rank(label: str) -> int:
    """
    Deterministische labelrang:
    lager getal = beter label.
    """
    if not isinstance(label, str):
        raise ValueError("label_rank verwacht een stringlabel.")

    normalized = label.strip().upper()
    ranks = _get_label_rank_map()

    if normalized in ranks:
        return int(ranks[normalized])

    raise ValueError(f"Onbekend energielabel '{label}' voor label_rank().")


def label_meets_target(expected_label: str, target_label: str) -> bool:
    """
    Controleer of een verwacht label voldoet aan een doel-label.
    Lager rank-getal = beter label.
    """
    if target_label == "next_step":
        raise ValueError("label_meets_target ondersteunt geen 'next_step'; behandel dat in hogere businesslogica.")

    return label_rank(expected_label) <= label_rank(target_label)


def next_better_label(label: str) -> str | None:
    """
    Geef het eerstvolgende betere label terug op basis van labelgrenzen.json.
    """
    config = get_label_boundaries()
    mapping = config.get("selection_helpers", {}).get("next_better_label", {})
    normalized = label.strip().upper()

    if normalized not in mapping:
        raise ValueError(f"Onbekend energielabel '{label}' voor next_better_label().")

    return mapping[normalized]
