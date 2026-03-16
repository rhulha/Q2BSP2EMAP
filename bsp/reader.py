from __future__ import annotations

from pathlib import Path

from .binary_reader import BinaryReader

LUMP_ENTITIES     = 0
LUMP_PLANES       = 1
LUMP_VERTICES     = 2
LUMP_VISIBILITY   = 3
LUMP_NODES        = 4
LUMP_TEXINFO      = 5
LUMP_FACES        = 6
LUMP_LIGHTMAPS    = 7
LUMP_LEAVES       = 8
LUMP_LEAF_FACES   = 9
LUMP_LEAF_BRUSHES = 10
LUMP_EDGES        = 11
LUMP_FACE_EDGES   = 12
LUMP_MODELS       = 13
LUMP_BRUSHES      = 14
LUMP_BRUSH_SIDES  = 15
LUMP_POP          = 16
LUMP_AREAS        = 17
LUMP_AREA_PORTALS = 18
NUM_LUMPS         = 19

Q2_VERSION = 38
Q2_MAGIC   = "IBSP"


def load_bsp(path: Path) -> list[bytes]:
    data = path.read_bytes()
    br = BinaryReader(data)

    magic = br.read_string(4)
    version = br.read_int()
    if magic != Q2_MAGIC:
        raise ValueError(f"not a Q2 BSP (magic={magic!r})")
    if version != Q2_VERSION:
        raise ValueError(f"expected BSP version {Q2_VERSION}, got {version}")

    offsets, lengths = [], []
    for _ in range(NUM_LUMPS):
        offsets.append(br.read_int())
        lengths.append(br.read_int())

    return [data[offsets[i]: offsets[i] + lengths[i]] for i in range(NUM_LUMPS)]
