from prompts import (
    METHODOLOGY_SOURCE_GUIDANCE,
    SYSTEM_INSTRUCTION_BASELINE,
    build_extract_report_prompt,
    build_final_report_prompt,
    build_measure_impact_prompt,
    build_optimize_report_prompt,
)


def test_system_instruction_baseline_enforces_json_only():
    text = SYSTEM_INSTRUCTION_BASELINE.lower()
    assert "json" in text
    assert "geen markdown" in text
    assert "geen toelichting buiten json" in text or "geen vrije tekst" in text


def test_methodology_source_guidance_contains_core_sources():
    text = METHODOLOGY_SOURCE_GUIDANCE
    assert "NTA 8800" in text
    assert "ISSO 82.1" in text
    assert "energielabel" in text.lower()


def test_extract_prompt_contains_required_extractie_meta_fields():
    prompt = build_extract_report_prompt().lower()
    assert "woningmodel" in prompt
    assert "assumptions" in prompt
    assert "uncertainties" in prompt
    assert "missing_fields" in prompt
    assert "confidence" in prompt
    assert "null" in prompt
    assert "alleen json" in prompt or "uitsluitend het woningmodel als json" in prompt


def test_measure_impact_prompt_builder_contains_json_and_scope():
    prompt = build_measure_impact_prompt().lower()
    assert "json" in prompt
    assert "measureimpact" in prompt or "impact" in prompt
    assert "missing" in prompt
    assert "improvable" in prompt
    assert "trias" in prompt


def test_optimize_prompt_builder_contains_trias_and_scenarios():
    prompt = build_optimize_report_prompt().lower()
    assert "scenario" in prompt
    assert "trias energetica" in prompt or "trias" in prompt
    assert "afhankelijkheden" in prompt or "conflicterende combinaties" in prompt
    assert "alleen json" in prompt


def test_final_report_prompt_builder_contains_required_report_fields():
    prompt = build_final_report_prompt().lower()
    assert "title" in prompt
    assert "summary" in prompt
    assert "current_label" in prompt
    assert "new_label" in prompt
    assert "new_ep2_kwh_m2" in prompt
    assert "monthly_savings_eur" in prompt
    assert "expected_property_value_gain_eur" in prompt
    assert "poc" in prompt
    assert "alleen json" in prompt
