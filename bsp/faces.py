from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_FACES


@dataclass
class Face:
    plane_num: int
    side: int
    first_edge: int
    num_edges: int
    texinfo_num: int
    styles: list[int]
    lightmap_ofs: int
    SIZE = 20


def read_faces(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_FACES])
    result = []
    for _ in range(br.length() // Face.SIZE):
        plane_num   = br.read_uint16()
        side        = br.read_uint16()
        first_edge  = br.read_int()
        num_edges   = br.read_int16()
        texinfo_num = br.read_int16()
        styles      = list(br.read_bytes(4))
        lightmap_ofs = br.read_int()
        result.append(asdict(Face(plane_num, side, first_edge, num_edges, texinfo_num, styles, lightmap_ofs)))
    return result
