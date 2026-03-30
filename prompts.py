SYSTEM_INSTRUCTION_BASELINE = """
Je bent een normgestuurde assistent voor energielabelanalyse (NTA8800 context).

STRIKTE OUTPUTREGELS:
- Geef ALLEEN geldige JSON terug
- Geen markdown
- Geen toelichting buiten JSON
- Geen extra velden buiten het schema
- Gebruik null voor onbekende waarden
- Gebruik GEEN placeholders zoals "onbekend" of "n.v.t."
"""


METHODOLOGY_SOURCE_GUIDANCE = """
Gebruik methodiekconsistentie gebaseerd op:
- NTA 8800 (EP2, labelbepaling)
- ISSO 82.1 (maatregelen en interpretatie)
- Energielabelsystematiek (label ↔ EP2)

BELANGRIJK:
- Geen exacte berekeningen simuleren alsof het officieel is
- Blijf indicatief maar logisch consistent
"""


EXTRACT_REPORT_USER_PROMPT = """
Doel: Zet een Vabi-energieprestatiebestand om naar een WoningModel JSON.

STRUCTUUR:
Gebruik exact deze hoofdvelden:
- meta
- woning
- prestatie
- maatwerkadvies
- bouwdelen
- installaties
- samenvatting_huidige_maatregelen
- extractie_meta

REGELS:
1. Gebruik null voor ontbrekende waarden
2. Gebruik GEEN defaults (geen 120m2 etc.)
3. Plaats aannames ALLEEN in extractie_meta.assumptions
4. Plaats onzekerheden ALLEEN in extractie_meta.uncertainties
5. Plaats ontbrekende velden in extractie_meta.missing_fields

EXTRACTIE_META VERPLICHT:
- confidence (0–1)
- missing_fields (lijst van veldpaden)
- assumptions (lijst van aannames)
- uncertainties (lijst van onzekerheden)

VELDNAMEN:
Gebruik EXACT deze keys (bijv.):
- prestatie.current_ep2_kwh_m2
- bouwdelen.dak.rc
- installaties.verwarming.type

NIET TOEGESTAAN:
- vrije interpretaties zonder bron
- waarden verzinnen zonder vermelding als assumption

UITVOER:
Geef uitsluitend het WoningModel als JSON.
"""


MEASURE_IMPACT_PROMPT = """
Doel: Bepaal impact van maatregelen.

INPUT:
- lijst met MeasureStatus (missing/improvable)

OUTPUT:
JSON lijst met MeasureImpact objecten.

REGELS:
- Alleen maatregelen met status: missing of improvable
- Gebruik indicatieve EP2-reductie (geen exacte berekening)
- Voeg altijd toe:
  - assumptions
  - uncertainties

LOGICA:
- Trias stap 1 > hogere prioriteit
- Schilmaatregelen > installaties > opwek

UITVOER:
Alleen JSON, geen tekst.
"""


OPTIMIZE_REPORT_USER_PROMPT = """
Doel: Bouw scenario's op basis van MeasureImpact.

REGELS:
- Respecteer Trias Energetica:
  1. Beperk energievraag
  2. Gebruik duurzame energie
  3. Optimaliseer fossiel restant

- Respecteer afhankelijkheden tussen maatregelen:
  - Geen conflicterende combinaties
  - Houd volgorde logisch

SCENARIO-EISEN:
- Logische volgorde van maatregelen
- Maximaal aantal maatregelen per scenario respecteren
- Balans tussen kosten en impact

UITVOER:
Alleen JSON met scenario-definities.
"""


BUILD_FINAL_REPORT_USER_PROMPT = """
Doel: Genereer eindrapport op basis van gekozen scenario.

OUTPUT STRUCTUUR:
- title
- summary
- current_label
- current_ep2_kwh_m2
- chosen_scenario
- measures
- logical_order
- total_investment_eur
- new_label
- new_ep2_kwh_m2
- monthly_savings_eur
- expected_property_value_gain_eur
- motivation
- assumptions
- uncertainties
- poc_disclaimer

REGELS:
- Gebruik GEEN marketingtaal
- Blijf technisch en feitelijk
- Alle aannames expliciet benoemen
- Alle onzekerheden expliciet benoemen

BELANGRIJK:
- Dit is een POC → geen officiële labelberekening suggereren

UITVOER:
Alleen JSON.
"""


def build_extract_report_prompt() -> str:
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        f"{EXTRACT_REPORT_USER_PROMPT.strip()}\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )


def build_measure_impact_prompt() -> str:
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        f"{MEASURE_IMPACT_PROMPT.strip()}\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )


def build_optimize_report_prompt() -> str:
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        f"{OPTIMIZE_REPORT_USER_PROMPT.strip()}\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )


def build_final_report_prompt() -> str:
    return (
        f"{SYSTEM_INSTRUCTION_BASELINE.strip()}\n\n"
        f"{BUILD_FINAL_REPORT_USER_PROMPT.strip()}\n\n"
        f"{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
    )
