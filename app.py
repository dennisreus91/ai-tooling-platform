import os
from typing import Any

from flask import Flask, jsonify


def create_app() -> Flask:
    """
    Application factory for the energy label tool.

    This keeps the app setup minimal and testable.
    """
    app = Flask(__name__)

    app.config["APP_NAME"] = os.getenv("APP_NAME", "energy-label-tool")
    app.config["ENVIRONMENT"] = os.getenv("FLASK_ENV", "production")

    @app.get("/")
    def root() -> tuple[dict[str, Any], int]:
        return {
            "name": app.config["APP_NAME"],
            "status": "running",
            "message": "Energy label tool API is online.",
        }, 200

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
