from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_LEAF_BRUSHES, LUMP_LEAF_FACES, LUMP_LEAVES


@dataclass
class Leaf:
    contents: int
    cluster: int
    area: int
    mins: list[int]
    maxs: list[int]
    first_leaf_face: int
    num_leaf_faces: int
    first_leaf_brush: int
    num_leaf_brushes: int
    SIZE = 28


def read_leafs(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_LEAVES])
    result = []
    for _ in range(br.length() // Leaf.SIZE):
        result.append(asdict(Leaf(
            br.read_int(),
            br.read_int16(),
            br.read_int16(),
            br.read_int16s(3),
            br.read_int16s(3),
            br.read_uint16(),
            br.read_uint16(),
            br.read_uint16(),
            br.read_uint16(),
        )))
    return result


def read_leaf_faces(lumps: list[bytes]) -> list[int]:
    br = BinaryReader(lumps[LUMP_LEAF_FACES])
    return br.read_uint16s(br.length() // 2)


def read_leaf_brushes(lumps: list[bytes]) -> list[int]:
    br = BinaryReader(lumps[LUMP_LEAF_BRUSHES])
    return br.read_uint16s(br.length() // 2)
