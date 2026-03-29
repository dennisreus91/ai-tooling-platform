from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


AllowedTargetLabel = Literal["next_step", "A", "B", "C", "D", "E", "F", "G"]
MeasureStatusType = Literal[
    "missing",
    "improvable",
    "sufficient",
    "not_applicable",
    "capacity_limited",
]


class RunPocFlowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    target_label: str = Field(..., min_length=1)
    required_measures: Union[str, List[str], None] = None
    file_url: HttpUrl
    debug: bool = False


class Constraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_label: AllowedTargetLabel
    required_measures: List[str] = Field(default_factory=list)


class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    cost: float
    score_gain: float
    notes: str | None = None


class ExtractieMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


class WoningModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    meta: Dict[str, Any] = Field(default_factory=dict)
    woning: Dict[str, Any] = Field(default_factory=dict)
    prestatie: Dict[str, Any] = Field(default_factory=dict)
    bouwdelen: Dict[str, Any] = Field(default_factory=dict)
    installaties: Dict[str, Any] = Field(default_factory=dict)
    samenvatting_huidige_maatregelen: List[str] = Field(default_factory=list)
    extractie_meta: ExtractieMeta = Field(default_factory=ExtractieMeta)


class ExtractedReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_label: str = Field(..., min_length=1)
    current_score: float = Field(..., ge=0)
    current_ep2_kwh_m2: float = Field(..., ge=0)
    measures: List[Measure] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class MeasureStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measure_id: str
    canonical_name: str
    status: MeasureStatusType
    current_value: Any = None
    target_value: Any = None
    reason: str


class MeasureImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measure_id: str
    canonical_name: str
    estimated_ep2_reduction: float = Field(ge=0.0)
    estimated_investment_eur: float = Field(ge=0.0)
    logic_score: float = Field(default=0.5, ge=0.0, le=1.0)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


class ScenarioDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    measure_ids: List[str] = Field(default_factory=list)
    ordered_measure_ids: List[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    expected_ep2_kwh_m2: float = Field(ge=0.0)
    expected_label: str
    selected_measures: List[str] = Field(default_factory=list)
    total_investment_eur: float = Field(ge=0.0)
    monthly_savings_eur: float = Field(ge=0.0)
    expected_property_value_gain_eur: float = Field(ge=0.0)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    trias_consistent: bool = True
    technical_feasible: bool = True


class ChosenScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    reason: str
    goal_achieved: bool


class OptimizationMeasure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    cost: float = Field(..., ge=0)
    score_gain: float = Field(..., gt=0)
    rationale: str | None = None


class OptimizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_measures: List[OptimizationMeasure] = Field(default_factory=list)
    total_cost: float = Field(..., ge=0)
    score_increase: float = Field(..., ge=0)
    expected_label: str = Field(..., min_length=1)
    resulting_score: float = Field(..., ge=0)
    expected_ep2_kwh_m2: float = Field(..., ge=0)
    monthly_savings_eur: float = Field(..., ge=0)
    expected_property_value_gain_eur: float = Field(..., ge=0)
    calculation_notes: List[str] = Field(default_factory=list)
    summary: str | None = None


class FinalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    current_label: str = Field(..., min_length=1)
    current_ep2_kwh_m2: float = Field(..., ge=0)
    chosen_scenario: str = Field(..., min_length=1)
    measures: List[str] = Field(default_factory=list)
    logical_order: List[str] = Field(default_factory=list)
    total_investment: float = Field(..., ge=0)
    new_label: str = Field(..., min_length=1)
    new_ep2_kwh_m2: float = Field(..., ge=0)
    monthly_savings_eur: float = Field(..., ge=0)
    expected_property_value_gain_eur: float = Field(..., ge=0)
    motivation: str = Field(..., min_length=1)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    poc_disclaimer: str = Field(..., min_length=1)


class PocFlowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraints: Constraints
    woningmodel: WoningModel
    measure_statuses: List[MeasureStatus]
    measure_impacts: List[MeasureImpact]
    scenarios: List[ScenarioDefinition]
    scenario_results: List[ScenarioResult]
    chosen_scenario: ChosenScenario
    final_report: FinalReport

