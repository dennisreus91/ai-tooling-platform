from prompts import (
    METHODOLOGY_SOURCE_GUIDANCE,
    build_extract_report_prompt,
    build_final_report_prompt,
    build_optimize_report_prompt,
)


def test_methodology_source_guidance_mentions_all_reference_documents():
    assert "NTA8800" in METHODOLOGY_SOURCE_GUIDANCE
    assert "ISSO 82.1" in METHODOLOGY_SOURCE_GUIDANCE
    assert "Energielabeltabel" in METHODOLOGY_SOURCE_GUIDANCE


def test_step_prompts_append_methodology_guidance():
    extract_prompt = build_extract_report_prompt()
    optimize_prompt = build_optimize_report_prompt()
    final_prompt = build_final_report_prompt()

    assert "Methodiekbronnen in file_search" in extract_prompt
    assert "Methodiekbronnen in file_search" in optimize_prompt
    assert "Methodiekbronnen in file_search" in final_prompt
