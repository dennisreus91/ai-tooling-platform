import pytest

from validators import normalize_constraints


def test_normalize_constraints_accepts_extended_labels():
    assert normalize_constraints("g", None).target_label == "G"


def test_normalize_constraints_rejects_invalid_target_label():
    with pytest.raises(ValueError):
        normalize_constraints("Z", None)
