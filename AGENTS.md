# AGENTS.md

## Projectdoel
Bouw binnen deze bestaande repository een Flask-gebaseerde energielabel-tool voor labelsprongadvies op basis van Vabi-rapporten.

De tool moet:
- een Vabi-bestand ontvangen
- een doel-label ontvangen
- het Vabi-bestand via Gemini LLM mappen naar een gestructureerd woningmodel
- de huidige woningstatus vergelijken met een maatregelenbibliotheek in JSON
- ontbrekende en verbeterbare maatregelen bepalen
- meerdere scenario’s opbouwen volgens Trias Energetica
- scenario’s via Gemini doorrekenen
- het beste scenario selecteren
- een adviesrapport genereren

Deze tool is een POC/demo en geen officiële energielabelregistratie.

## Kernprincipes
- Werk voort op de bestaande repository.
- Maak geen nieuwe repository.
- Gebruik de bestaande Flask-, Gemini-, test- en Render-structuur als basis.
- Houd wijzigingen klein, testbaar en modulair.
- Refactor alleen waar functioneel nodig.

## Methodische uitgangspunten
- EP2 / primair fossiel energiegebruik in kWh/m²·jr is leidend voor labelduiding.
- Gebruik NTA 8800 als methodische achtergrond.
- Gebruik ISSO 82.1 als basis voor labelrelevante maatregelen en opnamegerichte interpretatie.
- Gebruik Trias Energetica als leidende logica voor scenario-opbouw:
  1. beperk energievraag
  2. gebruik duurzame energie
  3. vul resterende vraag efficiënt fossiel in
- Neem alleen maatregelen mee die labelrelevant zijn binnen de POC-scope.

## Architectuurregels
- Houd `app.py` dun.
- Plaats businesslogica in aparte services of modules.
- Houd extractie, validatie, maatregelmatching, maatregelimpact, scenario-opbouw, scenario-doorrekening, scenarioselectie en rapportage gescheiden.
- Gebruik Pydantic voor alle gestructureerde data.
- Gebruik JSON-configuratiebestanden als bron van waarheid voor vaste logica.
- Maak de scenario-doorrekening vervangbaar:
  - nu: Gemini
  - later: Vabi of Uniec

## LLM-regels
Gebruik Gemini alleen voor:
- extractie van Vabi naar gestructureerde JSON
- indicatieve maatregel-impact screening
- scenario-doorrekening in de POC
- rapportgeneratie

Gebruik Gemini niet voor:
- harde businessvalidatie
- labelgrenzenlogica
- constraints-normalisatie
- foutafhandeling
- deterministische vergelijkingsregels

Alle LLM-output moet:
- JSON zijn
- parsebaar zijn
- met Pydantic worden gevalideerd
- expliciete aannames bevatten
- expliciete onzekerheden bevatten

## JSON-configuratiebestanden
Houd deze bestanden in de repository als bron van waarheid:
- `data/woningmodel_schema.json`
- `data/vabi_mapping.json`
- `data/maatregelenbibliotheek.json`
- `data/maatregel_relations.json`
- `data/trias_structuur.json`
- `data/scenario_templates.json`
- `data/labelgrenzen.json`
- `data/woningwaarde_label_impact.json`
- `data/aannameregels.json`
- `data/referentiecases.json` (optioneel, gewenst)

Maak deze bestanden inhoudelijk bruikbaar voor de POC; geen lege placeholders.

## Vabi-extractieregels
- Verwacht variatie in Vabi-bestanden.
- Bouw extractie tolerant en null-safe.
- Laat ontbrekende velden nooit een crash veroorzaken.
- Gebruik een flexibel woningmodel met:
  - confidence
  - missing_fields
  - assumptions
- `vabi_mapping.json` moet extractieregels bevatten, geen starre cell mapping.

## Maatregelvergelijking
Vergelijk huidige woningdata met de maatregelenbibliotheek en bepaal per maatregel:
- `missing`
- `improvable`
- `sufficient`
- `not_applicable`
- `capacity_limited`

Gebruik hiervoor:
- canonieke naam
- aliases
- target_metric
- target_value
- comparison_mode
- dependencies
- mutual_exclusions
- capacity logic waar relevant

## Scenario-opbouw
Gebruik vaste scenario-templates.
Implementeer minimaal:
- `MIN_LABELSPRONG`
- `GOEDKOOPSTE_DOELLABEL`
- `GEBALANCEERD`
- `SCHIL_EERST`

Scenario’s moeten:
- starten vanuit de huidige woningstatus
- Trias Energetica volgen
- rekening houden met dependencies en uitsluitingen
- geen onlogische combinaties bevatten

## Scenario-selectie
Selecteer het beste scenario op basis van vaste regels:
1. kies het goedkoopste scenario dat het gewenste label haalt
2. gebruik logische uitvoerbaarheid als secundaire afweging
3. geef voorrang aan consistente Trias-volgorde
4. kies een iets duurder scenario als het goedkoopste technisch of bouwkundig onlogisch is

Als geen scenario het doel-label haalt:
- kies het scenario dat het dichtst bij het doel komt
- rapporteer dit expliciet

## Labelgrenzen en woningwaarde
- Labelgrenzen moeten deterministisch uit `labelgrenzen.json` komen.
- Woningwaarde-impact moet deterministisch uit `woningwaarde_label_impact.json` komen.
- Gemini mag deze regels niet verzinnen.

## Rapportageregels
Het eindrapport moet minimaal bevatten:
- huidig label
- huidige EP2
- gekozen scenario
- nieuw label
- nieuwe EP2
- benodigde maatregelen
- logische volgorde
- totale investering
- maandbesparing
- woningwaarde-stijging
- motivatie voor gekozen scenario
- aannames
- onzekerheden
- POC-disclaimer

De rapportlaag mag geen nieuwe maatregelen of uitkomsten verzinnen die niet in de scenarioselectie zitten.

## Bestandsverantwoordelijkheden
- `app.py`: routes, orchestration, foutafhandeling
- `gemini_service.py`: generieke Gemini-koppeling
- `prompts.py`: alle prompts
- `schemas.py`: Pydantic schema’s
- `validators.py`: deterministische validatie en normalisatie
- `services/*`: domeinspecifieke logica
- `data/*`: JSON-configuratie
- `tests/*`: unit, mock, API en live tests

## Testregels
Voeg tests toe bij elke nieuwe feature.
Gebruik:
- unit tests
- mock tests
- API tests
- live Gemini tests
- stepwise pipeline tests

Verplicht te testen:
- Vabi-extractie
- null-safe extractie
- maatregelmatching
- maatregel-impact
- scenario-opbouw
- scenario-doorrekening
- labelmapping
- woningwaarde-impact
- scenarioselectie
- rapportgeneratie
- end-to-end flow

Tests met externe calls moeten gemockt worden tenzij expliciet live getest.
Live tests moeten expliciet activeerbaar blijven.

## Codespaces en Render
- Zorg dat de tool lokaal, in Codespaces en op Render te testen is.
- Maak tussenstappen inspecteerbaar waar nuttig.
- Houd bestaande deployment-aanpak in stand.

## Veiligheid en configuratie
- Gebruik environment variables voor alle secrets en modelconfiguratie.
- Hardcode nooit API keys of store-namen.
- Gebruik:
  - `GEMINI_API_KEY`
  - `GEMINI_MODEL`
  - `GEMINI_EXTRACTION_MODEL`
  - `GEMINI_SCENARIO_MODEL`
  - `GEMINI_REPORT_MODEL`
  - `GEMINI_METHOD_FILE_SEARCH_STORE`

## Scopebeheersing
Tenzij expliciet gevraagd:
- geen nieuwe frontend
- geen database
- geen async workers
- geen grote frameworkwissels
- geen officiële labelregistratielogica
- geen PDF-generator als dat nog niet gevraagd is

## Definitie van done
Een taak is pas klaar als:
- de code werkt
- de scope is afgedekt
- relevante tests zijn toegevoegd of aangepast
- tests groen zijn
- de flow end-to-end werkt binnen de POC-scope
- geen onnodige scope creep is toegevoegd
