import pytest
from pydantic import ValidationError

from schemas import (
    Constraints,
    ExtractedReport,
    FinalReport,
    Measure,
    OptimizationMeasure,
    OptimizationResult,
)


def test_constraints_accepts_allowed_target_labels():
    result = Constraints(
        target_label="A",
        required_measures=["isolatie", "warmtepomp"],
    )

    assert result.target_label == "A"
    assert result.required_measures == ["isolatie", "warmtepomp"]


def test_constraints_rejects_invalid_target_label():
    with pytest.raises(ValidationError):
        Constraints(
            target_label="D",
            required_measures=[],
        )


def test_measure_parses_valid_payload():
    measure = Measure(
        name="Spouwmuurisolatie",
        cost=2500,
        score_gain=15,
        notes="Geschikt bij voldoende spouwbreedte.",
    )

    assert measure.name == "Spouwmuurisolatie"
    assert measure.cost == 2500
    assert measure.score_gain == 15
    assert measure.notes == "Geschikt bij voldoende spouwbreedte."


def test_measure_rejects_negative_cost():
    with pytest.raises(ValidationError):
        Measure(
            name="Warmtepomp",
            cost=-1,
            score_gain=40,
        )


def test_measure_rejects_zero_score_gain():
    with pytest.raises(ValidationError):
        Measure(
            name="Warmtepomp",
            cost=8000,
            score_gain=0,
        )


def test_extracted_report_parses_valid_payload():
    report = ExtractedReport(
        current_label="D",
        current_score=120,
        measures=[
            {
                "name": "spouwmuurisolatie",
                "cost": 2500,
                "score_gain": 15,
            },
            {
                "name": "warmtepomp",
                "cost": 8000,
                "score_gain": 40,
                "notes": "Controleer afgiftesysteem.",
            },
        ],
        notes=["Rapport deels gebaseerd op aangeleverde opname."],
    )

    assert report.current_label == "D"
    assert report.current_score == 120
    assert len(report.measures) == 2
    assert report.measures[0].name == "spouwmuurisolatie"
    assert report.notes == ["Rapport deels gebaseerd op aangeleverde opname."]


def test_extracted_report_allows_empty_measures():
    report = ExtractedReport(
        current_label="C",
        current_score=180,
        measures=[],
        notes=[],
    )

    assert report.measures == []
    assert report.notes == []


def test_optimization_measure_parses_valid_payload():
    measure = OptimizationMeasure(
        name="Dakisolatie",
        cost=5000,
        score_gain=20,
        rationale="Goede verhouding tussen investering en labelsprong.",
    )

    assert measure.name == "Dakisolatie"
    assert measure.cost == 5000
    assert measure.score_gain == 20


def test_optimization_result_parses_valid_payload():
    result = OptimizationResult(
        selected_measures=[
            {
                "name": "Dakisolatie",
                "cost": 5000,
                "score_gain": 20,
                "rationale": "Sterke eerste stap.",
            },
            {
                "name": "Zonnepanelen",
                "cost": 4500,
                "score_gain": 18,
            },
        ],
        total_cost=9500,
        score_increase=38,
        expected_label="A",
        resulting_score=82,
        summary="Goedkoopste combinatie richting label A.",
    )

    assert len(result.selected_measures) == 2
    assert result.total_cost == 9500
    assert result.score_increase == 38
    assert result.expected_label == "A"
    assert result.resulting_score == 82


def test_optimization_result_rejects_negative_total_cost():
    with pytest.raises(ValidationError):
        OptimizationResult(
            selected_measures=[],
            total_cost=-10,
            score_increase=0,
            expected_label="B",
            resulting_score=150,
        )


def test_final_report_parses_valid_payload():
    report = FinalReport(
        title="Verduurzamingsadvies",
        summary="Deze woning kan met twee maatregelen naar label A.",
        measures=[
            {
                "name": "Dakisolatie",
                "cost": 5000,
                "score_gain": 20,
                "rationale": "Belangrijke verbetering van de schil.",
            }
        ],
        total_investment=5000,
        expected_label="A",
        rationale="De combinatie is gekozen op basis van lage investering en voldoende scoreverbetering.",
    )

    assert report.title == "Verduurzamingsadvies"
    assert report.summary.startswith("Deze woning")
    assert report.total_investment == 5000
    assert report.expected_label == "A"
    assert len(report.measures) == 1


def test_final_report_rejects_empty_title():
    with pytest.raises(ValidationError):
        FinalReport(
            title="   ",
            summary="Samenvatting",
            measures=[],
            total_investment=0,
            expected_label="B",
            rationale="Onderbouwing",
        )
