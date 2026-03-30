import pytest

from validators import normalize_constraints


def test_normalize_constraints_accepts_extended_labels():
    assert normalize_constraints("g", None).target_label == "G"
    assert normalize_constraints("A", None).target_label == "A"
    assert normalize_constraints("d", None).target_label == "D"


def test_normalize_constraints_accepts_next_step_variants():
    assert normalize_constraints("next_step", None).target_label == "next_step"
    assert normalize_constraints("nextstep", None).target_label == "next_step"
    assert normalize_constraints("next-step", None).target_label == "next_step"


def test_normalize_constraints_rejects_invalid_target_label():
    with pytest.raises(ValueError):
        normalize_constraints("Z", None)

    with pytest.raises(ValueError):
        normalize_constraints("", None)


def test_normalize_constraints_required_measures_none_becomes_empty_list():
    result = normalize_constraints("A", None)
    assert result.required_measures == []


def test_normalize_constraints_required_measures_string_becomes_list():
    result = normalize_constraints("B", "dakisolatie")
    assert result.required_measures == ["dakisolatie"]


def test_normalize_constraints_required_measures_list_is_cleaned_and_deduplicated():
    result = normalize_constraints(
        "C",
        ["Dakisolatie", "dakisolatie", "  hrpp_glas  ", "", "HRPP_GLAS"],
    )
    assert result.required_measures == ["Dakisolatie", "hrpp_glas"]


def test_normalize_constraints_required_measures_rejects_non_string_items():
    with pytest.raises(ValueError):
        normalize_constraints("A", ["dakisolatie", 123])  # type: ignore[list-item]
