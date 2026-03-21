import os
from typing import Any

from flask import Flask, request
from pydantic import ValidationError

from gemini_service import (
    build_final_report,
    download_file_to_temp,
    extract_report_data,
    optimize_report,
    upload_case_file,
)
from schemas import RunPocFlowRequest
from validators import normalize_constraints, validate_extract


def create_app() -> Flask:
    """
    Application factory for the energy label tool.
    """
    app = Flask(__name__)

    app.config["APP_NAME"] = os.getenv("APP_NAME", "ai-tooling-platform")
    app.config["ENVIRONMENT"] = os.getenv("FLASK_ENV", "production")

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

    @app.post("/run-poc-flow")
    def run_poc_flow() -> tuple[dict[str, Any], int]:
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
            constraints = normalize_constraints(
                target_label=parsed.target_label,
                required_measures=parsed.required_measures,
            )
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

        try:
            local_path = download_file_to_temp(str(parsed.file_url))
            uploaded_file = upload_case_file(local_path)
            extracted_report = extract_report_data(uploaded_file)
            validated_report = validate_extract(extracted_report)
            optimization_result = optimize_report(validated_report, constraints)
            final_report = build_final_report(optimization_result, constraints)
        except RuntimeError as exc:
            return {
                "error": {
                    "code": "processing_error",
                    "message": str(exc),
                }
            }, 500
        except Exception as exc:
            return {
                "error": {
                    "code": "unexpected_error",
                    "message": f"Unexpected error during POC flow: {exc}",
                }
            }, 500

        return {
            "status": "completed",
            "message": "POC flow completed successfully.",
            "data": {
                "user_id": parsed.user_id,
                "file_url": str(parsed.file_url),
                "constraints": constraints.model_dump(),
                "validated_report": validated_report.model_dump(),
                "optimization_result": optimization_result.model_dump(),
                "final_report": final_report.model_dump(),
            },
        }, 200

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
