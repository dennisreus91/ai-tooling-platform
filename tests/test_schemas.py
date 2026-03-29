from schemas import FinalReport, MeasureStatus, WoningModel


def test_woningmodel_null_safe_defaults():
    model = WoningModel.model_validate({"prestatie": {}, "extractie_meta": {}})
    assert model.meta == {}
    assert model.extractie_meta.confidence == 0


def test_measure_status_model():
    status = MeasureStatus(
        measure_id="dakisolatie",
        canonical_name="Dakisolatie",
        status="improvable",
        reason="Rc onder doelwaarde",
    )
    assert status.status == "improvable"


def test_final_report_required_fields():
    report = FinalReport(
        title="POC",
        summary="samenvatting",
        current_label="D",
        current_ep2_kwh_m2=300,
        chosen_scenario="GEBALANCEERD",
        measures=["dakisolatie"],
        logical_order=["dakisolatie"],
        total_investment=4000,
        new_label="B",
        new_ep2_kwh_m2=180,
        monthly_savings_eur=80,
        expected_property_value_gain_eur=7000,
        motivation="Goedkoopste haalbare route",
        assumptions=[],
        uncertainties=[],
        poc_disclaimer="poc",
    )
    assert report.new_label == "B"
