from validators import label_from_ep2, validate_woningmodel


def test_label_from_ep2_deterministic_mapping():
    assert label_from_ep2(170) == "B"
    assert label_from_ep2(400) == "G"


def test_validate_woningmodel_accepts_missing_fields():
    model = validate_woningmodel({"prestatie": {}, "extractie_meta": {"missing_fields": ["a", "a"]}})
    assert model.extractie_meta.missing_fields == ["a"]
