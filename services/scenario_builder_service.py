from __future__ import annotations

from schemas import MeasureImpact, ScenarioDefinition
from services.config_service import load_json


def build_scenarios(impacts: list[MeasureImpact]) -> list[ScenarioDefinition]:
    templates = load_json("data/scenario_templates.json")["templates"]
    ordered = [impact.measure_id for impact in sorted(impacts, key=lambda x: x.estimated_investment_eur)]
    scenarios: list[ScenarioDefinition] = []

    for template in templates:
        max_measures = int(template.get("max_measures", 5))
        measure_ids = ordered[:max_measures]
        scenarios.append(
            ScenarioDefinition(
                scenario_id=template["id"],
                scenario_name=template["id"],
                measure_ids=measure_ids,
                ordered_measure_ids=measure_ids,
            )
        )

    return scenarios
