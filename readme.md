Energielabel Tool – AI Labelsprong Advies

Deze repository bevat een AI-gedreven backend voor het analyseren, optimaliseren en rapporteren van energielabelverbeteringen op basis van een aangeleverd rapport (bijv. Vabi / NTA 8800).

De tool is ontworpen als **modulaire pipeline** waarbij een combinatie van:
- LLM (Google Gemini)
- Python validatie en businesslogica
- gestructureerde output (Pydantic schema’s)

wordt gebruikt om een volledig labelsprongadvies te genereren.

# Doel van de tool
De tool zet een bestaand energielabelrapport om in een concreet advies:

**Input:**
- PDF rapport (bijv. Vabi / energielabel)
- doel (bijv. energielabel A)
- optionele eisen (maatregelen)

**Output:**
- gevalideerde huidige situatie
- geoptimaliseerde maatregelen
- volledig eindrapport met:
  - investeringen
  - besparingen
  - labelverbetering
  - maatregelen
  - onderbouwing

# Architectuur (high-level)
De tool bestaat uit 5 stappen:
1. **Extractie (LLM)**
2. **Validatie (Python)**
3. **Optimalisatie (LLM + regels)**
4. **Rapportage (LLM)**
5. **API response**

PDF → Gemini → JSON → Validatie → Optimalisatie → Rapport → API output

# Belangrijkste modules
## 1. gemini_service.py
Verantwoordelijk voor alle LLM-interacties:
- `upload_case_file()` → upload PDF naar Gemini
- `extract_report_data()` → extractie naar gestructureerde data
- `optimize_report()` → berekenen beste maatregelen
- `build_final_report()` → genereren eindrapport

Belangrijk:
- gebruikt structured output via Pydantic schema’s
- gebruikt File Search store voor methodiekcontext

## 2. schemas.py
Bevat alle datamodellen (Pydantic):
- `ExtractedReport`
- `OptimizationResult`
- `FinalReport`
- `RunPocFlowRequest`

Dit vormt de **contractlaag van de applicatie**

## 3. validators.py
Bevat deterministische logica:
- `normalize_constraints()`
- `validate_extract()`

Zorgt dat LLM-output:
- compleet is
- correct gestructureerd is
- voldoet aan businessregels

## 4. app.py
Flask API met endpoints:

### `/run-poc-flow` (POST)
Volledige pipeline:

1. input validatie
2. PDF downloaden
3. upload naar Gemini
4. extractie
5. validatie
6. optimalisatie
7. rapportage

### `/test-fixtures/<filename>` (GET)
Alleen voor testing:
- serveert lokale test-PDF’s

# POC Flow (belangrijk voor Codex)
De kernflow:

```python
download_file_to_temp()
→ upload_case_file()
→ extract_report_data()
→ validate_extract()
→ optimize_report()
→ build_final_report()

Elke stap is essentieel en moet blijven werken.

# Teststrategie
De repository bevat 3 lagen van tests:

## 1. Unit tests (deterministisch)
- schemas
- validators

## 2. Mock tests
- Gemini wordt gemockt
- snelle en stabiele regressietests

## 3. Live tests (optioneel)
- echte Gemini calls
- gebruikt fixture PDF
- Belangrijke testbestanden:
- test_gemini_service.py
- test_api.py
- test_gemini_live.py
- test_e2e_live.py

# Fixtures
Locatie: tests/fixtures/sample_report.pdf
Dit is een gestandaardiseerd testdocument voor:
- extractie
- end-to-end tests

# Environment variabelen
Verplicht: GEMINI_API_KEY=...

Aanvullend:
- GEMINI_MODEL=gemini-2.5-flash
- GEMINI_OPTIMIZATION_MODEL=gemini-2.5-flash
- GEMINI_REPORT_MODEL=gemini-2.5-flash
- GEMINI_METHOD_FILE_SEARCH_STORE=fileSearchStores/...

Voor live tests:
- GEMINI_API_KEY=<jouw echte key>
- Gebruik `--live-gemini` vlag bij pytest om live tests expliciet te activeren
- ALLOW_TEST_FILE_ENDPOINT=true

# Belangrijke ontwerpprincipes
## 1. Scheiding van verantwoordelijkheden
- LLM → interpretatie & generatie
- Python → validatie & controle

## 2. Deterministische controle
Alle output van Gemini wordt:
- gevalideerd
- genormaliseerd

## 3. Structured output verplicht
Alle LLM output moet voldoen aan schema’s.

## 4. Geen businesslogica in prompts
Businessregels zitten in Python, niet in de LLM.

# Belangrijke regels voor aanpassingen (voor Codex)
Bij wijzigingen:
- behoud bestaande flow
- wijzig geen schema’s zonder testupdate
- voeg altijd tests toe bij nieuwe logica
- breek geen /run-poc-flow contract

# Testinstructies
- Standaard tests (zonder echte API-calls): `pytest -q`
- Live Gemini tests (met echte API-calls): `pytest --live-gemini tests/test_gemini_live.py tests/test_e2e_live.py -q`

Live tests falen nu expliciet als `GEMINI_API_KEY` of `tests/fixtures/sample_report.pdf` ontbreekt. Hierdoor kun je in Codespaces betrouwbaar zien dat echte Gemini-calls zijn uitgevoerd in plaats van geskipte tests.

# Deployment
- Flask app
- draait op Render
- start via: gunicorn app:app

# Toekomstige uitbreidingen
- betere optimalisatie-algoritmes
- kosten/besparing modellen
- koppeling met subsidies
- woningwaarde impact
- bulk analyse per postcode

# Belangrijk voor AI agents (Codex)
Deze repository is ontworpen om:
- autonoom verbeterd te worden
- getest te worden via pytest
- veilig aangepast te worden via kleine iteraties

Verwachting:
- analyseer eerst tests
- wijzig alleen relevante modules
- valideer altijd via tests

# Samenvatting
Deze tool:
- leest energielabelrapporten (PDF)
- zet deze om naar gestructureerde data
- optimaliseert maatregelen
- genereert een professioneel rapport
→ volledig geautomatiseerd via AI + validatie

## POC/MVP uitwerking
Zie `docs/poc_mvp_aanpassingen.md` voor de gevraagde flow-aanpassingen en teststrategie.
