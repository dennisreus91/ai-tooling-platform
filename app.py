import os
from typing import Any

from flask import Flask, request
from pydantic import ValidationError

from schemas import RunPocFlowRequest
from validators import normalize_constraints


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

        return {
            "status": "accepted",
            "message": "POC intake received successfully.",
            "data": {
                "user_id": parsed.user_id,
                "file_url": str(parsed.file_url),
                "constraints": {
                    "target_label": constraints.target_label,
                    "required_measures": constraints.required_measures,
                },
            },
        }, 200

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
