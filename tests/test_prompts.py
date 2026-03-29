from prompts import METHODOLOGY_SOURCE_GUIDANCE, build_extract_report_prompt, build_measure_impact_prompt


def test_prompt_contains_methodology_guidance():
    assert "NTA8800" in METHODOLOGY_SOURCE_GUIDANCE
    assert "ISSO 82.1" in METHODOLOGY_SOURCE_GUIDANCE


def test_measure_impact_prompt_builder():
    prompt = build_measure_impact_prompt()
    assert "JSON" in prompt or "json" in prompt
    assert "Methodiekbronnen" in prompt
    assert "impact" in prompt.lower()
    assert "NTA8800" in build_extract_report_prompt()
