# POC/MVP-aanpassingen voor gewenste energielabel-flow

## 1) Huidige status versus gewenste flow

De huidige implementatie ondersteunt al de basispijplijn:
1. intake (`/run-poc-flow`)
2. constraints-normalisatie
3. bestanddownload
4. upload naar Gemini
5. extractie
6. validatie
7. optimalisatie
8. eindrapport
9. JSON-response

Voor jouw gewenste flow zijn er nog gerichte uitbreidingen nodig in **schema’s, prompts, validatie en tests**.

### Statusupdate maart 2026
- De API-flow roept nu expliciet extractie + Python-validatie aan vóór optimalisatie:
  `download_file_to_temp -> upload_case_file -> extract_report_data -> validate_extract -> optimize_report -> build_final_report`.
- De optimalisatie krijgt naast `constraints` nu ook het gevalideerde extract mee (`extracted_report`) als expliciete input.
- Er zijn extra Python-guardrails toegevoegd:
  - `total_cost` moet exact overeenkomen met de som van `selected_measures`.
  - Bij doel `A/B/C` moet `expected_label` het doel halen (of beter); anders expliciete `methodology_conflict`.
- De extractiestap normaliseert nu robuuster LLM-JSON (o.a. komma-getallen zoals `"655,85"` en filtering van onverwachte velden) zodat live-output minder snel faalt op schema-validatie.

---

## 2) Benodigde functionele aanpassingen (POC)

### A. Intake uitbreiden met expliciete context
**Waarom:** Je wil expliciet kunnen meegeven welk label gewenst is en welke maatregelen verplicht zijn (al aanwezig), plus ruimte voor extra case-context.

**Aanpassing:**
- `RunPocFlowRequest` uitbreiden met optionele velden zoals:
  - `property_type` (optioneel)
  - `living_area_m2` (optioneel)
  - `assumptions_allowed` (default `false`)
- Alleen toevoegen als het direct nodig is voor prompts/validatie (scope klein houden).

### B. Extractie expliciet richten op EP2/kWh/m²·jr
**Waarom:** De methodiek vraagt om labelduiding op EP2 (primair fossiel energiegebruik).

**Aanpassing:**
- `ExtractedReport` uitbreiden met velden:
  - `current_ep2_kwh_m2` (float, >= 0)
  - `building_context` (optionele objectstructuur)
  - `source_quality_flags` (lijst met onzekerheden)
- Prompt aanscherpen: EP2 en bronverwijzing verplicht meenemen of expliciet als ontbrekend markeren.

### C. Optimalisatie-uitkomst uitbreiden met gevraagde KPI’s
**Waarom:** Je wilt niet alleen maatregelen en investering, maar ook maandbesparing en woningwaarde-impact.

**Aanpassing:**
- `OptimizationResult` uitbreiden met:
  - `expected_ep2_kwh_m2` (float, >= 0)
  - `monthly_savings_eur` (float, >= 0)
  - `expected_property_value_gain_eur` (float, >= 0)
  - `calculation_notes` (lijst strings, inclusief onzekerheden)
- Python-guardrails toevoegen:
  - `expected_ep2_kwh_m2` moet logisch aansluiten op `resulting_score`/EP2-logica
  - verplichte maatregelen blijven hard afgedwongen

### D. Rapportage-uitkomst synchroon houden met optimalisatie
**Waarom:** Rapport mag inhoudelijk niets wijzigen.

**Aanpassing:**
- `FinalReport` uitbreiden met:
  - `monthly_savings_eur`
  - `expected_property_value_gain_eur`
  - `expected_ep2_kwh_m2`
- In `build_final_report()` al bestaande consistentiechecks uitbreiden met deze velden.

### E. Foutafhandeling verder structureren
**Waarom:** Je wilt expliciete fouten i.p.v. schijnzekerheid.

**Aanpassing:**
- Gestandaardiseerde foutcodes voor:
  - `missing_ep2_data`
  - `insufficient_measures`
  - `methodology_conflict`
  - `invalid_llm_json`
- Deze codes opnemen in API-responses en tests.

---

## 3) MVP-aanvullingen (na POC)

1. **Deterministische rekenkern voor EP2-berekeningen** naast LLM-advies (LLM ondersteunt, Python beslist op kritieke businessregels).
2. **Methodiekversie vastleggen in output** (bijv. `methodology_version: "NTA8800:2024"`).
3. **Herleidbaarheid per maatregel** (welke bronpassage/aanname gebruikte het model).
4. **Scorecards voor onzekerheid** (low/medium/high confidence per KPI).

---

## 4) Benodigde testaanpassingen

## Offline tests (verplicht in CI)

### A. Schema-tests (`tests/test_schemas.py`)
Toevoegen/aanpassen:
- validatie van nieuwe velden in `ExtractedReport`, `OptimizationResult`, `FinalReport`
- negatieve waarden blokkeren voor kosten/KPI’s
- verplichte velden afdwingen

### B. Validator-tests (`tests/test_validators.py`, `tests/test_constraints.py`)
Toevoegen/aanpassen:
- normalisatie van `required_measures` blijft case-insensitief dedupliceren
- expliciete fout bij ontbrekende EP2-kernvelden
- onzekerheden correct in notes/flags

### C. Gemini service mock-tests (`tests/test_gemini_service.py`)
Toevoegen/aanpassen:
- parsing/validatie van nieuwe KPI-velden
- fout op lege/ongeldige JSON blijft hard falen
- rapport-consistentiechecks voor nieuwe KPI’s

### D. API-tests (`tests/test_api.py`)
Toevoegen/aanpassen:
- succesrespons bevat nieuwe outputvelden
- foutcodes machine-leesbaar en stabiel
- `400` voor inputfouten, `500` voor verwerkingsfouten

## Live tests (handmatig/periodiek)

### E. Live extractie test (`tests/test_gemini_live.py`)
Uitbreiden met asserts voor:
- `current_ep2_kwh_m2` aanwezig of expliciet als onzeker gemarkeerd
- JSON-structuur blijft valide

### F. Live end-to-end test (`tests/test_e2e_live.py`)
Uitbreiden met asserts voor:
- `optimization_result.expected_ep2_kwh_m2`
- `optimization_result.monthly_savings_eur`
- `optimization_result.expected_property_value_gain_eur`
- synchronisatie met `final_report`

---

## 5) Testuitvoering in Codespaces/Codex

## Snelle offline regressie
```bash
pytest -q
```

## Gericht op API + service
```bash
pytest -q tests/test_api.py tests/test_gemini_service.py
```

## Live Gemini tests
```bash
RUN_GEMINI_LIVE_TESTS=true GEMINI_API_KEY=*** pytest -q tests/test_gemini_live.py tests/test_e2e_live.py
```

> Advies: live tests niet op elke commit in CI draaien; plan ze als handmatige check of nightly workflow.

---

## 6) Definition of done voor deze flow

Een increment is “done” als:
1. nieuwe schema-velden aanwezig en gevalideerd zijn,
2. Python-guardrails kritieke regels hard afdwingen,
3. offline tests groen zijn,
4. live tests (indien API key aanwezig) groen zijn,
5. API-output volledig machine-leesbaar blijft.
