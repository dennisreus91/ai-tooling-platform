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
