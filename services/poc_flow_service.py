from __future__ import annotations

import os

from gemini_service import get_scenario_advice_with_gemini
from schemas import Constraints, MeasureOverview, PocFlowResult, WoningModel
from services.measure_matching_service import match_measures
from services.normalization_service import normalize_woningmodel
from services.config_service import get_label_boundaries
from services.report_generation_service import build_final_report
from validators import label_from_ep2


def _build_measure_overview(statuses):
    missing = [s for s in statuses if s.status == "missing"]
    improvable = [s for s in statuses if s.status == "improvable"]
    combined = missing + improvable
    return MeasureOverview(missing=missing, improvable=improvable, combined=combined)




def _estimate_ep2_from_label(label: str) -> float | None:
    boundaries = get_label_boundaries().get("boundaries", [])
    normalized = (label or "").strip().upper()
    for rule in boundaries:
        if str(rule.get("label", "")).upper() != normalized:
            continue
        min_v = rule.get("ep2_min_inclusive")
        max_v = rule.get("ep2_max_exclusive")
        if min_v is not None and max_v is not None:
            return float(min_v + (max_v - min_v) / 2.0)
        if min_v is not None:
            return float(min_v + 10.0)
        if max_v is not None:
            return max(float(max_v) - 10.0, 0.0)
    return None

def run_poc_flow(constraints: Constraints, woningmodel: WoningModel) -> PocFlowResult:
    model = normalize_woningmodel(woningmodel)

    current_ep2_raw = model.prestatie.current_ep2_kwh_m2
    current_label_raw = model.prestatie.current_label

    if current_ep2_raw is None and current_label_raw is None:
        raise ValueError("missing_ep2_data: current_ep2_kwh_m2 en current_label ontbreken; flow kan niet starten.")

    if current_ep2_raw is None and current_label_raw is not None:
        estimated = _estimate_ep2_from_label(str(current_label_raw))
        if estimated is None:
            raise ValueError("missing_ep2_data: current_ep2_kwh_m2 ontbreekt en label kan niet naar EP2 worden geschat.")
        current_ep2 = estimated
        if "prestatie.current_ep2_kwh_m2" not in model.extractie_meta.assumptions:
            model.extractie_meta.assumptions.append("prestatie.current_ep2_kwh_m2 geschat vanuit current_label via labelgrenzen.json.")
    else:
        current_ep2 = float(current_ep2_raw)

    current_label = str(current_label_raw or label_from_ep2(current_ep2))

    statuses = match_measures(model)
    overview = _build_measure_overview(statuses)

    scenario_advice = get_scenario_advice_with_gemini(
        constraints=constraints,
        woningmodel=model,
        measure_overview=overview,
        file_search_store=os.getenv("GEMINI_FILE_SEARCH_STORE"),
    )

    final_report = build_final_report(
        current_label=current_label,
        current_ep2=current_ep2,
        scenario_advice=scenario_advice,
    )

    return PocFlowResult(
        constraints=constraints,
        woningmodel=model,
        measure_statuses=statuses,
        measure_overview=overview,
        scenario_advice=scenario_advice,
        final_report=final_report,
    )
