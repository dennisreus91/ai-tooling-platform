from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


AllowedTargetLabel = Literal["next_step", "A", "B", "C", "D", "E", "F", "G"]
AllowedEnergyLabel = Literal["A++++", "A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"]
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

    @field_validator("required_measures", mode="before")
    @classmethod
    def ensure_required_measures_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("required_measures moet een lijst, string of null zijn.")
        cleaned: List[str] = []
        seen: set[str] = set()
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(text)
        return cleaned


class ExtractieMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    source_sections_found: List[str] = Field(default_factory=list)


class WoningMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    bron: Optional[str] = None
    versie: Optional[str] = None
    bestandstype: Optional[str] = None
    extractiemethode: Optional[str] = None


class WoningInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    projectnaam: Optional[str] = None
    adres_identificatie: Optional[str] = None
    bouwjaar: Optional[int] = None
    renovatiejaar: Optional[int] = None
    type: Optional[str] = None
    gebruiksoppervlakte_m2: Optional[float] = None
    inhoud_m3: Optional[float] = None
    aantal_bouwlagen: Optional[int] = None
    daktype: Optional[str] = None
    verliesoppervlak_m2: Optional[float] = None
    bouwperiode: Optional[str] = None
    woningtype_brontekst: Optional[str] = None


class PrestatieInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    current_ep2_kwh_m2: Optional[float] = None
    current_label: Optional[str] = None
    ep1_kwh_m2: Optional[float] = None
    ep3_aandeel_hernieuwbaar_pct: Optional[float] = None
    bronwaarde_ep2: Optional[str] = None
    bronwaarde_label: Optional[str] = None


class MaatwerkadviesInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    gasverbruik_m3: Optional[float] = None
    elektriciteitsverbruik_kwh: Optional[float] = None
    elektriciteitsopwekking_kwh: Optional[float] = None
    netto_elektriciteit_kwh: Optional[float] = None
    warmteverbruik_gj: Optional[float] = None
    co2_kg: Optional[float] = None


class DakInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    rc: Optional[float] = None
    brontekst: Optional[str] = None


class GevelInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    rc: Optional[float] = None
    brontekst: Optional[str] = None


class VloerInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    rc: Optional[float] = None
    brontekst: Optional[str] = None


class RamenInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    u_waarde: Optional[float] = None
    glastype: Optional[str] = None
    kozijn_isolerend: Optional[bool] = None
    brontekst: Optional[str] = None


class LuchtdichtingInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    qv10: Optional[float] = None
    brontekst: Optional[str] = None


class BouwdelenInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    dak: DakInfo = Field(default_factory=DakInfo)
    gevel: GevelInfo = Field(default_factory=GevelInfo)
    vloer: VloerInfo = Field(default_factory=VloerInfo)
    ramen: RamenInfo = Field(default_factory=RamenInfo)
    luchtdichting: LuchtdichtingInfo = Field(default_factory=LuchtdichtingInfo)


class VerwarmingInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Optional[str] = None
    rendement: Optional[float] = None
    brontekst: Optional[str] = None


class AfgifteInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_aanvoer_temp_c: Optional[float] = None
    brontekst: Optional[str] = None


class RegelingInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    waterzijdig_ingeregeld: Optional[bool] = None
    klasse: Optional[float] = None
    brontekst: Optional[str] = None


class VentilatieInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Optional[str] = None
    vraaggestuurd: Optional[bool] = None
    inregeling_ok: Optional[bool] = None
    brontekst: Optional[str] = None


class TapwaterInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Optional[str] = None
    zonneboiler: Optional[bool] = None
    douche_wtw: Optional[bool] = None
    rendement: Optional[float] = None
    brontekst: Optional[str] = None


class PvInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    kwp: Optional[float] = None
    max_extra_kwp: Optional[float] = None
    brontekst: Optional[str] = None


class ElektraInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_aansluitwaarde_kw: Optional[float] = None
    brontekst: Optional[str] = None


class InstallatiesInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    verwarming: VerwarmingInfo = Field(default_factory=VerwarmingInfo)
    afgifte: AfgifteInfo = Field(default_factory=AfgifteInfo)
    regeling: RegelingInfo = Field(default_factory=RegelingInfo)
    ventilatie: VentilatieInfo = Field(default_factory=VentilatieInfo)
    tapwater: TapwaterInfo = Field(default_factory=TapwaterInfo)
    pv: PvInfo = Field(default_factory=PvInfo)
    elektra: ElektraInfo = Field(default_factory=ElektraInfo)


class WoningModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    meta: WoningMeta = Field(default_factory=WoningMeta)
    woning: WoningInfo = Field(default_factory=WoningInfo)
    prestatie: PrestatieInfo = Field(default_factory=PrestatieInfo)
    maatwerkadvies: MaatwerkadviesInfo = Field(default_factory=MaatwerkadviesInfo)
    bouwdelen: BouwdelenInfo = Field(default_factory=BouwdelenInfo)
    installaties: InstallatiesInfo = Field(default_factory=InstallatiesInfo)
    samenvatting_huidige_maatregelen: List[str] = Field(default_factory=list)
    maatregelen: List["MaatregelExtract"] = Field(default_factory=list)
    extractie_meta: ExtractieMeta = Field(default_factory=ExtractieMeta)


class MaatregelWaarde(BaseModel):
    model_config = ConfigDict(extra="allow")

    parameter_naam: Optional[str] = None
    parameter_naam_origineel: Optional[str] = None
    waarde: Optional[float] = None
    eenheid: Optional[str] = None
    waarde_type: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MaatregelExtract(BaseModel):
    model_config = ConfigDict(extra="allow")

    maatregel_naam_origineel: Optional[str] = None
    maatregel_type: Optional[str] = None
    huidige_situatie: Dict[str, Any] = Field(default_factory=dict)
    voorgestelde_situatie: Dict[str, Any] = Field(default_factory=dict)
    betrokken_bouwdelen: List[str] = Field(default_factory=list)
    betrokken_installaties: List[str] = Field(default_factory=list)
    relevante_parameters: Dict[str, Any] = Field(default_factory=dict)
    maatregel_waarden: List[MaatregelWaarde] = Field(default_factory=list)
    opmerking: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def coerce_null_collections(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        for key in ("huidige_situatie", "voorgestelde_situatie", "relevante_parameters"):
            if normalized.get(key) is None:
                normalized[key] = {}
        for key in ("betrokken_bouwdelen", "betrokken_installaties", "maatregel_waarden"):
            if normalized.get(key) is None:
                normalized[key] = []
        if normalized.get("confidence") is None:
            normalized["confidence"] = 0.0
        return normalized




class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    cost: float = Field(..., ge=0)
    score_gain: float = Field(..., ge=0)
    notes: str | None = None


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
    evidence_fields: List[str] = Field(default_factory=list)
    current_values_snapshot: Dict[str, Any] = Field(default_factory=dict)
    gap_delta: Optional[float] = None
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


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
    expected_ep2_kwh_m2: float = Field(default=0.0)
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


class MeasureOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing: List[MeasureStatus] = Field(default_factory=list)
    improvable: List[MeasureStatus] = Field(default_factory=list)
    combined: List[MeasureStatus] = Field(default_factory=list)


class ScenarioAdvice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    expected_label: str
    expected_ep2_kwh_m2: float
    selected_measures: List[str] = Field(default_factory=list)
    logical_order: List[str] = Field(default_factory=list)
    total_investment_eur: float = Field(ge=0.0)
    monthly_savings_eur: float = Field(ge=0.0)
    expected_property_value_gain_eur: float = Field(ge=0.0)
    motivation: str
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    methodiek_bronnen: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    current_label: str = Field(..., min_length=1)
    current_ep2_kwh_m2: float = Field(ge=0.0)
    chosen_scenario: str = Field(..., min_length=1)
    measures: List[str] = Field(default_factory=list)
    logical_order: List[str] = Field(default_factory=list)
    total_investment_eur: float = Field(ge=0.0)
    new_label: str = Field(..., min_length=1)
    new_ep2_kwh_m2: float = Field()
    monthly_savings_eur: float = Field(ge=0.0)
    expected_property_value_gain_eur: float = Field(ge=0.0)
    motivation: str = Field(..., min_length=1)
    assumptions: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    poc_disclaimer: str = Field(..., min_length=1)


class PocFlowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraints: Constraints
    woningmodel: WoningModel
    measure_statuses: List[MeasureStatus]
    measure_overview: MeasureOverview
    scenario_advice: ScenarioAdvice
    final_report: FinalReport
