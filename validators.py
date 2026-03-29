from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from pydantic import ValidationError

from schemas import Constraints, ExtractedReport, Measure, WoningModel

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
    try:
        report = data if isinstance(data, ExtractedReport) else ExtractedReport.model_validate(data)
    except ValidationError as exc:
        has_ep2_error = any(err.get("loc") == ("current_ep2_kwh_m2",) for err in exc.errors())
        if has_ep2_error:
            raise ValueError("missing_ep2_data: current_ep2_kwh_m2 ontbreekt of is ongeldig.") from exc
        raise ValueError(f"Invalid extracted report data: {exc}") from exc

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


def validate_woningmodel(data: dict[str, Any]) -> WoningModel:
    try:
        model = WoningModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid_woningmodel: {exc}") from exc

    model.extractie_meta.missing_fields = sorted(set(model.extractie_meta.missing_fields))
    model.extractie_meta.assumptions = sorted(set(model.extractie_meta.assumptions))
    return model


def label_from_ep2(ep2_value: float, labelgrenzen_path: str = "data/labelgrenzen.json") -> str:
    boundaries = json.loads(Path(labelgrenzen_path).read_text())["boundaries"]
    for rule in boundaries:
        min_v = rule.get("ep2_min_inclusive", float("-inf"))
        max_v = rule.get("ep2_max_exclusive", float("inf"))
        if ep2_value >= min_v and ep2_value < max_v:
            return rule["label"]
    return "G"


def label_rank(label: str, labelgrenzen_path: str = "data/labelgrenzen.json") -> int:
    order = json.loads(Path(labelgrenzen_path).read_text())["order_best_to_worst"]
    normalized = label.strip().upper()
    if normalized in order:
        return order.index(normalized)
    first = normalized[0] if normalized else "G"
    for idx, value in enumerate(order):
        if value.startswith(first):
            return idx
    return len(order) - 1
