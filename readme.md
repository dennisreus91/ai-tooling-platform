# Energielabel Tool – Labelsprong Advies POC

Flask-gebaseerde POC voor labelsprongadvies op basis van Vabi/PDF-rapporten via `file_url`.

De tool combineert:
- **Gemini (LLM)** voor extractie, maatregel-gap-analyse en scenario-advies
- **Deterministische Python** voor validatie, normalisatie, verrijking, fallback-berekeningen en rapportopbouw
- **JSON-configuratie** in `data/*.json` als bron voor vaste regels en mappings

> Let op: dit is een **scenario-POC**, geen officiële energielabelregistratie of gecertificeerde NTA 8800-berekening.

---

## Huidige actieve flow (`POST /run-poc-flow`)

1. Request valideren met `RunPocFlowRequest` (`schemas.py`)
2. Constraints normaliseren (`validators.normalize_constraints`)
3. Bestand downloaden vanaf `file_url` (`gemini_service.download_file_to_temp`)
4. Bestand uploaden naar Gemini Files API (`gemini_service.upload_case_file`)
5. Gemini-extractie naar `WoningModel` (`gemini_service.extract_woningmodel_data`)
6. Woningmodel normaliseren (`services/normalization_service.normalize_woningmodel`)
7. EP2 bepalen (direct of via labelgrenzen-fallback)
8. Gemini measure-gap-analyse ophalen (`gemini_service.get_measure_gap_analysis_with_gemini`)
   - Daarna deterministische normalisatie/verrijking met maatregelenbibliotheek + quantity-resolutie
9. Gemini scenario-advies ophalen (`gemini_service.get_scenario_advice_with_gemini`)
   - Daarna deterministische normalisatie/fallbacks (o.a. investering, EP2, motivatie)
10. Deterministisch `FinalReport` bouwen (`services/report_generation_service.build_final_report`)

De flow-orchestratie staat in `services/poc_flow_service.py` en wordt aangeroepen vanuit `app.py`.


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

Foutcodes (samengevat):
- `invalid_json`, `validation_error`, `constraint_error`
- processing-codes zoals `missing_ep2_data`, `invalid_llm_json`, `processing_error`

---

## Responsegedrag (`debug`)

- `debug=true`: volledige pipeline-uitkomst incl. `woningmodel`, `measure_statuses`, `measure_overview`, `scenario_advice`, `final_report`.
- `debug=false` (default): zware tussenlagen worden verwijderd; output bevat primair `constraints` en `final_report`.

---

## Architectuur

### Kernbestanden
- `app.py` – Flask app, routes, foutafhandeling, orchestration
- `gemini_service.py` – Gemini client, file upload, JSON parsing, extractie + measure gap + scenario-advies
- `schemas.py` – Pydantic contracten voor request/response en domeinmodellen
- `validators.py` – constraints-normalisatie en labelhelpers

### Actief gebruikte services
- `services/config_service.py` – JSON-config laden met caching
- `services/extraction_service.py` – ruwe LLM payload → null-safe `WoningModel`
- `services/normalization_service.py` – typecoercie, missing fields, aannameregels
- `services/poc_flow_service.py` – orchestratie van de actieve POC-keten
- `services/report_generation_service.py` – finale rapportstructuur

### Aanwezige maar niet actief gekoppelde scenario-services
- `services/measure_matching_service.py`
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

Principe: vaste businessregels horen in JSON en worden in code toegepast, niet hardcoded gedupliceerd.

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
python app.py
```

Standaard draait Flask op poort `5000` (of `PORT` indien gezet).

---

## Testen

Volledige testsuite:

```bash
pytest -q
```

Naast unit-tests bevat de repository ook live/integratietests die afhankelijk kunnen zijn van credentials of netwerk.

---

## Grenzen van de POC

- Scenarioresultaten zijn indicatief en niet officieel
- Uitkomsten hangen af van extractiekwaliteit en beschikbare data
- Voor officiële berekeningen is een gecertificeerde rekenkern/koppeling nodig (bijv. Vabi/Uniec)
