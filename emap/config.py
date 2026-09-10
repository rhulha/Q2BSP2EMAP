"""Shared configuration and constants for the Q2 BSP -> Prodeus .emap converter."""
from __future__ import annotations

import configparser
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_conf = configparser.ConfigParser()
_conf.read(_ROOT / "conf.ini")
EMAP_DIR      = Path(_conf["paths"]["emap_dir"])
MATERIALS_DIR = Path(_conf["paths"]["materials_dir"])

SCALE             = 1.0 / 30.0
DEFAULT_TEX_SIZE  = 64.0
EPSILON      = 1e-5
MAX_FACE_PTS = 6
# Prodeus treats zero as an unset object reference: editor import drops targets
# to node 0 and leaves brush parent=0 dangling when it renumbers the nodes.
FIRST_NODE_ID = 1

CONTENTS_SOLID  = 0x1
CONTENTS_DETAIL = 0x8000000

SKYBOX = "Skybox/Asteroid_Surface"
SKIP_ENDINGS = ("clip", "trigger", "hint", "nodraw", "skip", "common/trigger")
SKY_KEYWORDS = ("sky",)
