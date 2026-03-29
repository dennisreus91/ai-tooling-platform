from gemini_service import _parse_llm_json


def test_parse_llm_json_extracts_fenced_block():
    raw = "tekst ```json\n{\"ok\": true}\n``` eind"
    assert _parse_llm_json(raw, "ctx") == {"ok": True}
