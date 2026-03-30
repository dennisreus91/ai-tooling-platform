# AGENTS.md

## Projectdoel
Bouw binnen deze repository een Flask-gebaseerde energielabel-tool voor labelsprongadvies op basis van Vabi-rapporten.

De tool moet:
- een Vabi-bestand verwerken
- een doel-label ontvangen
- het bestand via Gemini omzetten naar een gestructureerd woningmodel
- deterministisch maatregelen analyseren
- scenario’s opbouwen volgens Trias Energetica
- scenario’s doorrekenen (POC)
- het beste scenario selecteren
- een technisch adviesrapport genereren

Dit is een **POC / scenario-tool**, geen officiële energielabelregistratie.

---

# 🔑 Kernprincipes

## 1. JSON is de bron van waarheid (kritisch)
Alle vaste logica komt uit `data/*.json`.

Dit betekent:
- GEEN labelgrenzen in Python
- GEEN Trias-logica hardcoderen
- GEEN maatregelregels in code dupliceren

Code mag alleen:
- JSON lezen
- JSON toepassen

NOOIT:
- JSON overschrijven met eigen logica

---

## 2. Deterministisch > AI
De tool is primair deterministisch.

| Onderdeel | Type |
|----------|------|
| Extractie | AI |
| Maatregelmatching | Deterministisch |
| Scenario-opbouw | Deterministisch |
| Labelmapping | Deterministisch |
| Scenarioselectie | Deterministisch |

AI is **ondersteunend**, nooit leidend.

---

## 3. WoningModel is het centrale contract

Alle logica draait op één object: WoningModel

Regels:
- Dit model mag niet impliciet veranderen
- Alle services gebruiken dit als input/output
- Extractie moet hier naartoe mappen
- Validatie moet hierop draaien

Breek dit model niet zonder alle services aan te passen.

---

## 4. Null-safe architectuur
De tool mag nooit falen op ontbrekende data.

Gebruik:
- `null` voor onbekende waarden
- `extractie_meta.missing_fields`
- `extractie_meta.assumptions`
- `extractie_meta.uncertainties`

NOOIT:
- crashen op ontbrekende veldwaarden
- stilzwijgend defaults invullen in extractie

Defaults horen alleen thuis in:
👉 `aannameregels.json`

---

# 🧠 LLM-regels (Gemini)

Gebruik Gemini alleen voor:
- Vabi → WoningModel extractie
- optionele impactanalyse
- optionele scenario-opbouw
- optionele rapporttekst

Gebruik Gemini NIET voor:
- labelbepaling
- EP2-logica
- scenarioselectie
- constraints-validatie
- businessregels

Alle LLM-output moet:
- geldige JSON zijn
- schema-valide zijn (Pydantic)
- expliciete aannames bevatten
- expliciete onzekerheden bevatten

---

# 🚫 Verboden gedrag (zeer belangrijk)

Agents mogen NIET:

- labelgrenzen hardcoderen
- Trias-logica in Python herschrijven
- maatregelen toevoegen buiten `maatregelenbibliotheek.json`
- dependencies negeren
- mutual exclusions negeren
- aannames verstoppen buiten `extractie_meta`
- defaults invullen zonder logging
- AI-uitkomsten blind vertrouwen zonder validatie
- output genereren buiten schema’s

---

# 🔄 Pipeline (contract)

## Stap 1 – Extractie
Input:
- Vabi bestand

Output:
- `WoningModel`

---

## Stap 2 – Validatie & normalisatie
- null-safe
- geen crash
- deduplicatie van meta

---

## Stap 3 – Maatregelmatching
Output:
- `MeasureStatus[]`

---

## Stap 4 – Impactscreening
Output:
- `MeasureImpact[]`

---

## Stap 5 – Scenario-opbouw
Gebaseerd op:
- `scenario_templates.json`
- Trias
- dependencies

Output:
- `ScenarioDefinition[]`

---

## Stap 6 – Scenario-calculatie
POC:
- indicatief

Later:
- vervangbaar met Vabi/Uniec

---

## Stap 7 – Scenarioselectie
Deterministisch:
1. goedkoopste die doel haalt
2. anders dichtstbijzijnde

---

## Stap 8 – Rapport
Gebaseerd op:
- gekozen scenario
- geen nieuwe logica

---

# 🧱 Architectuurregels

- `app.py` = orchestration only
- `services/*` = businesslogica
- `schemas.py` = contract
- `validators.py` = deterministische regels
- `prompts.py` = AI-instructies
- `gemini_service.py` = LLM interface
- `data/*` = waarheid

---

# ⚙️ JSON-configuratie

Gebruik deze bestanden actief:

- `labelgrenzen.json`
- `maatregelenbibliotheek.json`
- `maatregel_relations.json`
- `trias_structuur.json`
- `scenario_templates.json`
- `woningwaarde_label_impact.json`
- `aannameregels.json`
- `vabi_mapping.json`

Deze moeten:
- volledig zijn
- geen placeholders bevatten
- consistent blijven

---

# 🧪 Testregels

Elke wijziging moet getest worden.

Minimaal:
- unit tests
- pipeline tests
- API tests

Verplicht te testen:
- extractie
- null-safe gedrag
- labelmapping
- scenarioselectie
- rapportoutput

---

# ⚙️ Omgevingsvariabelen

Gebruik alleen environment variables:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_EXTRACTION_MODEL`
- `GEMINI_SCENARIO_MODEL`
- `GEMINI_REPORT_MODEL`

Nooit hardcoderen.

---

# 🚀 Extensies

Toekomstige uitbreidingen:

## 1. Officiële rekenkern
- Vabi
- Uniec

## 2. Data-integraties
- BAG
- EP-online

## 3. AI uitbreidingen
- scenario-optimalisatie
- rapportverrijking

---

# 📌 Definitie van Done

Een taak is pas klaar als:

- code werkt
- JSON-structuur gerespecteerd is
- geen businesslogica is gedupliceerd
- tests groen zijn
- pipeline end-to-end werkt
- geen scope creep

---
