import pytest

from validators import validate_extract


def test_validate_extract_keeps_valid_measures():
    data = {
        "current_label": "D",
        "current_score": 220,
        "measures": [
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Zonnepanelen", "cost": 3500, "score_gain": 15},
        ],
        "notes": [],
    }

    result = validate_extract(data)

    assert result.current_label == "D"
    assert result.current_score == 220
    assert len(result.measures) == 2
    assert result.notes == []


def test_validate_extract_removes_negative_cost_measure():
    data = {
        "current_label": "D",
        "current_score": 220,
        "measures": [
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Foutieve maatregel", "cost": -1, "score_gain": 10},
        ],
        "notes": [],
    }

    result = validate_extract(data)

    assert len(result.measures) == 1
    assert result.measures[0].name == "Dakisolatie"
    assert any("cost was negative" in note for note in result.notes)


def test_validate_extract_removes_non_positive_score_gain_measure():
    data = {
        "current_label": "D",
        "current_score": 220,
        "measures": [
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"name": "Geen effect", "cost": 1000, "score_gain": 0},
        ],
        "notes": [],
    }

    result = validate_extract(data)

    assert len(result.measures) == 1
    assert result.measures[0].name == "Dakisolatie"
    assert any("score_gain was not positive" in note for note in result.notes)


def test_validate_extract_returns_empty_measure_list_when_all_invalid():
    data = {
        "current_label": "E",
        "current_score": 300,
        "measures": [
            {"name": "Ongeldig 1", "cost": -100, "score_gain": 10},
            {"name": "Ongeldig 2", "cost": 2500, "score_gain": 0},
        ],
        "notes": ["Originele noot."],
    }

    result = validate_extract(data)

    assert result.current_label == "E"
    assert result.current_score == 300
    assert result.measures == []
    assert "Originele noot." in result.notes
    assert len(result.notes) >= 3


def test_validate_extract_rejects_invalid_report_payload():
    data = {
        "current_label": "",
        "current_score": -1,
        "measures": [],
        "notes": [],
    }

    with pytest.raises(ValueError, match="Invalid extracted report data"):
        validate_extract(data)


def test_validate_extract_rejects_invalid_measure_shape_inside_report():
    data = {
        "current_label": "D",
        "current_score": 220,
        "measures": [
            {"name": "Dakisolatie", "cost": 4000, "score_gain": 20},
            {"cost": 1000, "score_gain": 5},
        ],
        "notes": [],
    }

    with pytest.raises(ValueError, match="Invalid extracted report data"):
        validate_extract(data)
