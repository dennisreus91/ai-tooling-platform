import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=32)
def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text())
