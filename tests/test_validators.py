from validators import (
    label_from_ep2,
    label_meets_target,
    label_rank,
    next_better_label,
    validate_woningmodel,
)


def test_label_from_ep2_deterministic_mapping():
    assert label_from_ep2(170) == "B"
    assert label_from_ep2(400) == "G"
    assert label_from_ep2(104.9) == "A+"
    assert label_from_ep2(105.0) == "A"


def test_label_rank_deterministic_order():
    assert label_rank("A") < label_rank("B")
    assert label_rank("B") < label_rank("C")
    assert label_rank("A+++") < label_rank("A")
    assert label_rank("G") > label_rank("F")


def test_label_meets_target_true_when_label_is_good_enough():
    assert label_meets_target("A", "B") is True
    assert label_meets_target("B", "B") is True
    assert label_meets_target("A++", "A") is True


def test_label_meets_target_false_when_label_is_insufficient():
    assert label_meets_target("C", "B") is False
    assert label_meets_target("G", "D") is False


def test_next_better_label():
    assert next_better_label("B") == "A"
    assert next_better_label("A") == "A+"
    assert next_better_label("A++++") is None


def test_validate_woningmodel_accepts_missing_fields_and_deduplicates():
    model = validate_woningmodel(
        {
            "prestatie": {},
            "extractie_meta": {
                "missing_fields": ["a", "a"],
                "assumptions": ["x", "x"],
                "uncertainties": ["u", "u"],
                "source_sections_found": ["Samenvatting", "Samenvatting"],
            },
        }
    )

    assert model.extractie_meta.missing_fields == ["a", "prestatie.current_ep2_kwh_m2"]
    assert model.extractie_meta.assumptions == ["x"]
    assert model.extractie_meta.uncertainties[0] == "u"
    assert model.extractie_meta.source_sections_found == ["Samenvatting"]


def test_validate_woningmodel_clamps_confidence():
    model = validate_woningmodel(
        {
            "prestatie": {},
            "extractie_meta": {
                "confidence": 2.5,
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )
    assert model.extractie_meta.confidence == 1.0

    model2 = validate_woningmodel(
        {
            "prestatie": {},
            "extractie_meta": {
                "confidence": -0.4,
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )
    assert model2.extractie_meta.confidence == 0.0


def test_validate_woningmodel_adds_uncertainty_when_label_and_ep2_missing():
    model = validate_woningmodel(
        {
            "prestatie": {
                "current_ep2_kwh_m2": None,
                "current_label": None,
            },
            "extractie_meta": {
                "missing_fields": [],
                "assumptions": [],
                "uncertainties": [],
            },
        }
    )

    assert "prestatie.current_ep2_kwh_m2" in model.extractie_meta.missing_fields
    assert any(
        "current_label als current_ep2_kwh_m2 ontbreken" in text
        or "current_label als current_ep2_kwh_m2 ontbreekt" in text
        or "Zowel current_label als current_ep2_kwh_m2 ontbreken" in text
        for text in model.extractie_meta.uncertainties
    )
