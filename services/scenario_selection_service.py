from __future__ import annotations

from schemas import ChosenScenario, ScenarioResult
from validators import label_rank


def choose_best_scenario(results: list[ScenarioResult], target_label: str) -> ChosenScenario:
    target_rank = label_rank(target_label)
    feasible = [r for r in results if label_rank(r.expected_label) <= target_rank]

    if feasible:
        selected = sorted(feasible, key=lambda r: (r.total_investment_eur, -r.monthly_savings_eur))[0]
        return ChosenScenario(
            scenario_id=selected.scenario_id,
            scenario_name=selected.scenario_name,
            reason="Goedkoopste scenario dat doel-label haalt.",
            goal_achieved=True,
        )

    selected = sorted(results, key=lambda r: label_rank(r.expected_label))[0]
    return ChosenScenario(
        scenario_id=selected.scenario_id,
        scenario_name=selected.scenario_name,
        reason="Doel-label niet gehaald; gekozen scenario komt het dichtst in de buurt.",
        goal_achieved=False,
    )
