from __future__ import annotations
from bsp.reader import LUMP_ENTITIES
import re
from collections import defaultdict

_QUOTED_PAIR_RE = re.compile(r'\s*"([^"]*)"\s+"([^"]*)"\s*')


def read_entities(lumps: list[bytes]) -> dict:
    text = lumps[LUMP_ENTITIES].decode("latin-1", errors="ignore")
    entities: dict[str, list[dict[str, str]]] = defaultdict(list)
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "{":
            current = {}
            continue
        if line == "}":
            if current is None:
                raise ValueError("unexpected closing entity brace")
            classname = current.get("classname", "")
            entities[classname].append(current)
            current = None
            continue
        if current is None:
            continue
        match = _QUOTED_PAIR_RE.fullmatch(line)
        if not match:
            continue
        current[match.group(1)] = match.group(2)
    return dict(entities)
