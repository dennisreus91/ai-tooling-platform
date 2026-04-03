from schemas import Constraints, ExtractieMeta, FinalReport, MeasureStatus, ScenarioAdvice, WoningModel


def test_woningmodel_null_safe_defaults():
    model = WoningModel.model_validate({"prestatie": {}, "extractie_meta": {}})
    assert model.prestatie.current_ep2_kwh_m2 is None
    assert model.extractie_meta.confidence == 0.0


def test_extractie_meta_defaults():
    meta = ExtractieMeta()
    assert meta.missing_fields == []


def test_measure_status_model():
    status = MeasureStatus(measure_id="dakisolatie", canonical_name="Dakisolatie", status="improvable", reason="Rc onder doelwaarde")
    assert status.status == "improvable"


def test_scenario_advice_required_fields():
    advice = ScenarioAdvice(
        scenario_id="GEMINI_GEBALANCEERD",
        scenario_name="Gemini Gebalanceerd",
        expected_label="B",
        expected_ep2_kwh_m2=180.0,
        selected_measures=["dakisolatie"],
        logical_order=["dakisolatie"],
        total_investment_eur=4000.0,
        monthly_savings_eur=80.0,
        expected_property_value_gain_eur=7000.0,
        motivation="Beste route",
    )
    assert advice.expected_label == "B"


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


def test_constraints_required_measures_string_normalized_to_list():
    constraints = Constraints(target_label="A", required_measures="dakisolatie")
    assert constraints.required_measures == ["dakisolatie"]


def test_maatregel_extract_null_collections_are_coerced():
    model = WoningModel.model_validate(
        {
            "prestatie": {"current_ep2_kwh_m2": 200},
            "maatregelen": [
                {
                    "maatregel_naam_origineel": "Test",
                    "huidige_situatie": None,
                    "voorgestelde_situatie": None,
                    "relevante_parameters": None,
                    "maatregel_waarden": None,
                }
            ],
            "extractie_meta": {},
        }
    )

    measure = model.maatregelen[0]
    assert measure.huidige_situatie == {}
    assert measure.voorgestelde_situatie == {}
    assert measure.relevante_parameters == {}
    assert measure.maatregel_waarden == []
