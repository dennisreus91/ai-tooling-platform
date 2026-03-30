import os
import sys
from pathlib import Path
from typing import Iterator

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
    config.addinivalue_line(
        "markers",
        "stepwise_live: live tests that validate the pipeline step by step",
    )
    config.addinivalue_line(
        "markers",
        "e2e_live: live end-to-end tests that validate the full flow",
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

    missing_files = [
        str(path.relative_to(PROJECT_ROOT))
        for path in LIVE_TEST_FILES
        if not path.exists()
    ]
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


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def sample_report_path() -> Path:
    path = PROJECT_ROOT / "tests" / "fixtures" / "sample_report.pdf"
    if not path.exists():
        pytest.fail(f"Expected fixture file does not exist: {path}")
    return path


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch):
    """
    Flask app fixture for API tests.
    Zet test fixture endpoint expliciet aan voor testdoeleinden.
    """
    monkeypatch.setenv("ALLOW_TEST_FILE_ENDPOINT", "true")

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def live_gemini_enabled(pytestconfig: pytest.Config) -> bool:
    return _live_enabled(pytestconfig)


@pytest.fixture()
def required_gemini_api_key(live_gemini_enabled: bool) -> str:
    """
    Alleen gebruiken in tests die echt een API key nodig hebben.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if live_gemini_enabled and not api_key:
        pytest.fail("GEMINI_API_KEY ontbreekt voor live Gemini test.")
    return api_key


@pytest.fixture()
def temp_env(monkeypatch: pytest.MonkeyPatch):
    """
    Helper fixture om eenvoudig tijdelijk env vars te zetten binnen een test.
    """
    return monkeypatch
