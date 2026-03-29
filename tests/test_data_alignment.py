import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text())


def _collect_schema_leaf_paths(node: dict, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    properties = node.get("properties", {}) if isinstance(node, dict) else {}

    for key, child in properties.items():
        current = f"{prefix}.{key}" if prefix else key
        child_props = child.get("properties", {}) if isinstance(child, dict) else {}
        if child_props:
            paths.update(_collect_schema_leaf_paths(child, current))
        else:
            paths.add(current)
    return paths


def test_measure_metrics_are_defined_in_schema_and_mapping():
    schema = _load("data/woningmodel_schema.json")
    mapping = _load("data/vabi_mapping.json")
    library = _load("data/maatregelenbibliotheek.json")

    schema_paths = _collect_schema_leaf_paths(schema)
    mapped_paths = {rule["target_field"] for rule in mapping["rules"]}

    missing_in_schema = []
    missing_in_mapping = []
    for measure in library["measures"]:
        target_metric = measure["target_metric"]
        if target_metric not in schema_paths:
            missing_in_schema.append(target_metric)
        if target_metric not in mapped_paths:
            missing_in_mapping.append(target_metric)

        for field in measure.get("match_fields", []):
            if field not in schema_paths:
                missing_in_schema.append(field)
            if field not in mapped_paths:
                missing_in_mapping.append(field)

    assert not missing_in_schema, f"Metricen ontbreken in woningmodel_schema: {sorted(set(missing_in_schema))}"
    assert not missing_in_mapping, f"Metricen ontbreken in vabi_mapping: {sorted(set(missing_in_mapping))}"


def test_measure_library_contains_isso_and_nta_metadata():
    library = _load("data/maatregelenbibliotheek.json")
    allowed_nta_domains = {
        "transmissie",
        "infiltratie",
        "verwarming",
        "ventilatie",
        "opwek",
        "tapwater",
    }

    for measure in library["measures"]:
        assert measure.get("isso_reference") == "ISSO 82.1"
        assert measure.get("nta_domain") in allowed_nta_domains
        assert measure.get("comparison_mode") in {"equals", "min_gte", "max_lte"}


def test_mapping_supports_measure_comparison_and_capacity_checks():
    mapping = _load("data/vabi_mapping.json")
    library = _load("data/maatregelenbibliotheek.json")

    mapped_paths = {rule["target_field"] for rule in mapping["rules"]}
    required_for_by_target = {rule["target_field"]: set(rule.get("required_for", [])) for rule in mapping["rules"]}

    for measure in library["measures"]:
        metric = measure["target_metric"]
        assert metric in mapped_paths
        assert "measure_matching" in required_for_by_target.get(metric, set()) or metric in {
            "prestatie.current_ep2_kwh_m2",
            "prestatie.current_label",
        }

        capacity_logic = measure.get("capacity_logic")
        if capacity_logic:
            cap_field = capacity_logic["field"]
            assert cap_field in mapped_paths
            assert "capacity_checks" in required_for_by_target.get(cap_field, set())
