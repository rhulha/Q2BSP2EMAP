from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_VERTICES

_SIZE = 12


def read_vertices(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_VERTICES])
    result = []
    for _ in range(br.length() // _SIZE):
        x, y, z = br.read_floats(3)
        result.append({"x": x, "y": y, "z": z})
    return result
