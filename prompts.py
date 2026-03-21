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
