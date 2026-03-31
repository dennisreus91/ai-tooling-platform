from __future__ import annotations

from typing import Any

from schemas import MeasureImpact, ScenarioDefinition
from services.config_service import (
    get_measure_relations,
    get_measures_library,
    get_scenario_templates,
)


def _order_by_trias_and_priority(measure_ids: list[str], measure_index: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        measure_ids,
        key=lambda mid: (
            int(measure_index.get(mid, {}).get("trias_step", 99)),
            float(measure_index.get(mid, {}).get("calculation_priority", 99)),
            mid,
        ),
    )


def _collect_candidates(impacts: list[MeasureImpact], measure_index: dict[str, dict[str, Any]]) -> list[str]:
    candidates = [i.measure_id for i in sorted(impacts, key=lambda x: (-x.logic_score, x.estimated_investment_eur))]
    return [mid for mid in candidates if measure_index.get(mid, {}).get("scenario_allowed", False)]


def _apply_dependency_rules(measure_ids: list[str], relations: dict[str, Any], measure_index: dict[str, dict[str, Any]]) -> list[str]:
    selected = set(measure_ids)

    for rule in relations.get("dependency_rules", []):
        measure_id = rule.get("measure_id")
        if measure_id not in selected:
            continue

        for req in rule.get("requires", []):
            if req in measure_index:
                selected.add(req)

        any_groups = rule.get("requires_any_of", [])
        for group in any_groups:
            if not isinstance(group, list) or not group:
                continue
            if any(g in selected for g in group):
                continue
            for candidate in group:
                if candidate in measure_index:
                    selected.add(candidate)
                    break

    # extra dependencies from measure library
    for mid in list(selected):
        for req in measure_index.get(mid, {}).get("dependencies", []):
            if req in measure_index:
                selected.add(req)

    return list(selected)


def _apply_mutual_exclusions(measure_ids: list[str], relations: dict[str, Any], measure_index: dict[str, dict[str, Any]]) -> list[str]:
    selected = set(measure_ids)

    for rule in relations.get("mutual_exclusion_rules", []):
        group = [m for m in rule.get("measures", []) if m in selected]
        if len(group) <= 1:
            continue

        # keep best: lower calculation_priority then lower trias_step
        best = sorted(
            group,
            key=lambda mid: (
                float(measure_index.get(mid, {}).get("calculation_priority", 99)),
                int(measure_index.get(mid, {}).get("trias_step", 99)),
                mid,
            ),
        )[0]

        for mid in group:
            if mid != best:
                selected.discard(mid)

    return list(selected)


def _apply_ordering_rules(measure_ids: list[str], relations: dict[str, Any], measure_index: dict[str, dict[str, Any]]) -> list[str]:
    ordered = _order_by_trias_and_priority(measure_ids, measure_index)

    for rule in relations.get("ordering_rules", []):
        before = rule.get("before")
        after = rule.get("after")
        if before not in ordered or after not in ordered:
            continue

        i_before = ordered.index(before)
        i_after = ordered.index(after)
        if i_before > i_after:
            ordered.pop(i_before)
            i_after = ordered.index(after)
            ordered.insert(i_after, before)

    return ordered


def _pick_for_template(
    template: dict[str, Any],
    candidates: list[str],
    measure_index: dict[str, dict[str, Any]],
) -> list[str]:
    preferred_steps = template.get("prefer_trias_steps", [1, 2, 3])
    max_measures = int(template.get("max_measures", 5))

    ranked = sorted(
        candidates,
        key=lambda mid: (
            preferred_steps.index(measure_index.get(mid, {}).get("trias_step"))
            if measure_index.get(mid, {}).get("trias_step") in preferred_steps
            else 99,
            float(measure_index.get(mid, {}).get("calculation_priority", 99)),
            mid,
        ),
    )

    return ranked[:max_measures]


def build_scenarios(impacts: list[MeasureImpact]) -> list[ScenarioDefinition]:
    templates = get_scenario_templates().get("templates", [])
    relations = get_measure_relations()
    library = get_measures_library().get("measures", [])
    measure_index = {m["id"]: m for m in library}

    candidates = _collect_candidates(impacts, measure_index)
    if not candidates:
        return []

    scenarios: list[ScenarioDefinition] = []

    for template in templates:
        scenario_id = template.get("id")
        if not scenario_id:
            continue

        selected = _pick_for_template(template, candidates, measure_index)
        selected = _apply_dependency_rules(selected, relations, measure_index)
        selected = _apply_mutual_exclusions(selected, relations, measure_index)
        ordered = _apply_ordering_rules(selected, relations, measure_index)

        max_measures = int(template.get("max_measures", len(ordered)))
        ordered = ordered[:max_measures]

        scenarios.append(
            ScenarioDefinition(
                scenario_id=scenario_id,
                scenario_name=str(template.get("description") or scenario_id),
                measure_ids=list(ordered),
                ordered_measure_ids=list(ordered),
            )
        )

    return scenarios
