# Energielabel Tool – Labelsprong Advies POC

Flask-gebaseerde POC voor labelsprongadvies op basis van Vabi-rapporten.

De tool combineert:
- **Gemini (LLM)** voor extractie en scenario-advies
- **Deterministische Python** voor validatie, normalisatie, maatregelmatching en rapportopbouw
- **JSON-configuratie** in `data/*.json` als bron voor vaste regels en mappings

> Let op: dit is een **scenario-POC**, geen officiële energielabelregistratie of gecertificeerde NTA 8800-berekening.

---

## Wat de app nu exact doet

De actieve API-flow (`POST /run-poc-flow`) voert deze stappen uit:
1. Input valideren (`RunPocFlowRequest`)
2. Constraints normaliseren (`target_label`, `required_measures`)
3. Bestand downloaden vanaf `file_url`
4. Bestand uploaden naar Gemini Files API
5. Gemini-extractie naar `WoningModel`
6. Null-safe validatie + normalisatie van het woningmodel
7. Deterministische maatregelmatching op basis van maatregelenbibliotheek
8. Gemini scenario-advies op basis van constraints, woningmodel en measure overview
9. Deterministische generatie van `FinalReport`

De response bevat bij succes een object met `constraints`, `scenario_advice` en `final_report`. Bij `debug=true` worden extra tussenlagen teruggegeven.

---

## API-endpoints

### `GET /`
Basale statusinformatie.

### `GET /health`
Health check met `{"status": "ok"}`.

### `GET /test-fixtures/<filename>`
Alleen beschikbaar als `ALLOW_TEST_FILE_ENDPOINT=true|1|yes`.

### `POST /run-poc-flow`
Start de volledige POC-flow.

Voorbeeldrequest:

```json
{
  "user_id": "demo-user",
  "target_label": "B",
  "required_measures": ["hr_glas", "dakisolatie"],
  "file_url": "https://example.com/vabi-report.pdf",
  "debug": false
}
```

Belangrijke validaties:
- JSON body verplicht
- `target_label` moet één van `next_step`, `A` t/m `G` zijn
- `required_measures` mag string, lijst of `null` zijn
- `file_url` moet geldige URL zijn

---

## Architectuur

### Kernbestanden
- `app.py` – Flask app, routes, foutafhandeling, orchestration
- `gemini_service.py` – Gemini client, bestandsupload, JSON parsing, extractie/scenario-advies
- `schemas.py` – Pydantic contracten voor request/response en domeinmodellen
- `validators.py` – constraints-normalisatie en deterministische labelhelpers

### Services
- `services/config_service.py` – JSON-config laden met caching
- `services/extraction_service.py` – ruwe payload → null-safe `WoningModel`
- `services/normalization_service.py` – typecoercie, missing fields, aannameregels
- `services/measure_matching_service.py` – status per maatregel (`missing`, `improvable`, etc.)
- `services/poc_flow_service.py` – orchestratie van de actieve POC-keten
- `services/report_generation_service.py` – finale rapportstructuur

### Aanwezige (momenteel niet gekoppelde) scenario-services
Deze bestaan in de code en zijn getest, maar worden niet direct vanuit `/run-poc-flow` aangeroepen:
- `services/measure_impact_service.py`
- `services/scenario_builder_service.py`
- `services/scenario_calculation_service.py`
- `services/scenario_selection_service.py`

---

## JSON-configuratie (`data/`)

De applicatie gebruikt o.a.:
- `labelgrenzen.json`
- `maatregelenbibliotheek.json`
- `maatregel_relations.json`
- `trias_structuur.json`
- `scenario_templates.json`
- `woningwaarde_label_impact.json`
- `aannameregels.json`
- `vabi_mapping.json`
- `woningmodel_schema.json`
- `referentiecases.json`

Principe: vaste logica hoort in JSON en wordt in code toegepast, niet gedupliceerd.

---

## Omgevingsvariabelen

Verplicht voor Gemini:
- `GEMINI_API_KEY`

Modelkeuzes:
- `GEMINI_MODEL`
- `GEMINI_EXTRACTION_MODEL`
- `GEMINI_SCENARIO_MODEL`

Optioneel:
- `GEMINI_METHOD_FILE_SEARCH_STORE`
- `APP_NAME`
- `FLASK_ENV`
- `ALLOW_TEST_FILE_ENDPOINT`
- `PORT`

---

## Installatie en lokaal draaien

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start de app:

```bash
python app.py
```

Standaard draait Flask op poort `5000` (of `PORT` indien gezet).

---

## Testen

Volledige testsuite:

```bash
pytest -q
```

In deze repository dekt de suite o.a.:
- schema-validatie
- validators
- service-flow
- API-routes
- data-alignment

---

## Grenzen van de POC

- Scenarioresultaten zijn indicatief en niet officieel
- Uitkomsten hangen af van extractiekwaliteit en beschikbare data
- Voor officiële berekeningen is een gecertificeerde rekenkern/koppeling nodig (bijv. Vabi/Uniec)
