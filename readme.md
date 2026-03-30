# Energielabel Tool – Labelsprong Advies POC

Flask-based POC voor labelsprongadvies op basis van Vabi-rapporten.

De tool combineert:
- **LLM (Gemini)** → extractie en optionele AI-logica  
- **Deterministische Python** → labelmapping, scenarioselectie, validatie  
- **JSON-configuratie** → bron van waarheid voor regels en aannames  

---

# 🧠 Architectuurprincipes

## 1. JSON is de bron van waarheid
Alle vaste logica zit in `data/*.json`, o.a.:
- `labelgrenzen.json` → EP2 → label mapping  
- `maatregel_relations.json` → afhankelijkheden & conflicts  
- `trias_structuur.json` → Trias Energetica  
- `scenario_templates.json` → scenario-opbouw  
- `aannameregels.json` → fallback logica  

👉 Code mag deze regels **niet hardcoderen**

---

## 2. Scheiding AI vs deterministisch

| Onderdeel | Type |
|----------|------|
| Extractie | AI (Gemini) |
| Maatregelmatching | Deterministisch |
| Scenario-opbouw | Deterministisch |
| Labelbepaling | Deterministisch |
| Rapportage | Deterministisch / optioneel AI |

👉 AI mag nooit beslissende logica overschrijven

---

## 3. Null-safe extractie
De tool is ontworpen om **nooit te falen op ontbrekende data**

Ontbrekende info wordt:
- `null` in model
- gelogd in `extractie_meta.missing_fields`
- aangevuld via aannames (indien nodig)

---

# 🔄 Hoofdflow `/run-poc-flow`

1. Download Vabi-bestand
2. Upload naar Gemini
3. Extractie → `WoningModel`
4. Validatie + normalisatie
5. Maatregelmatching:
   - `missing`
   - `improvable`
   - `sufficient`
   - `not_applicable`
   - `capacity_limited`
6. Impact-screening
7. Scenario-opbouw (Trias gestuurd)
8. Scenario-doorrekening (calculatorlaag)
9. Scenarioselectie (deterministisch)
10. Eindrapport (POC)

---

# 🧱 Kerncomponenten

## `app.py`
- API endpoints
- orchestration van de flow

## `services/`
Bevat alle businesslogica:

- `normalization_service.py`
- `measure_matching_service.py`
- `measure_impact_service.py`
- `scenario_builder_service.py`
- `scenario_calculation_service.py`
- `scenario_selection_service.py`
- `report_generation_service.py`

## `schemas.py`
- Pydantic datamodellen
- contract tussen alle lagen

## `validators.py`
- labelmapping (EP2 → label)
- constraint normalisatie
- woningmodel validatie

## `gemini_service.py`
- LLM integratie
- JSON parsing
- extractie naar WoningModel

---

# 🏠 WoningModel (kern van de tool)

Belangrijkste structuur:

```json
{
  "meta": {},
  "woning": {},
  "prestatie": {
    "current_ep2_kwh_m2": null,
    "current_label": null
  },
  "bouwdelen": {},
  "installaties": {},
  "maatwerkadvies": {},
  "extractie_meta": {
    "confidence": 0.0,
    "missing_fields": [],
    "assumptions": [],
    "uncertainties": []
  }
}
