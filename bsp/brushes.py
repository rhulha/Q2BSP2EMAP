from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_BRUSH_SIDES, LUMP_BRUSHES


@dataclass
class Brush:
    first_side: int
    num_sides: int
    contents: int
    SIZE = 12


@dataclass
class BrushSide:
    plane_num: int
    texinfo: int
    SIZE = 4


def read_brushes(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_BRUSHES])
    result = []
    for _ in range(br.length() // Brush.SIZE):
        result.append(asdict(Brush(br.read_int(), br.read_int(), br.read_int())))
    return result


def read_brush_sides(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_BRUSH_SIDES])
    result = []
    for _ in range(br.length() // BrushSide.SIZE):
        result.append(asdict(BrushSide(br.read_uint16(), br.read_int16())))
    return result
