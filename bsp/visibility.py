import csv
import struct
from pathlib import Path

from bsp.binary_reader import BinaryReader
from bsp.reader import LUMP_VISIBILITY


def _decompress_pvs(data: bytes, offset: int, num_clusters: int) -> list[int]:
    bits = []
    i = offset
    while len(bits) < num_clusters and i < len(data):
        b = data[i]; i += 1
        if b != 0:
            for j in range(8):
                bits.append((b >> j) & 1)
        else:
            count = data[i] if i < len(data) else 0
            i += 1
            bits.extend([0] * (count * 8))
    return bits[:num_clusters]


def write_visibility_csv(out_dir: Path, lumps: list[bytes]) -> None:
    data = lumps[LUMP_VISIBILITY]
    if len(data) < 4:
        return

    num_clusters = struct.unpack_from("<i", data, 0)[0]
    if num_clusters <= 0 or len(data) < 4 + num_clusters * 8:
        return

    pvs_offsets = [
        struct.unpack_from("<i", data, 4 + i * 8)[0]
        for i in range(num_clusters)
    ]

    target = out_dir / "visibility.csv"
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(range(num_clusters))
        for i in range(num_clusters):
            row = _decompress_pvs(data, pvs_offsets[i], num_clusters)
            writer.writerow(row)
    print(f"  wrote {target.name}")
