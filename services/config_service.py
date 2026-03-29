import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class ConfigError(Exception):
    """Custom exception for configuration-related errors."""
    pass


@lru_cache(maxsize=32)
def load_json(path: Path) -> dict[str, Any]:
    """
    Load a JSON file with validation and clear error handling.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {path}: {e}") from e
    except Exception as e:
        raise ConfigError(f"Failed to read config {path}: {e}") from e


def _load(name: str) -> dict[str, Any]:
    """
    Load a config file from the central config directory.
    """
    path = BASE_CONFIG_DIR / name
    return load_json(path)


# --- Core configuration loaders --- #

@lru_cache(maxsize=None)
def get_measures_library() -> dict[str, Any]:
    return _load("maatregelenbibliotheek.json")


@lru_cache(maxsize=None)
def get_measure_relations() -> dict[str, Any]:
    return _load("maatregel_relations.json")


@lru_cache(maxsize=None)
def get_trias_structure() -> dict[str, Any]:
    return _load("trias_structuur.json")


@lru_cache(maxsize=None)
def get_scenario_templates() -> dict[str, Any]:
    return _load("scenario_templates.json")


@lru_cache(maxsize=None)
def get_label_boundaries() -> dict[str, Any]:
    return _load("labelgrenzen.json")


@lru_cache(maxsize=None)
def get_assumption_rules() -> dict[str, Any]:
    return _load("aannameregels.json")


@lru_cache(maxsize=None)
def get_vabi_mapping() -> dict[str, Any]:
    return _load("vabi_mapping.json")


@lru_cache(maxsize=None)
def get_woning_schema() -> dict[str, Any]:
    return _load("woningmodel_schema.json")


@lru_cache(maxsize=None)
def get_reference_cases() -> dict[str, Any]:
    return _load("referentiecases.json")


@lru_cache(maxsize=None)
def get_value_impact() -> dict[str, Any]:
    return _load("woningwaarde_label_impact.json")
