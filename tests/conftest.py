import os
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LIVE_TEST_FILES = (
    PROJECT_ROOT / "tests" / "fixtures" / "sample_report.pdf",
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live-gemini",
        action="store_true",
        default=False,
        help="Run tests that perform real Gemini API calls.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_gemini: tests that call the real Gemini API and require GEMINI_API_KEY",
    )


def _live_enabled(config: pytest.Config) -> bool:
    return bool(config.getoption("--live-gemini"))


def _validate_live_prerequisites() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise pytest.UsageError(
            "Live Gemini tests requested but GEMINI_API_KEY is not set. "
            "Set GEMINI_API_KEY and rerun with --live-gemini."
        )

    missing_files = [str(path.relative_to(PROJECT_ROOT)) for path in LIVE_TEST_FILES if not path.exists()]
    if missing_files:
        raise pytest.UsageError(
            "Live Gemini tests requested but required fixture files are missing: "
            + ", ".join(missing_files)
        )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    live_enabled = _live_enabled(config)

    if live_enabled:
        _validate_live_prerequisites()
        return

    skip_live = pytest.mark.skip(
        reason="Live Gemini tests are disabled. Use --live-gemini."
    )

    for item in items:
        if "live_gemini" in item.keywords:
            item.add_marker(skip_live)
