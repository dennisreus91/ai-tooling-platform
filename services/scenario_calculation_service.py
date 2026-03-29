from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import ScenarioDefinition, ScenarioResult
from validators import label_from_ep2


class ScenarioCalculator(ABC):
    @abstractmethod
    def calculate(self, scenario: ScenarioDefinition, current_ep2: float) -> ScenarioResult:
        raise NotImplementedError


class GeminiScenarioCalculator(ScenarioCalculator):
    def calculate(self, scenario: ScenarioDefinition, current_ep2: float) -> ScenarioResult:
        reduction = 14.0 * len(scenario.measure_ids)
        new_ep2 = max(30.0, current_ep2 - reduction)
        investment = 2200.0 * len(scenario.measure_ids)
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            expected_ep2_kwh_m2=new_ep2,
            expected_label=label_from_ep2(new_ep2),
            selected_measures=scenario.ordered_measure_ids,
            total_investment_eur=investment,
            monthly_savings_eur=45.0 * len(scenario.measure_ids),
            expected_property_value_gain_eur=2000.0 * len(scenario.measure_ids),
            assumptions=["POC-indicatie via vervangbare calculatorlaag (Gemini placeholder)."],
            uncertainties=["Geen officiële NTA-rekenkern gekoppeld."],
        )
