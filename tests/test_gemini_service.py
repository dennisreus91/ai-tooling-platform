import pytest

from gemini_service import _parse_llm_json


def test_parse_llm_json_extracts_fenced_block():
    raw = "tekst ```json\n{\"ok\": true}\n``` eind"
    assert _parse_llm_json(raw, "ctx") == {"ok": True}


def test_parse_llm_json_extracts_plain_json():
    raw = '{"value": 123}'
    assert _parse_llm_json(raw, "ctx") == {"value": 123}


def test_parse_llm_json_extracts_json_with_prefix_text():
    raw = "Dit is uitleg {\"a\": 1}"
    assert _parse_llm_json(raw, "ctx") == {"a": 1}


def test_parse_llm_json_extracts_json_with_suffix_text():
    raw = "{\"b\": 2} extra tekst"
    assert _parse_llm_json(raw, "ctx") == {"b": 2}


def test_parse_llm_json_extracts_array_json():
    raw = "[{\"x\": 1}, {\"x\": 2}]"
    assert _parse_llm_json(raw, "ctx") == [{"x": 1}, {"x": 2}]


def test_parse_llm_json_uses_first_valid_json_block():
    raw = """
    tekst
    ```json
    {"a": 1}
    ```
    andere tekst
    ```json
    {"b": 2}
    ```
    """
    assert _parse_llm_json(raw, "ctx") == {"a": 1}


def test_parse_llm_json_handles_non_json_fenced_block():
    raw = "```text\nhello\n``` {\"valid\": true}"
    assert _parse_llm_json(raw, "ctx") == {"valid": True}


def test_parse_llm_json_raises_on_invalid_json():
    raw = "geen json hier"
    with pytest.raises(RuntimeError) as exc:
        _parse_llm_json(raw, "ctx")

    assert "invalid_llm_json" in str(exc.value)
