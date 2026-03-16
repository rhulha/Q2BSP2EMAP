from pathlib import Path

from bsp.reader import LUMP_LIGHTMAPS


def write_lightmaps_bin(out_dir: Path, lumps: list[bytes]) -> None:
    data = lumps[LUMP_LIGHTMAPS]
    target = out_dir / "lightmaps.bin"
    target.write_bytes(data)
    print(f"  wrote {target.name} ({len(data)} bytes)")
