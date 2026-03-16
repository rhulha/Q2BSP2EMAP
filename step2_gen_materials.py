"""
Copies Q2 neural-upscale PNGs into the Prodeus Materials folder
and writes a .mat sidecar for each one.

Source : neural_upscale_dir  (e.g. C:/Action/id/quake2-neural-upscale/textures)
Target : materials_dir        (e.g. .../Prodeus/Prodeus_Data/StreamingAssets/Materials)

Both paths are read from conf.ini.
"""

from __future__ import annotations

import configparser
import shutil
from pathlib import Path

_conf = configparser.ConfigParser()
_conf.read(Path(__file__).parent / "conf.ini")

SRC_DIR  = Path(_conf["paths"]["neural_upscale_dir"])
DEST_DIR = Path(_conf["paths"]["materials_dir"])

_MAT_TEMPLATE = (
    "shader=environment\r\n"
    "surface=Default\r\n"
    "parmTex=_MainTex={filename}\r\n"
)


def generate() -> None:
    png_files = list(SRC_DIR.rglob("*.png"))
    if not png_files:
        print(f"no PNGs found under {SRC_DIR}")
        return

    copied = 0
    skipped = 0

    for src in png_files:
        rel = src.relative_to(SRC_DIR)
        dest_png = DEST_DIR / rel
        dest_mat = dest_png.with_suffix(".mat")

        dest_png.parent.mkdir(parents=True, exist_ok=True)

        if not dest_png.exists():
            shutil.copy2(src, dest_png)
            copied += 1
        else:
            skipped += 1

        if not dest_mat.exists():
            mat_text = _MAT_TEMPLATE.format(filename=src.name)
            dest_mat.write_text(mat_text, encoding="utf-8")

    print(f"done — {copied} PNGs copied, {skipped} already present")
    print(f"target: {DEST_DIR}")


if __name__ == "__main__":
    generate()
