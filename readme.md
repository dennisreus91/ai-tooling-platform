# Energielabel Tool – Labelsprong Advies POC

Flask POC voor labelsprongadvies op basis van Vabi-rapporten. De flow combineert Gemini (extractie/screening) met deterministische Python-logica (labelmapping, scenarioselectie, validatie).

## Hoofdflow `/run-poc-flow`
1. download/upload Vabi-bestand
2. Gemini extractie naar woningmodel
3. normalisatie + null-safe validatie
4. maatregelmatching (`missing/improvable/sufficient/not_applicable/capacity_limited`)
5. impact-screening
6. scenario-opbouw met Trias templates
7. scenario-doorrekening via vervangbare calculatorlaag
8. scenarioselectie op vaste regels
9. eindrapport met POC-disclaimer

## Structuur
- `app.py`: routes/orchestration
- `services/*`: businesslogica per stap
- `schemas.py`: Pydantic modellen
- `validators.py`: constraints, labelmapping, validatie
- `data/*.json`: bron van waarheid voor vaste logica

## Belangrijke configuratie
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_EXTRACTION_MODEL`
- `GEMINI_SCENARIO_MODEL`
- `GEMINI_REPORT_MODEL`
- `GEMINI_METHOD_FILE_SEARCH_STORE`

## Testen
```bash
pytest -q
```
Live Gemini tests draaien alleen met `GEMINI_API_KEY` en skippen anders automatisch.

## POC beperking
Dit systeem is een scenario-tool en **geen officiële energielabelregistratie**. Voor officiële registratie moet later een rekenkoppeling naar Vabi/Uniec worden ingeplugd via de `ScenarioCalculator` abstractie.
