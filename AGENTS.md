# AGENTS.md

## Projectdoel (huidige codebasis)
Deze repository bevat een Flask-gebaseerde POC-tool voor labelsprongadvies op basis van een extern Vabi-bestand (`file_url`).

De runtime-flow die **nu** actief is op endpointniveau:
1. Download bestand via URL
2. Upload naar Gemini Files API
3. Gemini-extractie naar `WoningModel`
4. Deterministische validatie/normalisatie
5. Deterministische maatregelmatching
6. Gemini scenario-advies (met JSON-config als context)
7. Deterministische eindrapport-assemblage

Dit is een **POC / scenario-tool** en geen officiële energielabelregistratie of gecertificeerde NTA 8800-berekening.

---

## 🔑 Kernprincipes

## 1. JSON is bron van waarheid voor vaste regels
Gebruik configuratie uit `data/*.json` via `services/config_service.py`.

Belangrijk:
- Labelgrenzen komen uit `data/labelgrenzen.json`
- Maatregelen komen uit `data/maatregelenbibliotheek.json`
- Relaties/dependencies komen uit `data/maatregel_relations.json`
- Trias en templates komen uit `data/trias_structuur.json` en `data/scenario_templates.json`
- Aannames komen uit `data/aannameregels.json`

Voeg geen nieuwe vaste businessregels toe buiten JSON als die regel logisch in configuratie thuishoort.

---

## 2. AI + deterministisch (huidige taakverdeling)

| Onderdeel | Huidig gedrag |
|---|---|
| Bestandsdownload/upload | Deterministisch |
| Vabi/PDF → `WoningModel` extractie | Gemini |
| Structuurcoercie + null-safe template | Deterministisch |
| Validatie + normalisatie | Deterministisch |
| Maatregelmatching | Deterministisch |
| Scenario-advies voor actieve API-flow | Gemini |
| Final report-opbouw | Deterministisch |

Belangrijk: in de huidige `/run-poc-flow` wordt scenario-opbouw/-calculatie/-selectie niet lokaal doorgerekend, maar via `get_scenario_advice_with_gemini(...)` opgehaald en daarna gevalideerd.

---

## 3. `WoningModel` is het centrale contract
Alle ketenstappen werken op `WoningModel` (zie `schemas.py`).

Regels:
- Houd wijzigingen aan `WoningModel` expliciet en controleer impact op services/tests.
- Zorg dat extractie-output altijd schema-valide wordt gemaakt.
- Houd `extractie_meta` consequent gevuld met onzekerheden en missende velden.

---

## 4. Null-safe architectuur
Ontbrekende velden moeten niet crashen.

Gebruik:
- `null`/lege collecties waar passend
- `extractie_meta.missing_fields`
- `extractie_meta.assumptions`
- `extractie_meta.uncertainties`

Geen stille defaults in extractiecode; alleen expliciet, traceerbaar en bij voorkeur via configuratie of gedocumenteerde fallback.

---

## 🧠 Gemini-regels
Gemini wordt in de huidige code gebruikt voor:
- extractie (`extract_woningmodel_data`)
- scenario-advies (`get_scenario_advice_with_gemini`)

Alle LLM-output moet:
- parsebaar JSON zijn
- schema-valide worden gemaakt met Pydantic
- waar nodig genormaliseerd worden (lijstvelden, numerieke velden, motivation fallback)

Gebruik Gemini niet als ongevalideerde bron voor businessbeslissingen.

---

## 🔄 Actieve pipeline (contract in code)
De API-flow in `app.py` + `services/poc_flow_service.py`:

1. `RunPocFlowRequest` valideren (`schemas.py`)
2. Constraints normaliseren (`validators.normalize_constraints`)
3. Bestand downloaden (`gemini_service.download_file_to_temp`)
4. Bestand uploaden (`gemini_service.upload_case_file`)
5. Woningmodel-extractie (`gemini_service.extract_woningmodel_data`)
6. Woningmodel-normalisatie (`services/normalization_service.normalize_woningmodel`)
7. Maatregelmatching (`services/measure_matching_service.match_measures`)
8. MeasureOverview bouwen (missing/improvable)
9. Scenario-advies ophalen via Gemini (`get_scenario_advice_with_gemini`)
10. Final report bouwen (`services/report_generation_service.build_final_report`)

Bij `debug=false` worden zware tussenlagen uit de API-response verwijderd.

---

## 🧱 Architectuur (huidige rolverdeling)
- `app.py`: Flask app + endpoint orchestration + foutafhandeling
- `gemini_service.py`: Gemini client, file upload, JSON parsing, extractie/scenario-advies
- `schemas.py`: Pydantic contracten
- `validators.py`: constraint-normalisatie, labelfuncties, woningmodel-validatie
- `services/config_service.py`: centrale JSON-loaders met caching
- `services/extraction_service.py`: payload → null-safe `WoningModel`
- `services/normalization_service.py`: type-normalisatie + aannameregelverwerking
- `services/measure_matching_service.py`: deterministische maatregelstatus
- `services/report_generation_service.py`: eindrapportobject

Beschikbare maar niet in de actieve API-flow gekoppelde scenario-services:
- `services/measure_impact_service.py`
- `services/scenario_builder_service.py`
- `services/scenario_calculation_service.py`
- `services/scenario_selection_service.py`

---

## ⚙️ JSON-configuratie
Actief aanwezig in `data/`:
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

Houd configuratie intern consistent met schema’s en services.

---

## 🧪 Testregels
Bij wijzigingen minimaal draaien:
- unit tests
- service/pipeline tests
- API tests

Standaard volledige suite:
- `pytest -q`

Live/integratietests kunnen afhankelijk zijn van externe credentials of netwerkcondities.

---

## ⚙️ Omgevingsvariabelen
Gebruik bestaande env vars:
- `GEMINI_API_KEY` (verplicht voor Gemini-calls)
- `GEMINI_MODEL`
- `GEMINI_EXTRACTION_MODEL`
- `GEMINI_SCENARIO_MODEL`
- `GEMINI_METHOD_FILE_SEARCH_STORE`
- `APP_NAME`
- `FLASK_ENV`
- `ALLOW_TEST_FILE_ENDPOINT`
- `PORT`

Nooit API keys hardcoderen.

---

## 🚫 Verboden gedrag
- Businessregels hardcoderen als ze uit JSON horen te komen
- Ongevalideerde LLM-output direct vertrouwen
- Ontbrekende waarden stil maskeren zonder meta-logging
- Endpoint-contracten wijzigen zonder schema/testupdates

---

## ✅ Definitie van done
Een wijziging is af als:
- code werkt
- documentatie overeenkomt met de werkelijke codeflow
- JSON-centrische logica gerespecteerd blijft
- tests groen zijn
- geen onbedoelde scope-uitbreiding plaatsvindt
