SYSTEM_INSTRUCTION_BASELINE = """
Je bent een normgestuurde assistent voor energielabeladvies.
Geef uitsluitend geldige JSON terug zonder markdown of vrije tekst.
"""

METHODOLOGY_SOURCE_GUIDANCE = """
Methodiekbronnen in file_search:
- NTA8800
- ISSO 82.1
- Energielabeltabel
"""

EXTRACT_REPORT_USER_PROMPT = """
Zet Vabi-document om naar gestructureerd woningmodel JSON.
Verplicht: assumptions, uncertainties, missing_fields, confidence.
"""

OPTIMIZE_REPORT_USER_PROMPT = """
Reken scenario's indicatief door en retourneer alleen JSON.
"""

BUILD_FINAL_REPORT_USER_PROMPT = """
Genereer eindrapport als JSON op basis van gekozen scenario.
"""

MEASURE_IMPACT_PROMPT = """
Analyseer alleen missing/improvable maatregelen en geef JSON met impact-inschatting.
"""


def build_extract_report_prompt() -> str:
    return f"{EXTRACT_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"


def build_optimize_report_prompt() -> str:
    return f"{OPTIMIZE_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"


def build_final_report_prompt() -> str:
    return f"{BUILD_FINAL_REPORT_USER_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"


def build_measure_impact_prompt() -> str:
    return f"{MEASURE_IMPACT_PROMPT.strip()}\n\n{METHODOLOGY_SOURCE_GUIDANCE.strip()}"
