from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_PLANES


@dataclass
class Plane:
    normal: list[float]
    dist: float
    type: int
    SIZE = 20


def read_planes(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_PLANES])
    result = []
    for _ in range(br.length() // Plane.SIZE):
        result.append(asdict(Plane(br.read_floats(3), br.read_float(), br.read_int())))
    return result
