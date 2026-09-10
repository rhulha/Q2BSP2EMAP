"""Small CSV/JSON loaders for the step3 output tables."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)
