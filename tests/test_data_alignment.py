import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


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

    assert not missing_in_schema, (
        f"Metricen ontbreken in woningmodel_schema: {sorted(set(missing_in_schema))}"
    )
    assert not missing_in_mapping, (
        f"Metricen ontbreken in vabi_mapping: {sorted(set(missing_in_mapping))}"
    )


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
        assert isinstance(measure.get("label_relevant"), bool)
        assert isinstance(measure.get("scenario_allowed"), bool)
        assert isinstance(measure.get("status_output_types"), list)
        assert measure.get("trias_step") in {1, 2, 3}


def test_mapping_supports_measure_comparison_and_capacity_checks():
    mapping = _load("data/vabi_mapping.json")
    library = _load("data/maatregelenbibliotheek.json")

    mapped_paths = {rule["target_field"] for rule in mapping["rules"]}
    required_for_by_target = {
        rule["target_field"]: set(rule.get("required_for", []))
        for rule in mapping["rules"]
    }

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


def test_measure_relation_ids_match_measure_library():
    library = _load("data/maatregelenbibliotheek.json")
    relations = _load("data/maatregel_relations.json")

    measure_ids = {m["id"] for m in library["measures"]}

    unknown_ids = set()

    for rule in relations.get("dependency_rules", []):
        measure_id = rule.get("measure_id")
        if measure_id and measure_id not in measure_ids:
            unknown_ids.add(measure_id)

        for dep in rule.get("requires", []):
            if dep not in measure_ids:
                unknown_ids.add(dep)

        for group in rule.get("requires_any_of", []):
            if isinstance(group, list):
                for dep in group:
                    if dep not in measure_ids:
                        unknown_ids.add(dep)

    for rule in relations.get("mutual_exclusion_rules", []):
        for mid in rule.get("measures", []):
            if mid not in measure_ids:
                unknown_ids.add(mid)

    for rule in relations.get("ordering_rules", []):
        before = rule.get("before")
        after = rule.get("after")
        if before and before not in measure_ids:
            unknown_ids.add(before)
        if after and after not in measure_ids:
            unknown_ids.add(after)

    for rule in relations.get("capacity_rules", []):
        measure_id = rule.get("measure_id")
        if measure_id and measure_id not in measure_ids:
            unknown_ids.add(measure_id)

    for rule in relations.get("selection_hints", []):
        measure_id = rule.get("measure_id")
        if measure_id and measure_id not in measure_ids:
            unknown_ids.add(measure_id)

    assert not unknown_ids, f"Maatregel-ids in maatregel_relations.json ontbreken in maatregelenbibliotheek.json: {sorted(unknown_ids)}"


def test_required_scenario_templates_exist():
    templates = _load("data/scenario_templates.json")["templates"]
    template_ids = {t["id"] for t in templates}

    required = {
        "MIN_LABELSPRONG",
        "GOEDKOOPSTE_DOELLABEL",
        "GEBALANCEERD",
        "SCHIL_EERST",
    }

    assert required.issubset(template_ids), (
        f"Ontbrekende verplichte scenario templates: {sorted(required - template_ids)}"
    )


def test_trias_categories_cover_measure_library_categories():
    library = _load("data/maatregelenbibliotheek.json")
    trias = _load("data/trias_structuur.json")

    measure_categories = {m["category"] for m in library["measures"]}
    trias_categories = set()

    for step in trias.get("steps", []):
        trias_categories.update(step.get("categories", []))

    missing_categories = measure_categories - trias_categories
    assert not missing_categories, (
        f"Maatregelcategorieën ontbreken in trias_structuur.json: {sorted(missing_categories)}"
    )


def test_label_boundaries_and_value_impact_cover_same_labels():
    labelgrenzen = _load("data/labelgrenzen.json")
    value_impact = _load("data/woningwaarde_label_impact.json")

    labels_from_boundaries = {entry["label"] for entry in labelgrenzen["boundaries"]}
    labels_from_multipliers = set(value_impact["label_multipliers"].keys())

    assert labels_from_boundaries == labels_from_multipliers, (
        "Labels in labelgrenzen.json en woningwaarde_label_impact.json komen niet overeen."
    )


def test_label_boundaries_are_monotonic_and_complete():
    labelgrenzen = _load("data/labelgrenzen.json")
    boundaries = labelgrenzen["boundaries"]

    assert boundaries, "labelgrenzen.json bevat geen boundaries."

    previous_max = None
    for boundary in boundaries:
        min_val = boundary.get("ep2_min_inclusive")
        max_val = boundary.get("ep2_max_exclusive")

        if previous_max is not None and min_val is not None:
            assert float(min_val) == float(previous_max), (
                f"Boundary sluit niet aan op vorige grens bij label {boundary['label']}."
            )

        previous_max = max_val if max_val is not None else previous_max


def test_assumption_rules_reference_existing_schema_fields():
    schema = _load("data/woningmodel_schema.json")
    assumptions = _load("data/aannameregels.json")
    schema_paths = _collect_schema_leaf_paths(schema)

    missing_fields = []
    for rule in assumptions.get("rules", []):
        field = rule.get("field")
        if field and field not in schema_paths:
            missing_fields.append(field)

    assert not missing_fields, (
        f"Velden uit aannameregels.json ontbreken in woningmodel_schema.json: {sorted(set(missing_fields))}"
    )
