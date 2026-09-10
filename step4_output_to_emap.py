"""CLI entry point: convert every step3 output/<map> directory to a .emap file.

The conversion logic lives in the emap/ package; this module wires it up and
re-exports the pieces tests and the debug scripts import directly.
"""
from __future__ import annotations

from pathlib import Path

from emap.config import EMAP_DIR, MATERIALS_DIR, SCALE
from emap.coords import _parse_origin, _q2_to_emap
from emap.io_utils import _load_csv, _load_json
from emap.movers_door import DOOR_START_OPEN, _build_button_triggers, _build_door_movers
from emap.movers_plat import _build_plat_movers
from emap.writer import convert_to_emap

__all__ = [
    "EMAP_DIR", "MATERIALS_DIR", "SCALE", "DOOR_START_OPEN",
    "_load_csv", "_load_json", "_parse_origin", "_q2_to_emap",
    "_build_plat_movers", "_build_door_movers", "_build_button_triggers",
    "convert_to_emap", "main",
]


def main() -> None:
    out_root = Path(__file__).parent / "output"
    out_dirs = sorted(d for d in out_root.iterdir() if d.is_dir())
    if not out_dirs:
        print("no output directories found — run step3 first")
        return

    EMAP_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in out_dirs:
        if not (out_dir / "planes.csv").exists():
            continue
        emap_path = EMAP_DIR / f"{out_dir.name}.emap"
        print(f"converting {out_dir.name} ...")
        convert_to_emap(out_dir, emap_path)

    print("all done.")


if __name__ == "__main__":
    main()
