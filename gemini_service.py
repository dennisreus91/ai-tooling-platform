from __future__ import annotations

import json
import mimetypes
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import requests
from google import genai
from google.genai import types

from prompts import (
    SYSTEM_INSTRUCTION_BASELINE,
    build_extract_report_prompt,
    build_measure_gap_prompt,
    build_scenario_advice_prompt,
)
from schemas import Constraints, MeasureOverview, MeasureStatus, ScenarioAdvice, WoningModel
from services.config_service import (
    get_label_boundaries,
    get_scenario_templates,
    get_trias_structure,
    get_vabi_mapping,
    get_woning_schema,
)
from services.config_service import get_measures_library
from services.extraction_service import extract_woningmodel_from_payload

DEFAULT_TIMEOUT_SECONDS = 60
MAX_EPA_XML_FILE_SIZE_BYTES = 15 * 1024 * 1024
MAX_EPA_XML_CANDIDATES = 20
MAX_EPA_XML_CONTEXT_ROWS = 120
PREFERRED_EPA_XML_BASENAMES = {"project.xml", "project"}
MEASURE_LIBRARY_FIELDS = (
    "id",
    "canonical_name",
    "aliases",
    "category",
    "trias_step",
    "isso_reference",
    "nta_domain",
    "calculation_priority",
    "target_metric",
    "target_value",
    "target_value_note",
    "unit_for_quantity",
    "investment_per_unit_eur",
    "investment_bandwidth_eur",
    "impact_path",
    "match_fields",
    "dependencies",
    "mutual_exclusions",
    "comparison_mode",
    "notes",
    "label_relevant",
    "scenario_allowed",
    "status_output_types",
)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=_get_required_env("GEMINI_API_KEY"))


def _get_extract_model() -> str:
    return os.getenv("GEMINI_EXTRACTION_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def _get_scenario_model() -> str:
    return os.getenv("GEMINI_SCENARIO_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def _guess_mime_type(file_path: str) -> str | None:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def _is_safe_zip_member(filename: str) -> bool:
    path = Path(filename)
    if path.is_absolute():
        return False
    return ".." not in path.parts


def _looks_like_well_formed_xml(content: bytes) -> bool:
    try:
        ET.fromstring(content)
        return True
    except ET.ParseError:
        return False


def _extract_xml_from_epa(local_path: str) -> str:
    try:
        archive = zipfile.ZipFile(local_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("epa_zip_invalid: .epa bestand is geen geldig ZIP-archief.") from exc

    with archive:
        xml_candidates: list[zipfile.ZipInfo] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            if not _is_safe_zip_member(info.filename):
                continue
            if not info.filename.lower().endswith(".xml"):
                continue
            xml_candidates.append(info)

        if not xml_candidates:
            raise ValueError("epa_xml_missing: geen XML-bestand gevonden in .epa archief.")

        ranked_candidates = sorted(
            xml_candidates,
            key=lambda item: (
                -int(Path(item.filename).name.lower() in PREFERRED_EPA_XML_BASENAMES),
                -int(item.file_size),
                item.filename.lower(),
            ),
        )[:MAX_EPA_XML_CANDIDATES]

        for candidate in ranked_candidates:
            if candidate.file_size > MAX_EPA_XML_FILE_SIZE_BYTES:
                continue
            try:
                content = archive.read(candidate)
            except Exception:
                continue
            if not content.strip():
                continue
            if not _looks_like_well_formed_xml(content):
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as temp_xml:
                temp_xml.write(content)
                return temp_xml.name

    raise ValueError("epa_xml_invalid: geen valide XML-bestand gevonden in .epa archief.")


def _normalize_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _flatten_xml_leaf_values(xml_path: str) -> list[dict[str, str]]:
    root = ET.parse(xml_path).getroot()
    rows: list[dict[str, str]] = []

    def walk(node: ET.Element, current_path: str) -> None:
        new_path = f"{current_path}/{node.tag.split('}')[-1]}" if current_path else node.tag.split("}")[-1]
        children = list(node)
        if not children:
            value = (node.text or "").strip()
            if value:
                rows.append(
                    {
                        "xml_path": new_path,
                        "leaf_tag": node.tag.split("}")[-1],
                        "value": value,
                    }
                )
            return
        for child in children:
            if len(rows) >= MAX_EPA_XML_CONTEXT_ROWS:
                return
            walk(child, new_path)

    walk(root, "")
    return rows[:MAX_EPA_XML_CONTEXT_ROWS]


def _build_epa_project_context(xml_path: str) -> dict[str, Any]:
    leaf_rows = _flatten_xml_leaf_values(xml_path)
    if not leaf_rows:
        return {}

    mapping = get_vabi_mapping()
    rules = mapping.get("rules", [])

    mapping_candidates: list[dict[str, Any]] = []
    for row in leaf_rows:
        normalized_leaf = _normalize_term(row["leaf_tag"])
        normalized_path = _normalize_term(row["xml_path"])
        matched_targets: list[str] = []
        for rule in rules:
            target_field = str(rule.get("target_field", "")).strip()
            if not target_field:
                continue
            possible_labels = [str(label) for label in rule.get("possible_labels", []) if label]
            for label in possible_labels:
                normalized_label = _normalize_term(label)
                if not normalized_label:
                    continue
                if normalized_label in normalized_leaf or normalized_label in normalized_path:
                    matched_targets.append(target_field)
                    break
        mapping_candidates.append(
            {
                "xml_path": row["xml_path"],
                "value": row["value"],
                "candidate_target_fields": sorted(set(matched_targets)),
            }
        )

    return {
        "source_type": "epa_project_xml",
        "mapping_strategy": "semantic_label_matching_via_vabi_mapping",
        "project_xml_candidates": mapping_candidates,
    }


def build_extraction_context(local_path: str) -> dict[str, Any]:
    suffix = Path(local_path).suffix.lower()
    if suffix != ".epa":
        return {}

    project_xml_path = _extract_xml_from_epa(local_path)
    try:
        return _build_epa_project_context(project_xml_path)
    finally:
        try:
            Path(project_xml_path).unlink(missing_ok=True)
        except Exception:
            pass


def _prepare_file_for_upload(local_path: str) -> tuple[str, str | None, list[str]]:
    cleanup_paths: list[str] = []
    suffix = Path(local_path).suffix.lower()

    if suffix == ".epa":
        extracted_xml_path = _extract_xml_from_epa(local_path)
        cleanup_paths.append(extracted_xml_path)
        return extracted_xml_path, "text/xml", cleanup_paths

    if suffix == ".xml":
        return local_path, "text/xml", cleanup_paths

    return local_path, _guess_mime_type(local_path), cleanup_paths


def download_file_to_temp(file_url: str) -> str:
    response = requests.get(file_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()

    suffix = Path(file_url).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(response.content)
        return temp_file.name


def upload_case_file(local_path: str) -> Any:
    client = _get_gemini_client()
    prepared_path, mime_type, cleanup_paths = _prepare_file_for_upload(local_path)

    try:
        if mime_type:
            return client.files.upload(file=prepared_path, config={"mime_type": mime_type})
        return client.files.upload(file=prepared_path)
    finally:
        for path in cleanup_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                continue


def _parse_llm_json(raw_text: str, context: str) -> Any:
    decoder = json.JSONDecoder()

    def decode_start(text: str) -> Any | None:
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
                return value
            except json.JSONDecodeError:
                continue
        return None

    stripped = raw_text.strip()
    parsed = decode_start(stripped)
    if parsed is not None:
        return parsed

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    for block in fenced_blocks:
        parsed = decode_start(block.strip())
        if parsed is not None:
            return parsed

    raise RuntimeError(f"invalid_llm_json: {context} did not return valid JSON.")


def _generate_json(*, model: str, contents: list[Any], context_name: str, tools: list[Any] | None = None) -> Any:
    client = _get_gemini_client()
    config: dict[str, Any] = {"system_instruction": SYSTEM_INSTRUCTION_BASELINE}
    if tools:
        config["tools"] = tools
    response = client.models.generate_content(model=model, contents=contents, config=config)

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError(f"{context_name} returned an empty response.")

    return _parse_llm_json(raw_text, context_name)


def extract_woningmodel_data(uploaded_file: Any, extraction_context: dict[str, Any] | None = None) -> WoningModel:
    payload = _generate_json(
        model=_get_extract_model(),
        contents=[uploaded_file, build_extract_report_prompt(get_woning_schema(), extraction_context)],
        context_name="Gemini woningmodel extraction",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_llm_json: Gemini woningmodel extraction payload should be an object.")
    return extract_woningmodel_from_payload(payload)


def _normalize_measure_gap_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    normalized = dict(raw)
    for key in ("measure_id", "canonical_name", "status", "reason"):
        if normalized.get(key) is None:
            normalized[key] = ""

    status = str(normalized.get("status", "")).strip().lower()
    if status not in {"missing", "improvable", "sufficient", "not_applicable", "capacity_limited"}:
        status = "missing"
    normalized["status"] = status

    if not isinstance(normalized.get("evidence_fields"), list):
        normalized["evidence_fields"] = []
    if not isinstance(normalized.get("current_values_snapshot"), dict):
        normalized["current_values_snapshot"] = {}
    if not isinstance(normalized.get("assumptions"), list):
        normalized["assumptions"] = []
    if not isinstance(normalized.get("uncertainties"), list):
        normalized["uncertainties"] = []

    gap_delta = normalized.get("gap_delta")
    if gap_delta is not None:
        try:
            normalized["gap_delta"] = float(gap_delta)
        except (TypeError, ValueError):
            normalized["gap_delta"] = None

    return normalized


def _normalize_measure_gap_payload(raw: dict[str, Any]) -> dict[str, Any]:
    missing_raw = raw.get("missing")
    improvable_raw = raw.get("improvable")
    combined_raw = raw.get("combined")

    def _normalize_collection(values: Any) -> list[dict[str, Any]]:
        if not isinstance(values, list):
            return []
        result: list[dict[str, Any]] = []
        for item in values:
            normalized_item = _normalize_measure_gap_item(item)
            if normalized_item is not None:
                result.append(normalized_item)
        return result

    missing = _normalize_collection(missing_raw)
    improvable = _normalize_collection(improvable_raw)
    combined = _normalize_collection(combined_raw)

    if not combined:
        combined = [*missing, *improvable]

    return {
        "missing": missing,
        "improvable": improvable,
        "combined": combined,
    }


def _enrich_measure_gap_payload_with_library(raw: dict[str, Any]) -> dict[str, Any]:
    library = get_measures_library().get("measures", [])
    measure_index: dict[str, dict[str, Any]] = {}
    for measure in library:
        if not isinstance(measure, dict):
            continue
        key = str(measure.get("id", "")).strip()
        if key:
            measure_index[key] = measure

    def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        key = str(result.get("measure_id", "")).strip()
        measure = measure_index.get(key)
        if not measure:
            return result

        # Altijd canonical_name/id vanuit bibliotheek als bron van waarheid.
        result["id"] = measure.get("id")
        result["canonical_name"] = str(measure.get("canonical_name") or result.get("canonical_name") or "").strip()

        for field in MEASURE_LIBRARY_FIELDS:
            if field in {"id", "canonical_name"}:
                continue
            result[field] = measure.get(field)
        return result

    return {
        "missing": [_enrich_item(item) for item in raw.get("missing", []) if isinstance(item, dict)],
        "improvable": [_enrich_item(item) for item in raw.get("improvable", []) if isinstance(item, dict)],
        "combined": [_enrich_item(item) for item in raw.get("combined", []) if isinstance(item, dict)],
    }


def _resolve_measure_overview_quantities(raw: dict[str, Any], woningmodel: WoningModel) -> dict[str, Any]:
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace(",", ".").strip()
            return float(value)
        except (TypeError, ValueError):
            return None

    def _text(value: Any) -> str:
        return str(value or "").strip().casefold()

    measure_candidates = [m.model_dump() for m in woningmodel.maatregelen]

    def _match_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
        labels = {
            _text(item.get("measure_id")),
            _text(item.get("id")),
            _text(item.get("canonical_name")),
        }
        for alias in item.get("aliases") or []:
            labels.add(_text(alias))

        labels = {label for label in labels if label}
        if not labels:
            return None

        for candidate in measure_candidates:
            original_name = _text(candidate.get("maatregel_naam_origineel"))
            if not original_name:
                continue
            if original_name in labels:
                return candidate
            if any(label in original_name or original_name in label for label in labels):
                return candidate
        return None

    def _resolve_from_target_metric(item: dict[str, Any]) -> tuple[float | None, str | None]:
        target_metric = str(item.get("target_metric") or "").strip()
        mapping = {
            "bouwdelen.dak.": "bouwdelen.dak.oppervlakte_m2",
            "bouwdelen.gevel.": "bouwdelen.gevel.oppervlakte_m2",
            "bouwdelen.vloer.": "bouwdelen.vloer.oppervlakte_m2",
            "bouwdelen.ramen.": "bouwdelen.ramen.oppervlakte_m2",
        }
        woning = woningmodel.model_dump()

        def _get_nested(container: dict[str, Any], path: str) -> Any:
            current: Any = container
            for part in path.split("."):
                if not isinstance(current, dict):
                    return None
                current = current.get(part)
            return current

        for prefix, source_field in mapping.items():
            if not target_metric.startswith(prefix):
                continue
            value = _safe_float(_get_nested(woning, source_field))
            if value is not None:
                return value, source_field
        return None, None

    def _resolve_item(item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        quantity_value = None
        quantity_unit = None
        quantity_source_field = None
        quantity_confidence = 0.0

        candidate = _match_candidate(result)
        if candidate:
            quantity_value = _safe_float(candidate.get("quantity_value"))
            quantity_unit = candidate.get("quantity_unit")
            quantity_source_field = candidate.get("quantity_source_field")
            quantity_confidence = _safe_float(candidate.get("quantity_confidence")) or 0.0

        if quantity_value is None:
            derived_value, derived_source = _resolve_from_target_metric(result)
            if derived_value is not None:
                quantity_value = derived_value
                quantity_source_field = derived_source
                quantity_confidence = max(quantity_confidence, 0.6)
                if not quantity_unit:
                    quantity_unit = result.get("unit_for_quantity")

        if quantity_value is None and str(result.get("unit_for_quantity") or "").strip() == "woning":
            quantity_value = 1.0
            quantity_unit = "woning"
            quantity_source_field = "constant:woning"
            quantity_confidence = max(quantity_confidence, 1.0)

        result["resolved_quantity_value"] = quantity_value
        result["resolved_quantity_unit"] = quantity_unit
        result["resolved_quantity_source_field"] = quantity_source_field
        result["resolved_quantity_confidence"] = max(0.0, min(1.0, float(quantity_confidence or 0.0)))
        return result

    return {
        "missing": [_resolve_item(item) for item in raw.get("missing", []) if isinstance(item, dict)],
        "improvable": [_resolve_item(item) for item in raw.get("improvable", []) if isinstance(item, dict)],
        "combined": [_resolve_item(item) for item in raw.get("combined", []) if isinstance(item, dict)],
    }


def get_measure_gap_analysis_with_gemini(
    *,
    woningmodel: WoningModel,
    file_search_store: str | None = None,
) -> tuple[list[MeasureStatus], MeasureOverview]:
    input_payload = {
        "woningmodel": woningmodel.model_dump(),
        "relevante_woninginformatie": {
            "woning": woningmodel.woning.model_dump(),
            "prestatie": woningmodel.prestatie.model_dump(),
            "bouwdelen": woningmodel.bouwdelen.model_dump(),
            "installaties": woningmodel.installaties.model_dump(),
            "huidige_maatregelen_samenvatting": woningmodel.samenvatting_huidige_maatregelen,
            "huidige_maatregelen_gestructureerd": [m.model_dump() for m in woningmodel.maatregelen],
        },
        "maatregelenbibliotheek": get_measures_library().get("measures", []),
    }

    tools = None
    if file_search_store:
        tools = [
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[file_search_store]
                )
            )
        ]
        input_payload["file_search_store"] = file_search_store

    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(input_payload, ensure_ascii=False), build_measure_gap_prompt()],
        context_name="Gemini measure gap analysis",
        tools=tools,
    )

    if not isinstance(raw, dict):
        raise RuntimeError("invalid_llm_json: Measure gap analysis response should be an object.")

    normalized = _normalize_measure_gap_payload(raw)
    enriched = _enrich_measure_gap_payload_with_library(normalized)
    resolved = _resolve_measure_overview_quantities(enriched, woningmodel)
    overview = MeasureOverview.model_validate(resolved)
    statuses = [*overview.missing, *overview.improvable]
    return statuses, overview




def _normalize_scenario_advice_payload(raw: dict[str, Any], measure_overview: MeasureOverview | None = None) -> dict[str, Any]:
    allowed_fields = {
        "scenario_id",
        "scenario_name",
        "expected_label",
        "expected_ep2_kwh_m2",
        "selected_measures",
        "logical_order",
        "total_investment_eur",
        "monthly_savings_eur",
        "expected_gasverbruik_m3",
        "expected_elektriciteitsverbruik_kwh",
        "expected_property_value_gain_eur",
        "motivation",
        "assumptions",
        "uncertainties",
        "methodiek_bronnen",
    }
    normalized = {key: value for key, value in raw.items() if key in allowed_fields}

    def _normalize_measures(values: Any) -> list[str]:
        result: list[str] = []
        if not isinstance(values, list):
            return result
        for item in values:
            if isinstance(item, str):
                v = item.strip()
                if v:
                    result.append(v)
                continue
            if isinstance(item, dict):
                for key in ("measure_id", "id", "name", "canonical_name"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        result.append(value.strip())
                        break
        return result

    if "selected_measures" in normalized:
        normalized["selected_measures"] = _normalize_measures(normalized.get("selected_measures"))
    if "logical_order" in normalized:
        normalized["logical_order"] = _normalize_measures(normalized.get("logical_order"))

    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace(",", ".").strip()
            return float(value)
        except (TypeError, ValueError):
            return None

    def _estimate_measure_investment(measure: dict[str, Any]) -> float:
        per_unit = _safe_float(measure.get("investment_per_unit_eur"))
        if per_unit is not None and per_unit > 0:
            return round(per_unit, 2)

        bandwidth = measure.get("investment_bandwidth_eur", {})
        low = _safe_float(bandwidth.get("min"))
        high = _safe_float(bandwidth.get("max"))
        if low is not None and high is not None and low > 0 and high > 0:
            return round((low + high) / 2.0, 2)

        return 0.0

    selected_measures = normalized.get("selected_measures") or []
    provided_total = _safe_float(normalized.get("total_investment_eur"))
    if isinstance(selected_measures, list) and selected_measures and (provided_total is None or provided_total <= 0.0):
        if measure_overview is not None:
            overview_items = measure_overview.combined or [*measure_overview.missing, *measure_overview.improvable]
            overview_index = {
                str(item.measure_id or item.id or "").strip(): item
                for item in overview_items
                if str(item.measure_id or item.id or "").strip()
            }
            quantity_total = 0.0
            quantity_assumptions: list[str] = []
            quantity_uncertainties: list[str] = []

            for measure_id in selected_measures:
                item = overview_index.get(str(measure_id).strip())
                if not item:
                    quantity_uncertainties.append(
                        f"Maatregel '{measure_id}' ontbreekt in measure_overview; quantity-gedreven investering niet toepasbaar."
                    )
                    continue
                unit_price = _safe_float(item.investment_per_unit_eur)
                quantity_value = _safe_float(item.resolved_quantity_value)
                unit_for_quantity = str(item.unit_for_quantity or "").strip()
                if quantity_value is None and unit_for_quantity == "woning":
                    quantity_value = 1.0
                if unit_price is None or unit_price <= 0.0:
                    quantity_uncertainties.append(
                        f"Maatregel '{measure_id}' heeft geen bruikbare investment_per_unit_eur; library fallback nodig."
                    )
                    continue
                if quantity_value is None or quantity_value <= 0.0:
                    quantity_uncertainties.append(
                        f"Maatregel '{measure_id}' heeft geen bruikbare resolved_quantity_value; library fallback nodig."
                    )
                    continue
                quantity_total += unit_price * quantity_value
                quantity_assumptions.append(
                    f"{measure_id}: total_investment component = investment_per_unit_eur * resolved_quantity_value."
                )

            if quantity_total > 0.0:
                normalized["total_investment_eur"] = round(quantity_total, 2)
                assumptions = normalized.get("assumptions")
                if not isinstance(assumptions, list):
                    assumptions = []
                assumptions.append(
                    "total_investment_eur is deterministisch afgeleid uit measure_overview (resolved quantities * investment_per_unit_eur)."
                )
                assumptions.extend(quantity_assumptions)
                normalized["assumptions"] = assumptions

                uncertainties = normalized.get("uncertainties")
                if not isinstance(uncertainties, list):
                    uncertainties = []
                uncertainties.extend(quantity_uncertainties)
                normalized["uncertainties"] = uncertainties
                provided_total = normalized["total_investment_eur"]

    if isinstance(selected_measures, list) and selected_measures and (provided_total is None or provided_total <= 0.0):
        library = get_measures_library().get("measures", [])
        measure_index = {
            str(measure.get("id", "")).strip(): measure
            for measure in library
            if isinstance(measure, dict) and str(measure.get("id", "")).strip()
        }

        fallback_total = 0.0
        fallback_uncertainties: list[str] = []
        for measure_id in selected_measures:
            measure = measure_index.get(str(measure_id).strip())
            if not measure:
                fallback_uncertainties.append(
                    f"Maatregel '{measure_id}' ontbreekt in maatregelenbibliotheek; investering niet meegerekend."
                )
                continue
            estimated = _estimate_measure_investment(measure)
            fallback_total += estimated
            if estimated == 0.0:
                fallback_uncertainties.append(
                    f"Maatregel '{measure_id}' heeft geen bruikbare investment_per_unit_eur/investment_bandwidth_eur in de bibliotheek."
                )

        normalized["total_investment_eur"] = round(fallback_total, 2)

        assumptions = normalized.get("assumptions")
        if not isinstance(assumptions, list):
            assumptions = []
        assumptions.append(
            "total_investment_eur is deterministisch afgeleid uit maatregelenbibliotheek (POC-fallback) omdat Gemini geen bruikbare investeringswaarde gaf."
        )
        normalized["assumptions"] = assumptions

        uncertainties = normalized.get("uncertainties")
        if not isinstance(uncertainties, list):
            uncertainties = []
        uncertainties.extend(fallback_uncertainties)
        normalized["uncertainties"] = uncertainties

    for key in (
        "total_investment_eur",
        "monthly_savings_eur",
        "expected_property_value_gain_eur",
        "expected_gasverbruik_m3",
        "expected_elektriciteitsverbruik_kwh",
    ):
        value = normalized.get(key)
        if key in {"expected_gasverbruik_m3", "expected_elektriciteitsverbruik_kwh"}:
            normalized[key] = _safe_float(value)
            continue
        if value is None:
            normalized[key] = 0.0

    if normalized.get("expected_ep2_kwh_m2") is None:
        label = normalized.get("expected_label")
        boundaries = get_label_boundaries().get("boundaries", [])
        normalized_label = str(label or "").strip().upper()
        fallback_ep2 = None
        for rule in boundaries:
            if str(rule.get("label", "")).upper() != normalized_label:
                continue
            min_v = rule.get("ep2_min_inclusive")
            max_v = rule.get("ep2_max_exclusive")
            if min_v is not None and max_v is not None:
                fallback_ep2 = float(min_v + (max_v - min_v) / 2.0)
            elif min_v is not None:
                fallback_ep2 = float(min_v + 10.0)
            elif max_v is not None:
                fallback_ep2 = max(float(max_v) - 10.0, 0.0)
            break
        normalized["expected_ep2_kwh_m2"] = fallback_ep2 if fallback_ep2 is not None else 0.0

    if not isinstance(normalized.get("motivation"), str) or not normalized["motivation"].strip():
        normalized["motivation"] = "Gemini-output bevatte geen geldige motivatie; fallback toegepast."

    return normalized


def get_scenario_advice_with_gemini(
    *,
    constraints: Constraints,
    woningmodel: WoningModel,
    measure_overview: MeasureOverview,
    file_search_store: str | None = None,
) -> ScenarioAdvice:
    input_payload = {
        "constraints": constraints.model_dump(),
        "woningmodel": woningmodel.model_dump(),
        "measure_overview": measure_overview.model_dump(),
        "relevante_woninginformatie": {
            "woning": woningmodel.woning.model_dump(),
            "prestatie": woningmodel.prestatie.model_dump(),
            "bouwdelen": woningmodel.bouwdelen.model_dump(),
            "installaties": woningmodel.installaties.model_dump(),
        },
        "scenario_templates": get_scenario_templates().get("templates", []),
        "trias_structuur": get_trias_structure(),
    }

    tools = None
    if file_search_store:
        tools = [
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[file_search_store]
                )
            )
        ]
        input_payload["file_search_store"] = file_search_store

    raw = _generate_json(
        model=_get_scenario_model(),
        contents=[json.dumps(input_payload, ensure_ascii=False), build_scenario_advice_prompt()],
        context_name="Gemini scenario advice",
        tools=tools,
    )

    if not isinstance(raw, dict):
        raise RuntimeError("invalid_llm_json: Scenario advice response should be an object.")

    return ScenarioAdvice.model_validate(_normalize_scenario_advice_payload(raw, measure_overview))
