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
- als kosten of scoreverbetering ontbreken, neem de maatregel niet op en leg dit uit in notes
"""

OPTIMIZE_REPORT_PROMPT = """
Je optimaliseert een gevalideerd energielabelrapport naar een gestructureerd adviesresultaat.

Je krijgt als input:
1. constraints
2. validated_report

Doel:
- bepaal de goedkoopste geldige combinatie van maatregelen binnen de opgegeven constraints
- respecteer altijd required_measures
- gebruik de methodiekdocumentatie als leidende bron voor de rekenwijze
- gebruik de validated_report-data als leidende bron voor de casusdata
- voeg geen maatregelen toe die niet in validated_report.measures staan
- geef alleen JSON terug volgens het OptimizationResult-schema

Belangrijke regels:
- selected_measures moeten afkomstig zijn uit validated_report.measures
- required_measures moeten altijd in selected_measures zitten als ze beschikbaar zijn in de input
- total_cost moet gelijk zijn aan de som van de gekozen maatregelen
- score_increase moet de totale scoreverbetering van de gekozen maatregelen weergeven
- resulting_score moet aansluiten op current_score + score_increase
- expected_label moet een logische uitkomst zijn op basis van de aangeleverde casus en methodiek
- summary mag kort zijn, maar moet de keuze verklaren

Verboden:
- geen markdown
- geen vrije tekst buiten JSON
- geen alternatieve sleutelvelden
- geen aannames buiten de input en methodiekcontext
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
- rationale: korte onderbouwing waarom dit scenario passend is

Verboden:
- geen markdown
- geen vrije tekst buiten JSON
- geen nieuwe maatregelen toevoegen
- geen andere total_investment of expected_label gebruiken dan in optimization_result
"""
