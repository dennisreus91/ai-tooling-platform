import pytest

from gemini_service import _normalize_measure_gap_payload, _normalize_scenario_advice_payload, _parse_llm_json


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


def test_normalize_scenario_advice_payload_derives_ep2_when_missing():
    normalized = _normalize_scenario_advice_payload(
        {
            "scenario_id": "S1",
            "scenario_name": "test",
            "expected_label": "B",
            "expected_ep2_kwh_m2": None,
            "motivation": "test",
        }
    )

    assert isinstance(normalized["expected_ep2_kwh_m2"], float)
    assert normalized["expected_ep2_kwh_m2"] > 0


def test_normalize_scenario_advice_payload_drops_unknown_fields():
    normalized = _normalize_scenario_advice_payload(
        {
            "scenario_id": "S1",
            "scenario_name": "test",
            "expected_label": "B",
            "expected_ep2_kwh_m2": 120,
            "motivation": "ok",
            "label_range": {"min_ep2": 51, "max_ep2": 100},
            "target_label_achieved": True,
        }
    )

    assert "label_range" not in normalized
    assert "target_label_achieved" not in normalized


def test_normalize_measure_gap_payload_builds_combined_when_missing():
    normalized = _normalize_measure_gap_payload(
        {
            "missing": [
                {
                    "measure_id": "dakisolatie",
                    "canonical_name": "Dakisolatie",
                    "status": "missing",
                    "reason": "Ontbreekt",
                }
            ],
            "improvable": [
                {
                    "measure_id": "gevelisolatie",
                    "canonical_name": "Gevelisolatie",
                    "status": "improvable",
                    "reason": "Niet op doelwaarde",
                }
            ],
        }
    )

    assert len(normalized["combined"]) == 2
    assert normalized["combined"][0]["measure_id"] == "dakisolatie"


def test_normalize_measure_gap_payload_normalizes_invalid_fields():
    normalized = _normalize_measure_gap_payload(
        {
            "missing": [
                {
                    "measure_id": "x",
                    "canonical_name": "X",
                    "status": "UNKNOWN",
                    "reason": "x",
                    "evidence_fields": "not-a-list",
                    "current_values_snapshot": [],
                    "assumptions": "a",
                    "uncertainties": "u",
                    "gap_delta": "abc",
                }
            ],
            "improvable": [],
            "combined": [],
        }
    )

    item = normalized["missing"][0]
    assert item["status"] == "missing"
    assert item["evidence_fields"] == []
    assert item["current_values_snapshot"] == {}
    assert item["assumptions"] == []
    assert item["uncertainties"] == []
    assert item["gap_delta"] is None


def test_normalize_scenario_advice_payload_estimates_total_investment_from_library_when_missing():
    normalized = _normalize_scenario_advice_payload(
        {
            "scenario_id": "S1",
            "scenario_name": "test",
            "expected_label": "B",
            "expected_ep2_kwh_m2": 120,
            "selected_measures": ["dakisolatie", "gevelisolatie"],
            "total_investment_eur": None,
            "motivation": "ok",
        }
    )

    assert normalized["total_investment_eur"] > 0
    assert any("deterministisch afgeleid uit maatregelenbibliotheek" in msg for msg in normalized["assumptions"])


def test_normalize_scenario_advice_payload_keeps_positive_total_investment_from_gemini():
    normalized = _normalize_scenario_advice_payload(
        {
            "scenario_id": "S1",
            "scenario_name": "test",
            "expected_label": "B",
            "expected_ep2_kwh_m2": 120,
            "selected_measures": ["dakisolatie"],
            "total_investment_eur": 12345,
            "motivation": "ok",
        }
    )

    assert normalized["total_investment_eur"] == 12345
