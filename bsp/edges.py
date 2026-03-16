from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_EDGES, LUMP_FACE_EDGES

_EDGE_SIZE = 4


def read_edges(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_EDGES])
    result = []
    for _ in range(br.length() // _EDGE_SIZE):
        v0 = br.read_uint16()
        v1 = br.read_uint16()
        result.append({"v0": v0, "v1": v1})
    return result


def read_face_edges(lumps: list[bytes]) -> list[int]:
    br = BinaryReader(lumps[LUMP_FACE_EDGES])
    return br.read_ints(br.length() // 4)
