from __future__ import annotations

from schemas import WoningModel


def normalize_woningmodel(model: WoningModel) -> WoningModel:
    prestatie = model.prestatie
    ep2 = prestatie.get("current_ep2_kwh_m2")
    if ep2 is None:
        model.extractie_meta.missing_fields.append("prestatie.current_ep2_kwh_m2")
        model.extractie_meta.assumptions.append("EP2 ontbreekt; conservatieve default 320 toegepast.")
        prestatie["current_ep2_kwh_m2"] = 320.0
    else:
        prestatie["current_ep2_kwh_m2"] = float(ep2)

    if not model.woning.get("oppervlakte_m2"):
        model.woning["oppervlakte_m2"] = 120
        model.extractie_meta.assumptions.append("Oppervlakte niet gevonden; default 120m2.")

    model.extractie_meta.missing_fields = sorted(set(model.extractie_meta.missing_fields))
    model.extractie_meta.assumptions = sorted(set(model.extractie_meta.assumptions))
    return model
