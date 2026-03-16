from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_TEXINFO


@dataclass
class Texinfo:
    u_axis: list[float]
    u_offset: float
    v_axis: list[float]
    v_offset: float
    flags: int
    value: int
    texture: str
    next_texinfo: int
    SIZE = 76


def read_texinfo(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_TEXINFO])
    result = []
    for _ in range(br.length() // Texinfo.SIZE):
        u_axis   = br.read_floats(3)
        u_offset = br.read_float()
        v_axis   = br.read_floats(3)
        v_offset = br.read_float()
        flags    = br.read_int()
        value    = br.read_int()
        texture  = br.read_string(32).split("\x00", 1)[0]
        next_ti  = br.read_int()
        result.append(asdict(Texinfo(u_axis, u_offset, v_axis, v_offset, flags, value, texture, next_ti)))
    return result
