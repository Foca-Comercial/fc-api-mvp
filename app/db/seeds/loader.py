from pathlib import Path
from typing import Any

import json5

DATA_DIR = Path(__file__).parent / "data"


def load_records(relative_path: str) -> list[dict[str, Any]]:
    path = DATA_DIR / relative_path
    with path.open(encoding="utf-8") as file:
        data = json5.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{relative_path}: se esperaba una lista de registros")  # noqa: TRY004
    return data
