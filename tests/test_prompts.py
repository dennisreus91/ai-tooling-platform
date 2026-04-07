from prompts import (
    METHODOLOGY_SOURCE_GUIDANCE,
    SYSTEM_INSTRUCTION_BASELINE,
    TRIAS_ENERGETICA_INSTRUCTIE,
    build_extract_report_prompt,
    build_scenario_advice_prompt,
)
from services.config_service import get_label_boundaries, get_woning_schema


def test_system_instruction_baseline_enforces_json_only():
    text = SYSTEM_INSTRUCTION_BASELINE.lower()
    assert "json" in text
    assert "geen markdown" in text


def test_methodology_source_guidance_contains_core_sources():
    text = METHODOLOGY_SOURCE_GUIDANCE
    assert "NTA 8800" in text
    assert "ISSO 82.1" in text


def test_extract_prompt_contains_schema_and_extractie_meta_rules():
    prompt = build_extract_report_prompt(get_woning_schema()).lower()
    assert "woningmodel" in prompt
    assert "schema" in prompt
    assert "probeer alle woningmodel-velden te vullen" in prompt
    assert "belangrijke mapping-focus" in prompt
    assert "prioriteit 1: bronrapport" in prompt
    assert "ep2 is de huidige energieprestatie-indicator" in prompt
    assert "als prestatie.current_label ontbreekt maar ep2 wel beschikbaar is" in prompt
    assert "assumptions" in prompt
    assert "uncertainties" in prompt
    assert "missing_fields" in prompt
    assert "null" in prompt


def test_extract_prompt_includes_extraction_context_when_provided():
    prompt = build_extract_report_prompt(
        get_woning_schema(),
        {"source_type": "epa_project_xml", "project_xml_candidates": [{"xml_path": "project/bouwjaar", "value": "1995"}]},
    ).lower()
    assert "epa_project_xml" in prompt
    assert "project/bouwjaar" in prompt


def test_extract_prompt_includes_label_boundaries_when_provided():
    prompt = build_extract_report_prompt(get_woning_schema(), label_boundaries=get_label_boundaries())
    assert "Deterministische labelmapping" in prompt
    assert "\"label\": \"B\"" in prompt
    assert "\"ep2_min_inclusive\": 160.0" in prompt


def test_scenario_advice_prompt_contains_trias_and_output_contract():
    prompt = build_scenario_advice_prompt().lower()
    assert "scenarioadvice" in prompt
    assert "selected_measures" in prompt
    assert "trias" in prompt
    assert "alleen json" in prompt
    assert TRIAS_ENERGETICA_INSTRUCTIE.strip().splitlines()[0].lower() in prompt
