from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_NODES


@dataclass
class Node:
    plane_num: int
    children: list[int]
    mins: list[int]
    maxs: list[int]
    first_face: int
    num_faces: int
    SIZE = 28


def read_nodes(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_NODES])
    result = []
    for _ in range(br.length() // Node.SIZE):
        result.append(asdict(Node(
            br.read_int(),
            br.read_ints(2),
            br.read_int16s(3),
            br.read_int16s(3),
            br.read_uint16(),
            br.read_uint16(),
        )))
    return result
