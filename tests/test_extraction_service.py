from services.extraction_service import extract_woningmodel_from_payload


def test_extract_coerces_measures_from_summary_when_missing():
    model = extract_woningmodel_from_payload(
        {
            "prestatie": {"current_ep2_kwh_m2": 220.0},
            "samenvatting_huidige_maatregelen": ["HR++ glas", "Dakisolatie"],
            "extractie_meta": {},
        }
    )

    assert len(model.maatregelen) == 2
    assert model.maatregelen[0].maatregel_naam_origineel == "HR++ glas"
    assert model.maatregelen[0].maatregel_waarden == []


def test_extract_normalizes_maatregelwaarden_numeric_and_unit():
    model = extract_woningmodel_from_payload(
        {
            "prestatie": {"current_ep2_kwh_m2": 210.0},
            "maatregelen": [
                {
                    "maatregel_naam_origineel": "Gevelisolatie verhogen",
                    "maatregel_waarden": [
                        {"parameter_naam": "Rc", "waarde": "4,5", "eenheid": "m²K/W"},
                        {"parameter_naam": "Oppervlak", "waarde": "onbekend", "eenheid": 123},
                    ],
                }
            ],
            "extractie_meta": {},
        }
    )

    values = model.maatregelen[0].maatregel_waarden
    assert values[0].waarde == 4.5
    assert values[0].eenheid == "m²K/W"
    assert values[1].waarde is None
    assert values[1].eenheid == "123"


def test_extract_normalizes_measure_quantity_and_bouwdeel_surface_fields():
    model = extract_woningmodel_from_payload(
        {
            "prestatie": {"current_ep2_kwh_m2": 210.0},
            "bouwdelen": {
                "dak": {"oppervlakte_m2": "64,5"},
                "gevel": {"oppervlakte_m2": "onbekend"},
            },
            "maatregelen": [
                {
                    "maatregel_naam_origineel": "Dakisolatie",
                    "quantity_value": "64,5",
                    "quantity_unit": "m2",
                    "quantity_source_field": "bouwdelen.dak.oppervlakte_m2",
                    "quantity_confidence": "0.75",
                }
            ],
            "extractie_meta": {},
        }
    )

    assert model.bouwdelen.dak.oppervlakte_m2 == 64.5
    assert model.bouwdelen.gevel.oppervlakte_m2 is None
    assert model.maatregelen[0].quantity_value == 64.5
    assert model.maatregelen[0].quantity_unit == "m2"
    assert model.maatregelen[0].quantity_source_field == "bouwdelen.dak.oppervlakte_m2"
    assert model.maatregelen[0].quantity_confidence == 0.75
