from dataclasses import asdict, dataclass

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_MODELS


@dataclass
class Model:
    mins: list[float]
    maxs: list[float]
    origin: list[float]
    headnode: int
    first_face: int
    num_faces: int
    SIZE = 48


def read_models(lumps: list[bytes]) -> list[dict]:
    br = BinaryReader(lumps[LUMP_MODELS])
    result = []
    for _ in range(br.length() // Model.SIZE):
        result.append(asdict(Model(
            br.read_floats(3),
            br.read_floats(3),
            br.read_floats(3),
            br.read_int(),
            br.read_int(),
            br.read_int(),
        )))
    return result
