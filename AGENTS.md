# AGENTS.md

## Projectdoel
Bouw binnen repository `ai-tooling-platform` een Flask-gebaseerde AI-tool voor energielabelaars en adviseurs die Vabi-, EPA-, XML- en PDF-rapporten omzet naar een gestructureerd verduurzamingsadvies.

De tool moet in opeenvolgende fases:
- intake ontvangen vanuit Typebot of een vergelijkbare frontend
- woning- en maatregeldata extraheren uit geüploade bestanden
- extracted data valideren en normaliseren
- methodiekgestuurd optimaliseren op basis van constraints
- een gestructureerd eindrapport genereren
- fouten expliciet signaleren als data ontbreekt of onzeker is

## Productcontext
De tool is bedoeld als POC voor een Labelsprong-adviesflow.

Input:
- `user_id`
- `target_label`
- `required_measures`
- `file_url`

Verwachte flow:
1. intake ontvangen
2. constraints normaliseren
3. bestand downloaden
4. bestand uploaden naar Gemini
5. extractie uitvoeren
6. extractie valideren
7. optimalisatie uitvoeren
8. eindrapport genereren
9. JSON-response teruggeven

## Functionele uitgangspunten
- Het energielabel wordt bepaald op basis van **EP2 / primair fossiel energiegebruik in kWh/m²·jr**.
- Rekenmethodiek en interpretatie moeten aansluiten op:
  - NTA 8800:2024
  - ISSO 82.1 (6e druk)
  - Energielabel tabel
  - maatregelenbestand / maatregelencatalogus
- De methodiekdocumentatie is leidend voor de rekenwijze.
- Het geüploade rapport is leidend voor de casusdata.
- Als brondata ontbreken of onzeker zijn, moet de tool dit expliciet melden en niet gokken.
- Output moet zoveel mogelijk bestaan uit parsebare, gestructureerde JSON.

## Domeinregels
- Gebruik labelgrenzen en EP2-logica als vaste basis voor labelduiding.
- Werk conservatief bij onzekerheid.
- Voeg geen maatregelen, kosten, labels of technische aannames toe die niet uit de casusdata, methodiekcontext of expliciete validatieregels volgen.
- Verplichte maatregelen uit `required_measures` moeten in de optimalisatie-uitkomst worden gerespecteerd.
- De rapportagelaag mag de optimalisatie-uitkomst niet inhoudelijk wijzigen.
- Als een maatregel technisch of inhoudelijk niet plausibel is, moet die worden uitgesloten of expliciet als onzeker worden gemarkeerd.
- Fouten moeten expliciet teruggegeven worden; geen hallucinaties, geen schijnzekerheid.

## Architectuurregels
- Houd `app.py` dun; orchestration mag daar staan, businesslogica niet.
- Plaats businesslogica in losse modules.
- Gebruik Pydantic-schema’s voor alle gestructureerde data.
- Gebruik aparte modules voor:
  - `schemas.py`
  - `validators.py`
  - `prompts.py`
  - `gemini_service.py`
- Maak functies klein, testbaar en goed afgebakend.
- Gebruik structured JSON output waar mogelijk.
- Voeg tests toe bij iedere nieuwe feature.

## Bestandverantwoordelijkheden
- `app.py`
  - Flask app factory
  - routes
  - orchestration van bestaande services
  - foutafhandeling
- `schemas.py`
  - Pydantic-schema’s voor intake, extractie, optimalisatie en rapportage
- `validators.py`
  - normalisatie van constraints
  - validatie en opschoning van extracted data
- `prompts.py`
  - alle LLM-prompts
- `gemini_service.py`
  - bestanddownload
  - bestandupload
  - extractie
  - optimalisatie
  - rapportage
- `tests/`
  - unit tests
  - API tests
  - integratietests met mocks

## Schema-uitgangspunten
Gebruik minimaal deze schema’s:
- `RunPocFlowRequest`
- `Constraints`
- `Measure`
- `ExtractedReport`
- `OptimizationMeasure`
- `OptimizationResult`
- `FinalReport`

Schema-intentie:
- `Constraints`
  - genormaliseerde gebruikersconstraints
- `Measure`
  - extracted maatregel uit bronbestand
- `ExtractedReport`
  - gestructureerde extractie uit rapport
- `OptimizationResult`
  - gekozen maatregelen, totale kosten, scoretoename, verwacht label
- `FinalReport`
  - klantgericht eindrapport op basis van optimalisatie-uitkomst

## Validatieregels
### Constraints
- `target_label` moet genormaliseerd worden naar:
  - `next_step`
  - `A`
  - `B`
  - `C`
- `required_measures` mag:
  - string zijn
  - lijst van strings zijn
  - null zijn
- `required_measures` moet genormaliseerd worden naar een schone lijst zonder lege waarden en zonder case-insensitieve duplicaten

### Extracted data
- `current_label` moet aanwezig zijn
- `current_score` moet bruikbaar zijn
- extracted measures moeten opgeschoond worden
- measures met:
  - negatieve kosten
  - `score_gain <= 0`
  moeten verwijderd worden
- onbruikbare extracties moeten een expliciete fout geven
- validatie mag geen LLM gebruiken

## LLM-regels
- Gebruik de LLM alleen voor:
  - extractie
  - optimalisatie in de POC
  - rapportage
- Gebruik de LLM niet voor:
  - business-validatie
  - constraints-normalisatie
  - harde foutafhandeling
- Vertrouw niet uitsluitend op prompt-naleving voor harde businessregels; controleer kritieke regels ook in Python.
- Parse LLM-output altijd als JSON en valideer die vervolgens met Pydantic.
- Als LLM-output leeg, ongeldig of niet-parsebaar is, geef een expliciete fout terug.

## Gemini-regels
- Gebruik environment variables voor alle Gemini-configuratie.
- Hardcode nooit API keys of store-namen.
- Modellen moeten configureerbaar zijn via env vars:
  - `GEMINI_MODEL`
  - `GEMINI_OPTIMIZATION_MODEL`
  - `GEMINI_REPORT_MODEL`
- Methodiekcontext via File Search moet configureerbaar zijn via:
  - `GEMINI_METHOD_FILE_SEARCH_STORE`
- Tests voor Gemini-functionaliteit moeten met mocks draaien, zonder echte API-calls.

## Promptregels
- Prompts moeten in `prompts.py` staan.
- Prompts moeten:
  - alleen JSON-output vragen
  - geen markdown toestaan
  - geen vrije tekst buiten JSON toestaan
  - duidelijk maken wat wel en niet mag
- Prompts mogen helpen sturen, maar harde bedrijfsregels moeten ook in Python afgedwongen worden.

## Rapportageregels
- Het eindrapport moet uitsluitend gebaseerd zijn op:
  - `OptimizationResult`
  - `Constraints`
- Voeg geen nieuwe maatregelen toe in de rapportagelaag.
- `expected_label` in het rapport moet exact overeenkomen met `OptimizationResult.expected_label`.
- `total_investment` in het rapport moet exact overeenkomen met `OptimizationResult.total_cost`.
- Als dat niet zo is, moet de rapportagestap expliciet falen.

## API-regels
- De API moet altijd JSON teruggeven.
- Inputfouten moeten als `400` terugkomen.
- Verwerkingsfouten moeten expliciet en gestructureerd terugkomen.
- Houd foutcodes voorspelbaar en machine-leesbaar.
- `/health` moet `{"status": "ok"}` teruggeven.
- `/run-poc-flow` is de hoofdroute voor de POC-flow.

## Kwaliteitsregels
- Na iedere wijziging moeten tests draaien.
- Voeg geen grote refactors toe buiten de scope van de taak.
- Hardcode nooit secrets of API keys.
- Gebruik env vars voor configuratie.
- Geef fouten expliciet en gestructureerd terug.
- Houd wijzigingen klein en gericht.
- Laat de API voorspelbaar blijven; breek bestaande responses niet zonder noodzaak.
- Voeg geen ongebruikte code toe.
- Voeg geen “tijdelijke” shortcuts toe zonder dat expliciet te benoemen.

## Testregels
- Voeg tests toe bij iedere nieuwe feature.
- Gebruik unit tests voor:
  - schema-validatie
  - validators
  - servicefuncties
- Gebruik API tests voor endpointgedrag.
- Gebruik mocks voor externe calls:
  - netwerkverkeer
  - Gemini
  - file upload/download
- Houd tests deterministisch.
- Als tests falen, herstel alleen de directe oorzaak van de failure.
- Voeg geen refactors toe in een fix-run tenzij strikt noodzakelijk.

## Workflowregels
- Werk per taak in kleine, afgebakende stappen.
- Wijzig alleen de bestanden die nodig zijn voor de taak.
- Definieer per taak duidelijk wanneer deze “done” is.
- Breid het project gefaseerd uit; bouw nooit meerdere grote functionele lagen tegelijk.
- Voer geen grote refactors uit buiten de scope van de taak.
- Als een taak draait om een bugfix of CI-failure:
  - fix alleen de failure
  - verander geen omliggende architectuur zonder noodzaak

## Scopebeheersing
- Houd je strikt aan de gevraagde fase.
- Voeg geen toekomstige features alvast toe.
- Voeg geen PDF-generatie toe tenzij daar expliciet om gevraagd is.
- Voeg geen async verwerking toe tenzij daar expliciet om gevraagd is.
- Voeg geen database of opslaglaag toe tenzij daar expliciet om gevraagd is.
- Voeg geen frontendlogica toe tenzij daar expliciet om gevraagd is.

## CI- en reviewregels
- Iedere wijziging moet door GitHub Actions gevalideerd worden voordat deze naar `main` gaat.
- Houd wijzigingen klein en gericht zodat failures eenvoudig herleidbaar zijn.
- PR’s moeten merge-ready zijn:
  - groene tests
  - beperkte scope
  - geen ongebruikte code
  - geen scope creep
- Gebruik waar relevant `@codex review` op grotere pull requests.
- Laat reviews vooral letten op:
  - foutafhandeling
  - schema-validatie
  - regressierisico
  - testdekking
  - onnodige scope-uitbreiding

## Merge-discipline
- `main` is protected.
- Directe pushes naar `main` zijn niet toegestaan.
- Alleen merge na succesvolle CI-checks en review.
- Houd pull requests klein en inhoudelijk coherent.
- Gebruik CI als harde kwaliteitsgate, niet alleen als informatief signaal.

## Veiligheids- en configuratieregels
- Secrets alleen via environment variables of GitHub/Render secrets.
- Geen credentials in code, tests of voorbeeldbestanden.
- `.env.example` mag alleen placeholders bevatten.
- Productie- en testconfiguratie moeten van elkaar gescheiden blijven.

## Stijlregels voor code
- Schrijf duidelijke, eenvoudige Python-code.
- Geef functies een enkel doel.
- Gebruik expliciete namen.
- Vermijd verborgen bijwerkingen.
- Vermijd onnodige abstractielagen.
- Geef docstrings aan publieke functies waar dat helpt.
- Houd foutmeldingen concreet en bruikbaar.

## Definitie van done
Een taak is pas klaar als:
- de code werkt
- de scope volledig is afgedekt
- relevante tests zijn toegevoegd of bijgewerkt
- alle tests groen zijn
- geen onnodige extra wijzigingen zijn meegenomen

## Fasegerichte ontwikkelvolgorde
Werk bij voorkeur in deze volgorde:
1. fundament
2. intake-endpoint
3. schema-laag
4. validatielaag
5. Gemini extractielaag
6. optimalisatielaag
7. rapportagelaag
8. orchestrationflow
9. CI- en merge-discipline

## Wat in deze repo niet automatisch mag gebeuren
Tenzij expliciet gevraagd:
- geen grote herstructurering van bestanden
- geen migratie naar een ander framework
- geen vervanging van Flask
- geen vervanging van Pydantic
- geen wijziging van responseformaten zonder noodzaak
- geen toevoeging van databases, queues of background workers
- geen wijziging van businessregels buiten de huidige taak

## Belangrijkste ontwikkelprincipe
Deze repo bouwt een normgestuurde energielabel-tool waarin:
- methodiek leidend is voor de berekeningslogica
- casusdata leidend is voor de woninginput
- validatie in Python plaatsvindt
- LLM-output altijd gecontroleerd wordt
- fouten expliciet gemeld worden
- kleine, testbare stappen belangrijker zijn dan snelheid

  ## Critical repair rules
- Never hardcode outputs just to satisfy tests.
- Never bypass validation to make tests pass.
- Fix root causes, not symptoms.
- Do not remove or weaken failing tests unless the test itself is incorrect.
- Preserve existing business logic unless the task explicitly changes it.
- Prefer the smallest safe patch.
- Do not refactor unrelated code during a repair run.
- Stop after the requested scope is fixed.
