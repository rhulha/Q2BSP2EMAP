from __future__ import annotations

import configparser
import struct
from pathlib import Path

_MAGIC       = b"PACK"
_ENTRY_SIZE  = 64
_NAME_SIZE   = 56

_conf = configparser.ConfigParser()
_conf.read(Path(__file__).parent / "conf.ini")
_PAK_DIR = Path(_conf["paths"]["pak_dir"])
_BASE_DIR = Path(_conf["paths"]["base_dir"])


def unpack_pak(pak_path: Path, out_dir: Path) -> None:
    data = pak_path.read_bytes()

    magic, dir_offset, dir_length = struct.unpack_from("<4sii", data, 0)
    if magic != _MAGIC:
        raise ValueError(f"{pak_path.name}: not a PAK file (magic={magic!r})")

    entry_count = dir_length // _ENTRY_SIZE
    print(f"{pak_path.name}: {entry_count} files")

    for i in range(entry_count):
        base = dir_offset + i * _ENTRY_SIZE
        raw_name, file_offset, file_size = struct.unpack_from(f"<{_NAME_SIZE}sii", data, base)
        name = raw_name.split(b"\x00", 1)[0].decode("latin-1")

        dest = out_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data[file_offset: file_offset + file_size])

    print(f"  extracted to {out_dir}")


def main() -> None:
    paks = sorted(_PAK_DIR.glob("*.pak"))
    if not paks:
        print(f"no .pak files found in {_PAK_DIR}")
        return

    for pak in paks:
        unpack_pak(pak, _BASE_DIR)

    print("done.")


if __name__ == "__main__":
    main()
