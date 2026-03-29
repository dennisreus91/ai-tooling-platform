import os
from pathlib import Path
from typing import Any

from flask import Flask, abort, request, send_file
from pydantic import ValidationError

from gemini_service import download_file_to_temp, extract_report_data, upload_case_file
from schemas import RunPocFlowRequest, WoningModel
from services.poc_flow_service import run_poc_flow
from validators import normalize_constraints


_KNOWN_PROCESSING_CODES = (
    "missing_ep2_data",
    "insufficient_measures",
    "methodology_conflict",
    "invalid_llm_json",
    "processing_error",
)


def _extract_processing_code(message: str) -> str:
    for code in _KNOWN_PROCESSING_CODES:
        if message.startswith(f"{code}:"):
            return code
    return "processing_error"


def _build_woningmodel_from_extract(extract_payload: dict[str, Any]) -> WoningModel:
    current_label = str(extract_payload.get("current_label", "onbekend"))
    current_ep2 = float(extract_payload.get("current_ep2_kwh_m2", 320.0))
    return WoningModel.model_validate(
        {
            "meta": {"source": "gemini_extract"},
            "woning": {"oppervlakte_m2": 120},
            "prestatie": {
                "current_label": current_label,
                "current_ep2_kwh_m2": current_ep2,
            },
            "bouwdelen": {},
            "installaties": {},
            "samenvatting_huidige_maatregelen": [m.get("name", "") for m in extract_payload.get("measures", [])],
            "extractie_meta": {
                "confidence": 0.6,
                "missing_fields": [],
                "assumptions": ["Woningmodel deels afgeleid van extractie-output."],
                "uncertainties": extract_payload.get("notes", []),
            },
        }
    )


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
            return {"error": {"code": "invalid_json", "message": "Request body must be valid JSON."}}, 400

        try:
            parsed = RunPocFlowRequest.model_validate(payload)
            constraints = normalize_constraints(parsed.target_label, parsed.required_measures)
        except ValidationError as exc:
            return {"error": {"code": "validation_error", "message": "Input validation failed.", "details": exc.errors()}}, 400
        except ValueError as exc:
            return {"error": {"code": "constraint_error", "message": str(exc)}}, 400

        try:
            local_path = download_file_to_temp(str(parsed.file_url))
            uploaded_file = upload_case_file(local_path)
            extracted_report = extract_report_data(uploaded_file).model_dump()
            woningmodel = _build_woningmodel_from_extract(extracted_report)
            result = run_poc_flow(constraints, woningmodel)
        except Exception as exc:
            return {
                "error": {
                    "code": _extract_processing_code(str(exc)),
                    "message": f"processing_error: {exc}",
                }
            }, 500

        response_data = result.model_dump()
        if not parsed.debug:
            response_data.pop("woningmodel", None)

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
