EXTRACT_REPORT_PROMPT = """
Je extraheert gegevens uit een energielabelrapport, Vabi-bestand, EPA-export of PDF.

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
- geef alleen JSON terug
- geen markdown
- geen toelichtende tekst buiten de JSON
- als EP2 ontbreekt, vermeld expliciet in notes waarom deze niet betrouwbaar te bepalen is
- als kosten of scoreverbetering ontbreken, neem de maatregel niet op en leg dit uit in notes
"""

OPTIMIZE_REPORT_PROMPT = """
Je optimaliseert direct vanuit het aangeleverde bronrapport (PDF/Vabi/EPA) naar een gestructureerd adviesresultaat.

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

Verboden:
- geen markdown
- geen vrije tekst buiten JSON
- geen alternatieve sleutelvelden
- geen hallucinaties bij ontbrekende data; benoem onzekerheid in calculation_notes
"""

BUILD_FINAL_REPORT_PROMPT = """
Je maakt een klantgericht verduurzamingsrapport op basis van een bestaande optimization_result.

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
- measures: neem de gekozen maatregelen uit optimization_result over
- total_investment: moet exact overeenkomen met optimization_result.total_cost
- expected_label: moet exact overeenkomen met optimization_result.expected_label
- expected_ep2_kwh_m2: moet exact overeenkomen met optimization_result.expected_ep2_kwh_m2
- monthly_savings_eur: moet exact overeenkomen met optimization_result.monthly_savings_eur
- expected_property_value_gain_eur: moet exact overeenkomen met optimization_result.expected_property_value_gain_eur
- rationale: korte onderbouwing waarom dit scenario passend is

Verboden:
- geen markdown
- geen vrije tekst buiten JSON
- geen nieuwe maatregelen toevoegen
- geen afwijkende waardes gebruiken voor total_investment, expected_label, expected_ep2_kwh_m2,
  monthly_savings_eur en expected_property_value_gain_eur
"""
