import os
from pathlib import Path
from typing import Any
import tempfile

from flask import Flask, abort, request, send_file
from pydantic import ValidationError

from gemini_service import (
    download_file_to_temp,
    extract_woningmodel_data,
    upload_case_file,
)
from schemas import RunPocFlowRequest
from services.poc_flow_service import run_poc_flow
from validators import normalize_constraints


_KNOWN_PROCESSING_CODES = (
    "missing_ep2_data",
    "insufficient_measures",
    "methodology_conflict",
    "invalid_llm_json",
    "invalid_woningmodel",
    "processing_error",
)


def _extract_processing_code(message: str) -> str:
    for code in _KNOWN_PROCESSING_CODES:
        if message.startswith(f"{code}:"):
            return code
    return "processing_error"


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["APP_NAME"] = os.getenv("APP_NAME", "ai-tooling-platform")
    app.config["ENVIRONMENT"] = os.getenv("FLASK_ENV", "production")
    app.config["ALLOW_TEST_FILE_ENDPOINT"] = (
        os.getenv("ALLOW_TEST_FILE_ENDPOINT", "").lower() in {"1", "true", "yes"}
    )

    fixtures_dir = (Path(__file__).resolve().parent / "tests" / "fixtures").resolve()

    @app.get("/")
    def root() -> tuple[dict[str, Any], int]:
        return {
            "name": app.config["APP_NAME"],
            "status": "running",
            "message": "AI tooling platform API is online.",
        }, 200

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/test-fixtures/<path:filename>")
    def test_fixture_file(filename: str):
        if not app.config["ALLOW_TEST_FILE_ENDPOINT"]:
            abort(404)

        requested_path = (fixtures_dir / filename).resolve()
        if fixtures_dir not in requested_path.parents and requested_path != fixtures_dir:
            abort(404)
        if not requested_path.exists() or not requested_path.is_file():
            abort(404)
        return send_file(requested_path)

    @app.post("/run-poc-flow")
    def run_poc_flow_route() -> tuple[dict[str, Any], int]:
        payload = request.get_json(silent=True)
        if payload is None:
            return {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            }, 400

        try:
            parsed = RunPocFlowRequest.model_validate(payload)
            constraints = normalize_constraints(parsed.target_label, parsed.required_measures)
        except ValidationError as exc:
            return {
                "error": {
                    "code": "validation_error",
                    "message": "Input validation failed.",
                    "details": exc.errors(),
                }
            }, 400
        except ValueError as exc:
            return {
                "error": {
                    "code": "constraint_error",
                    "message": str(exc),
                }
            }, 400

        local_path: str | None = None

        try:
            # 1. Download bestand
            local_path = download_file_to_temp(str(parsed.file_url))

            # 2. Upload naar Gemini
            uploaded_file = upload_case_file(local_path)

            # 3. Extractie naar WoningModel
            woningmodel = extract_woningmodel_data(uploaded_file)

            # 4. Volledige POC-flow
            result = run_poc_flow(constraints, woningmodel)

        except ValueError as exc:
            return {
                "error": {
                    "code": _extract_processing_code(str(exc)),
                    "message": str(exc),
                }
            }, 400
        except RuntimeError as exc:
            return {
                "error": {
                    "code": _extract_processing_code(str(exc)),
                    "message": str(exc),
                }
            }, 500
        except Exception as exc:
            return {
                "error": {
                    "code": "processing_error",
                    "message": f"processing_error: {exc}",
                }
            }, 500
        finally:
            if local_path:
                try:
                    Path(local_path).unlink(missing_ok=True)
                except Exception:
                    # tijdelijke cleanup mag de response niet breken
                    pass

        response_data = result.model_dump()

        if not parsed.debug:
            # Behoud eindrapport en kernoutput, maar verberg zware debug/tussenlagen
            response_data.pop("woningmodel", None)
            response_data.pop("measure_statuses", None)
            response_data.pop("measure_overview", None)
            response_data.pop("scenario_advice", None)

        return {
            "status": "completed",
            "message": "POC flow completed successfully.",
            "data": response_data,
        }, 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
