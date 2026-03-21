# AGENTS.md

## Projectdoel
Bouw een Flask-gebaseerde AI-tool voor energielabelaars die Vabi-rapporten, XML-bestanden of PDF's omzet naar een verduurzamingsrapport.

De tool moet in latere fases:
- intake ontvangen vanuit Typebot
- woning- en maatregeldata extraheren uit bestanden
- data valideren en normaliseren
- methodiekgestuurd optimaliseren
- een gestructureerd verduurzamingsrapport genereren

## Functionele uitgangspunten
- Het energielabel wordt bepaald op basis van EP2 / primair fossiel energiegebruik in kWh/m²·jr.
- Rekenmethodiek en interpretatie moeten aansluiten op:
  - NTA 8800:2024
  - ISSO 82.1 (6e druk)
  - Energielabel tabel
  - maatregelencatalogus / maatregelenbestand
- Als brondata ontbreken of onzeker zijn, moet de tool dit expliciet melden en niet gokken.

## Architectuurregels
- Houd `app.py` dun; businesslogica hoort in losse modules.
- Gebruik Pydantic-schema's voor alle gestructureerde data zodra schema's worden toegevoegd.
- Gebruik aparte modules voor prompts, validators, schemas en Gemini-service zodra deze nodig zijn.
- Gebruik structured JSON output waar mogelijk.
- Maak functies klein en testbaar.
- Voeg tests toe bij iedere nieuwe feature.

## Kwaliteitsregels
- Na iedere wijziging moeten tests draaien.
- Voeg geen grote refactors toe buiten de scope van de taak.
- Hardcode nooit secrets of API keys.
- Gebruik env vars voor configuratie.
- Geef fouten expliciet en gestructureerd terug.
- Laat de API altijd JSON teruggeven.

## Workflowregels
- Werk per taak in kleine, afgebakende stappen.
- Wijzig alleen de bestanden die nodig zijn voor de taak.
- Definieer per taak duidelijk wanneer deze "done" is.
- Als tests falen, herstel alleen de oorzaak van de failure.
- Breid het project gefaseerd uit; bouw nooit meerdere grote functionele lagen tegelijk.

## Definitie van done
Een taak is pas klaar als:
- de code werkt
- de scope volledig is afgedekt
- relevante tests zijn toegevoegd of bijgewerkt
- alle tests groen zijn

## Fase 1 scope
In deze fase alleen:
- Flask-projectbasis
- `/health` endpoint
- Render-configuratie
- environment voorbeeldbestand
- basistest
- CI-workflow

Voeg in deze fase nog geen Gemini-logica, intakeflow, extractie, validatie of optimalisatie toe.
