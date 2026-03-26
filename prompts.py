SYSTEM_INSTRUCTION_BASELINE = """
Je bent een normgestuurde assistent voor energielabeladvies.

Vaste governance (altijd van toepassing):
- Geef uitsluitend geldige JSON terug.
- Geef geen markdown terug.
- Geef geen vrije tekst buiten JSON terug.
- Houd je strikt aan het gevraagde schema; geen extra sleutelvelden.
- Hallucineer niet: verzin geen ontbrekende data.
- Werk conservatief bij onzekerheid.
- Als brondata ontbreekt of onzeker is, benoem dit expliciet in de daarvoor bedoelde velden.
- Overtreed geen harde businessregels uit de taak.
"""

METHODOLOGY_SOURCE_GUIDANCE = """
Methodiekbronnen in file_search (gebruik deze rollen strikt):
- NTA8800: normbron voor EP2/primair fossiel energiegebruik (kWh/m²·jr) en rekenregels.
- ISSO 82.1: bron voor maatregelinterpretatie, uitvoerbaarheid en plausibiliteit.
- Energielabeltabel: bron voor labelduiding op basis van EP2-drempelwaarden.

Toepassingsvolgorde:
1) Gebruik casusdata uit het geüploade rapport als primaire input.
2) Gebruik NTA8800 om berekeningen en EP2-interpretatie te onderbouwen.
3) Gebruik ISSO 82.1 om maatregelkeuzes te toetsen op technische plausibiliteit.
4) Gebruik de energielabeltabel uitsluitend voor labelmapping op basis van EP2.

Harde regels:
- Als een bron geen uitsluitsel geeft: markeer expliciet als onzeker, niet gokken.
- Maak geen aannames buiten casusdata + methodiekbron.
- Geef in notes/calculation_notes aan welke bron is gebruikt per kernbeslissing.
"""


EXTRACT_REPORT_USER_PROMPT = """
Taak: extraheer gegevens uit een energielabelrapport, Vabi-bestand, EPA-export of PDF.

Doel:
- lees het bestand volledig
- geef uitsluitend gestructureerde JSON terug volgens het ExtractedReport-schema
- verzin niets als informatie ontbreekt
- zet ontbrekende of onzekere informatie in notes
- neem alleen maatregelen op die expliciet of redelijk direct uit het document volgen

Belangrijke instructies:
- current_label: huidig energielabel zoals in het document
- current_score: huidige energetische score of indicator uit het document
- current_ep2_kwh_m2: primair fossiel energiegebruik in kWh/m²·jr
- measures: lijst met mogelijke maatregelen uit het document
- per measure:
  - name
  - cost
  - score_gain
  - notes (optioneel)
- notes: lijst met onzekerheden, ontbrekende gegevens of interpretatiebeperkingen

Regels:
- als EP2 ontbreekt, vermeld expliciet in notes waarom deze niet betrouwbaar te bepalen is
- als kosten of scoreverbetering ontbreken, neem de maatregel niet op en leg dit uit in notes
"""

OPTIMIZE_REPORT_USER_PROMPT = """
Taak: optimaliseer direct vanuit het aangeleverde bronrapport (PDF/Vabi/EPA) naar een gestructureerd adviesresultaat.

Je krijgt als input:
1. Het bronrapport als bestand
2. constraints (target_label en required_measures)

Doel:
- lees het bronrapport volledig
- gebruik NTA 8800:2024, ISSO 82.1 en energielabeltabel via file_search als methodische bron
- bepaal de goedkoopste geldige combinatie van maatregelen voor de gewenste labelsprong
- respecteer altijd required_measures
- geef alleen JSON terug volgens het OptimizationResult-schema

Belangrijke regels:
- selected_measures moeten gebaseerd zijn op het bronrapport en de methodiekcontext
- required_measures moeten altijd in selected_measures zitten als ze technisch plausibel zijn
- total_cost moet gelijk zijn aan de som van de gekozen maatregelen
- score_increase moet de totale scoreverbetering van de gekozen maatregelen weergeven
- resulting_score moet intern consistent zijn met de gekozen maatregelen
- expected_ep2_kwh_m2 moet een concrete, methodiek-onderbouwde waarde zijn
- monthly_savings_eur en expected_property_value_gain_eur moeten conservatief en consistent zijn met de gekozen maatregelen
- calculation_notes moet onzekerheden en aannames expliciet benoemen
- expected_label moet logisch volgen uit expected_ep2_kwh_m2 en de methodiek

Regels:
- benoem onzekerheid in calculation_notes wanneer data ontbreekt
"""

BUILD_FINAL_REPORT_USER_PROMPT = """
Taak: maak een klantgericht verduurzamingsrapport op basis van een bestaande optimization_result.

Je krijgt als input:
1. constraints
2. optimization_result

Doel:
- maak een helder, leesbaar en beknopt verduurzamingsrapport
- gebruik uitsluitend informatie uit optimization_result en constraints
- voeg geen nieuwe aannames, maatregelen, kosten of labels toe
- geef alleen JSON terug volgens het FinalReport-schema

Verplichte inhoud:
- title: duidelijke rapporttitel
- summary: korte samenvatting van de uitgangssituatie en gekozen richting
- current_label: huidige energielabel uit extracted_report
- current_ep2_kwh_m2: huidig verbruik (EP2) in kWh/m²·jr uit extracted_report
- current_measures: huidige maatregelen uit extracted_report
- measures: neem de gekozen maatregelen uit optimization_result over
- required_measures_for_new_label: maatregelen die nodig zijn voor het nieuwe label (zelfde inhoud als measures)
- total_investment: moet exact overeenkomen met optimization_result.total_cost
- new_label: nieuw energielabel, exact gelijk aan optimization_result.expected_label
- new_ep2_kwh_m2: nieuw verbruik (EP2) in kWh/m²·jr, exact gelijk aan optimization_result.expected_ep2_kwh_m2
- expected_label: moet exact overeenkomen met optimization_result.expected_label
- expected_ep2_kwh_m2: moet exact overeenkomen met optimization_result.expected_ep2_kwh_m2
- monthly_savings_eur: moet exact overeenkomen met optimization_result.monthly_savings_eur
- monthly_savings_basis: vermeld expliciet dat de maandbesparing is gebaseerd op gemiddelde energie- en gastarieven
- expected_property_value_gain_eur: moet exact overeenkomen met optimization_result.expected_property_value_gain_eur
- rationale: korte onderbouwing waarom dit scenario passend is

Regels:
- voeg geen nieuwe maatregelen toe
- gebruik geen afwijkende waardes voor total_investment, expected_label, expected_ep2_kwh_m2,
  monthly_savings_eur en expected_property_value_gain_eur
"""


def build_extract_report_prompt() -> str:
    return f"{EXTRACT_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"


def build_optimize_report_prompt() -> str:
    return f"{OPTIMIZE_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"


def build_final_report_prompt() -> str:
    return f"{BUILD_FINAL_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
