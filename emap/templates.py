"""Loads the .emap text fragments (header, surface, node templates) from input/."""
from __future__ import annotations

import json
from pathlib import Path

_INPUT_DIR = Path(__file__).resolve().parent.parent / "input"


def _load_text_template(name: str) -> str:
    return (_INPUT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", "\r\n")


_HEADER          = _load_text_template("emap_header.txt")
_SURF_TEMPLATE   = _load_text_template("emap_surf_template.txt")
with (_INPUT_DIR / "emap_node_templates.json").open(encoding="utf-8") as _f:
    _NODE_TEMPLATES: dict[str, str] = json.load(_f)

_ENTITY_MAP: dict[str, str] = {
    "weapon_shotgun":         "weapon_shotgun",
    "weapon_machinegun":      "weapon_smg",
    "monster_soldier_light":  "zombie",
    "monster_soldier":        "soldier",
    "monster_infantry":       "heavy",
    "ammo_bullets":           "ammo_bullets",
    "item_health":            "health_small",
    "light":                  "light",
}
