from __future__ import annotations

import json
from typing import Any

SYSTEM_INSTRUCTION_BASELINE = """
Je bent een normgestuurde assistent voor energielabelanalyse in POC-context.

STRIKTE OUTPUTREGELS:
- Geef ALLEEN geldige JSON terug
- Geen markdown
- Geen toelichting buiten JSON
- Geen extra velden buiten het gevraagde schema
- Gebruik null voor onbekende waarden
"""


METHODOLOGY_SOURCE_GUIDANCE = """
Gebruik methodiekconsistentie gebaseerd op:
- ISSO 82.1
- ISSO 82.2
- NTA 8800
- RVO voorbeeldwoningen

BELANGRIJK:
- Dit is een indicatieve POC (geen officiële labelregistratie)
- Blijf technisch en expliciteer aannames en onzekerheden
"""


TRIAS_ENERGETICA_INSTRUCTIE = """
Respecteer Trias Energetica in scenario-advies:
1. Beperk eerst de energievraag (schil, luchtdichting, ventilatie)
2. Gebruik daarna duurzame bronnen/installaties
3. Optimaliseer pas daarna resterend fossiel energiegebruik
"""


def build_extract_report_prompt(woningmodel_schema: dict[str, Any]) -> str:
    schema_json = json.dumps(woningmodel_schema, ensure_ascii=False, indent=2)
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        "Doel: map het aangeleverde Vabi-rapport direct naar exact één WoningModel JSON.\n"
        "Gebruik dit schema als leidend contract (veldnamen exact overnemen):\n"
        f"{schema_json}\n\n"
        "Regels:\n"
        "- Geen backend-hermapping verwachten: vul direct het juiste model in\n"
        "- Gebruik null bij ontbrekende waarden\n"
        "- Zet aannames alleen in extractie_meta.assumptions\n"
        "- Zet onzekerheden alleen in extractie_meta.uncertainties\n"
        "- Zet missende velden in extractie_meta.missing_fields\n"
        "- Geef uitsluitend JSON van het WoningModel terug\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )


def build_scenario_advice_prompt() -> str:
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        "Doel: maak scenarioadvies op basis van woningmodel + maatregeloverzicht + templates.\n"
        "Input bevat:\n"
        "- woningmodel\n"
        "- measure_overview (missing, improvable, combined)\n"
        "- relevante woninginformatie\n"
        "- scenario_templates\n"
        "- trias_structuur\n"
        "- toegang tot file_search_store met methodiekdocumenten\n\n"
        "Output: precies één ScenarioAdvice JSON-object met onder meer:\n"
        "scenario_id, scenario_name, expected_label, expected_ep2_kwh_m2, selected_measures, logical_order,\n"
        "total_investment_eur, monthly_savings_eur, expected_property_value_gain_eur, motivation, assumptions, uncertainties, methodiek_bronnen.\n\n"
        "Regels:\n"
        "- Maak meerdere scenario-opties intern en kies de beste optie voor doel-label + Trias\n"
        "- Respecteer opgegeven required_measures\n"
        "- Gebruik alleen maatregelen uit het meegegeven measure_overview\n"
        "- Geef alleen JSON terug\n\n"
        f"{TRIAS_ENERGETICA_INSTRUCTIE.strip()}\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )
