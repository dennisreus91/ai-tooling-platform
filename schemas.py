from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


AllowedTargetLabel = Literal["next_step", "A", "B", "C"]


class RunPocFlowRequest(BaseModel):
    """
    Raw intake payload received from Typebot or another frontend.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    target_label: str = Field(..., min_length=1)
    required_measures: Union[str, List[str], None] = None
    file_url: HttpUrl


class Constraints(BaseModel):
    """
    Normalized user constraints used in later pipeline steps.
    """

    model_config = ConfigDict(extra="forbid")

    target_label: AllowedTargetLabel
    required_measures: List[str] = Field(default_factory=list)


class Measure(BaseModel):
    """
    Single extracted measure from a report.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    cost: float
    score_gain: float
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Measure name must not be empty.")
        return cleaned


class ExtractedReport(BaseModel):
    """
    Structured output of the report extraction step.
    """

    model_config = ConfigDict(extra="forbid")

    current_label: str = Field(..., min_length=1)
    current_score: float = Field(..., ge=0)
    current_ep2_kwh_m2: float = Field(..., ge=0)
    measures: List[Measure] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    @field_validator("current_label")
    @classmethod
    def validate_current_label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("current_label must not be empty.")
        return cleaned


class OptimizationMeasure(BaseModel):
    """
    Measure selected in the optimization step.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    cost: float = Field(..., ge=0)
    score_gain: float = Field(..., gt=0)
    rationale: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("OptimizationMeasure name must not be empty.")
        return cleaned


class OptimizationResult(BaseModel):
    """
    Structured output of the optimization step.
    """

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

    @field_validator("expected_label")
    @classmethod
    def validate_expected_label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("expected_label must not be empty.")
        return cleaned


class FinalReport(BaseModel):
    """
    Structured output of the final reporting step.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    measures: List[OptimizationMeasure] = Field(default_factory=list)
    total_investment: float = Field(..., ge=0)
    expected_label: str = Field(..., min_length=1)
    expected_ep2_kwh_m2: float = Field(..., ge=0)
    monthly_savings_eur: float = Field(..., ge=0)
    expected_property_value_gain_eur: float = Field(..., ge=0)
    rationale: str = Field(..., min_length=1)

    @field_validator("title", "summary", "expected_label", "rationale")
    @classmethod
    def validate_non_empty_string(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be empty.")
        return cleaned
