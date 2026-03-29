# Energielabel Tool – Labelsprong Advies POC

Deze repository bevat een Flask-gebaseerde AI-tool voor het analyseren van Vabi-rapporten en het genereren van een labelsprongadvies richting een gewenst energielabel.

De tool is bedoeld als **POC/demo** en gebruikt in de huidige fase **Gemini LLM** voor:
- extractie van woningdata uit Vabi-bestanden
- indicatieve maatregel-impact analyse
- scenario-doorrekening
- rapportgeneratie

De architectuur is zo opgezet dat de tijdelijke Gemini-doorrekening later vervangen kan worden door een koppeling met software zoals **Vabi** of **Uniec**.

## Doel van de tool

De tool helpt energielabelaars en adviseurs om op basis van een Vabi-rapport een onderbouwd scenario-advies te genereren richting een gewenst label.

### Input
- Vabi-bestand
- doel-label (bijvoorbeeld A)

### Output
Een adviesrapport met minimaal:
- huidig energielabel
- huidige EP2 in kWh/m²
- gekozen scenario
- nieuw energielabel
- nieuwe EP2 in kWh/m²
- benodigde maatregelen
- logische volgorde van maatregelen
- investering
- maandbesparing
- verwachte woningwaarde-stijging
- aannames en onzekerheden

## Belangrijke disclaimer

Deze tool is een **POC / scenario-adviestool** en geen officiële energielabelregistratie.
De scenario-doorrekening wordt in deze fase indicatief uitgevoerd via Gemini LLM.
De tool is voorbereid op latere vervanging van de rekenlaag door een koppeling met Vabi of Uniec.

## Werking van de tool

De flow bestaat uit de volgende stappen:

1. gebruiker uploadt een Vabi-bestand en kiest een doel-label
2. Gemini zet het Vabi-bestand om naar een gestructureerd woningmodel in JSON
3. de extractie wordt genormaliseerd en gevalideerd
4. de huidige woningstatus wordt vergeleken met de maatregelenbibliotheek
5. per maatregel wordt bepaald of deze ontbreekt, verbeterbaar is of al voldoende aanwezig is
6. er worden meerdere scenario’s opgebouwd volgens Trias Energetica
7. Gemini rekent deze scenario’s indicatief door
8. het beste scenario wordt geselecteerd op basis van vaste regels
9. de tool genereert een adviesrapport

## Methodische basis

De tool is inhoudelijk gebaseerd op:
- NTA 8800 voor EP2-logica en energieprestatiecontext
- ISSO 82.1 voor opname en labelrelevante maatregelen
- Trias Energetica voor scenario-opbouw
- vaste labelgrenzen via JSON-configuratie
- vaste woningwaarde-impact via JSON-configuratie

## Architectuur (high-level)

De tool werkt als hybride systeem:

- **Gemini**
  - extractie
  - maatregel-impact screening
  - scenario-doorrekening
  - rapportage

- **Python + JSON**
  - validatie
  - normalisatie
  - maatregelmatching
  - scenario-opbouwregels
  - labelmapping
  - scenarioselectie
  - waardelogica

## Belangrijkste onderdelen

### Flask / API
- `app.py`
  - routes
  - orchestration
  - foutafhandeling

### Gemini
- `gemini_service.py`
  - generieke Gemini-koppeling

### Prompts
- `prompts.py`
  - extractieprompt
  - maatregel-impact prompt
  - scenario prompt
  - rapportprompt

### Validatie en schema’s
- `schemas.py`
  - Pydantic modellen
- `validators.py`
  - normalisatie en validatie

### Services
Domeinlogica is opgesplitst in services zoals:
- extractie
- normalisatie
- maatregelmatching
- maatregel-impact
- scenario-opbouw
- scenario-doorrekening
- scenarioselectie
- rapportgeneratie

### JSON-configuratie
De vaste logica en domeinkennis staan in JSON-bestanden in `data/`.

## JSON-bestanden

De tool gebruikt de volgende belangrijke configuratiebestanden:

- `data/woningmodel_schema.json`
  - doelschema voor Vabi-extractie
- `data/vabi_mapping.json`
  - flexibele extractieregels voor Vabi-bestanden
- `data/maatregelenbibliotheek.json`
  - labelrelevante maatregelen en doelwaarden
- `data/maatregel_relations.json`
  - dependencies en uitsluitingen
- `data/trias_structuur.json`
  - Trias Energetica volgorde
- `data/scenario_templates.json`
  - standaard scenariofamilies
- `data/labelgrenzen.json`
  - EP2 naar energielabel mapping
- `data/woningwaarde_label_impact.json`
  - indicatieve impact op woningwaarde
- `data/aannameregels.json`
  - conservatieve fallbackregels
- `data/referentiecases.json`
  - referentiecases voor consistentie

## Scenario’s

De tool rekent minimaal de volgende scenario’s door:

- `MIN_LABELSPRONG`
- `GOEDKOOPSTE_DOELLABEL`
- `GEBALANCEERD`
- `SCHIL_EERST`

De scenario’s worden opgebouwd volgens Trias Energetica en mogen geen technisch onlogische combinaties bevatten.

## Maatregelstatus

Per maatregel bepaalt de tool één van de volgende statussen:

- `missing`
- `improvable`
- `sufficient`
- `not_applicable`
- `capacity_limited`

## Labelmapping

Het energielabel wordt niet door Gemini bedacht.
De tool gebruikt `data/labelgrenzen.json` om EP2 deterministisch naar een labelklasse te vertalen.

## Woningwaarde

De verwachte woningwaarde-stijging is indicatief en wordt afgeleid uit `data/woningwaarde_label_impact.json`.
Dit onderdeel is bedoeld voor rapportage en business case, niet voor de kern-doorrekening.

## File Search store

Gemini kan methodiek- en referentiedocumenten ophalen via een bestaande File Search store.

Configuratie:
- `GEMINI_METHOD_FILE_SEARCH_STORE=fileSearchStores/...`

De file store bevat bijvoorbeeld:
- NTA 8800
- ISSO 82.1
- ISSO 82.2
- opnameformulieren
- RVO voorbeeldwoningen
- voorbeeld Vabi-adviesrapporten
- labelgrens-bronnen
- bronnen voor woningwaarde-impact

## Environment variables

Verplicht:
- `GEMINI_API_KEY`

Aanbevolen:
- `GEMINI_MODEL`
- `GEMINI_EXTRACTION_MODEL`
- `GEMINI_SCENARIO_MODEL`
- `GEMINI_REPORT_MODEL`
- `GEMINI_METHOD_FILE_SEARCH_STORE`
- `ALLOW_TEST_FILE_ENDPOINT=true` voor lokale/live testflows

## Lokaal draaien

Voorbeeld:

```bash
pip install -r requirements.txt
flask run
