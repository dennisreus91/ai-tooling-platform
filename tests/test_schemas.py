from schemas import (
    Constraints,
    ExtractieMeta,
    FinalReport,
    MeasureStatus,
    ScenarioDefinition,
    ScenarioResult,
    WoningModel,
)


def test_woningmodel_null_safe_defaults():
    model = WoningModel.model_validate({"prestatie": {}, "extractie_meta": {}})

    assert model.meta.bron is None
    assert model.woning.bouwjaar is None
    assert model.prestatie.current_ep2_kwh_m2 is None
    assert model.bouwdelen.dak.rc is None
    assert model.installaties.verwarming.type is None

    assert model.extractie_meta.confidence == 0.0
    assert model.extractie_meta.missing_fields == []
    assert model.extractie_meta.assumptions == []
    assert model.extractie_meta.uncertainties == []
    assert model.extractie_meta.source_sections_found == []


def test_extractie_meta_defaults():
    meta = ExtractieMeta()
    assert meta.confidence == 0.0
    assert meta.missing_fields == []
    assert meta.assumptions == []
    assert meta.uncertainties == []
    assert meta.source_sections_found == []


def test_measure_status_model():
    status = MeasureStatus(
        measure_id="dakisolatie",
        canonical_name="Dakisolatie",
        status="improvable",
        reason="Rc onder doelwaarde",
    )
    assert status.measure_id == "dakisolatie"
    assert status.status == "improvable"
    assert status.reason == "Rc onder doelwaarde"


def test_scenario_definition_defaults():
    scenario = ScenarioDefinition(
        scenario_id="GEBALANCEERD",
        scenario_name="Gebalanceerd scenario",
    )
    assert scenario.measure_ids == []
    assert scenario.ordered_measure_ids == []


def test_scenario_result_accepts_core_fields():
    result = ScenarioResult(
        scenario_id="GEBALANCEERD",
        scenario_name="Gebalanceerd scenario",
        expected_ep2_kwh_m2=180.0,
        expected_label="B",
        selected_measures=["dakisolatie", "zonnepanelen_pv"],
        total_investment_eur=12000.0,
        monthly_savings_eur=95.0,
        expected_property_value_gain_eur=7000.0,
        assumptions=["Indicatieve POC-berekening."],
        uncertainties=["Geen officiële NTA-rekenkern gekoppeld."],
    )
    assert result.expected_label == "B"
    assert result.selected_measures == ["dakisolatie", "zonnepanelen_pv"]
    assert result.trias_consistent is True
    assert result.technical_feasible is True


def test_final_report_required_fields():
    report = FinalReport(
        title="POC Labelsprongadvies",
        summary="Indicatief labelsprongadvies.",
        current_label="D",
        current_ep2_kwh_m2=300.0,
        chosen_scenario="GEBALANCEERD",
        measures=["dakisolatie"],
        logical_order=["dakisolatie"],
        total_investment_eur=4000.0,
        new_label="B",
        new_ep2_kwh_m2=180.0,
        monthly_savings_eur=80.0,
        expected_property_value_gain_eur=7000.0,
        motivation="Goedkoopste haalbare route.",
        assumptions=[],
        uncertainties=[],
        poc_disclaimer="Dit rapport is een POC-scenario-inschatting.",
    )
    assert report.new_label == "B"
    assert report.total_investment_eur == 4000.0


def test_constraints_required_measures_string_normalized_to_list():
    constraints = Constraints(
        target_label="A",
        required_measures="dakisolatie",
    )
    assert constraints.required_measures == ["dakisolatie"]


def test_constraints_required_measures_deduplicated():
    constraints = Constraints(
        target_label="A",
        required_measures=["Dakisolatie", "dakisolatie", "  dakisolatie  ", "hrpp_glas"],
    )
    assert constraints.required_measures == ["Dakisolatie", "hrpp_glas"]
