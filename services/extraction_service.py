from __future__ import annotations

from schemas import WoningModel


def extract_woningmodel_from_payload(payload: dict) -> WoningModel:
    # POC null-safe parser; in productie via Gemini extractie met schema/mapping.
    return WoningModel.model_validate(payload)
