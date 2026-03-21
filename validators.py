from typing import List

from schemas import Constraints


_ALLOWED_TARGET_LABELS = {
    "next_step": "next_step",
    "nextstep": "next_step",
    "next-step": "next_step",
    "a": "A",
    "b": "B",
    "c": "C",
}


def _normalize_target_label(target_label: str) -> str:
    value = target_label.strip().lower()

    if value not in _ALLOWED_TARGET_LABELS:
        raise ValueError(
            "target_label must be one of: next_step, A, B, C."
        )

    return _ALLOWED_TARGET_LABELS[value]


def _normalize_required_measures(required_measures: str | list[str] | None) -> List[str]:
    if required_measures is None:
        return []

    if isinstance(required_measures, str):
        candidates = [required_measures]
    elif isinstance(required_measures, list):
        candidates = required_measures
    else:
        raise ValueError(
            "required_measures must be a string, a list of strings, or null."
        )

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


def normalize_constraints(
    target_label: str,
    required_measures: str | list[str] | None,
) -> Constraints:
    normalized_target_label = _normalize_target_label(target_label)
    normalized_required_measures = _normalize_required_measures(required_measures)

    return Constraints(
        target_label=normalized_target_label,
        required_measures=normalized_required_measures,
    )
