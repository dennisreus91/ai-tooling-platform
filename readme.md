# 🏡 Energielabel Tool – AI Labelsprong Advies

Deze repository bevat een AI-gedreven backend voor het analyseren, optimaliseren en rapporteren van energielabelverbeteringen op basis van een aangeleverd rapport (bijv. Vabi / NTA 8800).

De tool is ontworpen als **modulaire pipeline** waarbij een combinatie van:
- LLM (Google Gemini)
- Python validatie en businesslogica
- gestructureerde output (Pydantic schema’s)

wordt gebruikt om een volledig labelsprongadvies te genereren.

---

# 🎯 Doel van de tool

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
  - onderbouwing

---

# 🧠 Architectuur (high-level)

De tool bestaat uit 5 stappen:

1. **Extractie (LLM)**
2. **Validatie (Python)**
3. **Optimalisatie (LLM + regels)**
4. **Rapportage (LLM)**
5. **API response**
