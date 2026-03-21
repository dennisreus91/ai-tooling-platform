import pytest

from validators import normalize_constraints


def test_normalize_constraints_with_string_measure():
    result = normalize_constraints(
        target_label="a",
        required_measures="warmtepomp",
    )

    assert result.target_label == "A"
    assert result.required_measures == ["warmtepomp"]


def test_normalize_constraints_with_list_measures():
    result = normalize_constraints(
        target_label="next-step",
        required_measures=["isolatie", "zonnepanelen"],
    )

    assert result.target_label == "next_step"
    assert result.required_measures == ["isolatie", "zonnepanelen"]


def test_normalize_constraints_removes_empty_values_and_duplicates():
    result = normalize_constraints(
        target_label="b",
        required_measures=["isolatie", " ", "Isolatie", "zonnepanelen"],
    )

    assert result.target_label == "B"
    assert result.required_measures == ["isolatie", "zonnepanelen"]


def test_normalize_constraints_allows_none_required_measures():
    result = normalize_constraints(
        target_label="c",
        required_measures=None,
    )

    assert result.target_label == "C"
    assert result.required_measures == []


def test_normalize_constraints_rejects_invalid_target_label():
    with pytest.raises(ValueError, match="target_label must be one of"):
        normalize_constraints(
            target_label="D",
            required_measures=None,
        )


def test_normalize_constraints_rejects_non_string_measure_items():
    with pytest.raises(ValueError, match="required_measures must only contain strings"):
        normalize_constraints(
            target_label="A",
            required_measures=["isolatie", 123],
        )
