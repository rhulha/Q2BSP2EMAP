from __future__ import annotations

import io
import struct


class BinaryReader:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self._data_len = len(data)

    def read_bytes(self, count: int) -> bytes:
        data = self._buf.read(count)
        if len(data) != count:
            raise EOFError(f"expected {count} bytes, got {len(data)}")
        return data

    def read_int(self) -> int:
        return struct.unpack("<i", self.read_bytes(4))[0]

    def read_ints(self, count: int) -> list[int]:
        if count == 0:
            return []
        return list(struct.unpack(f"<{count}i", self.read_bytes(4 * count)))

    def read_uint16(self) -> int:
        return struct.unpack("<H", self.read_bytes(2))[0]

    def read_uint16s(self, count: int) -> list[int]:
        if count == 0:
            return []
        return list(struct.unpack(f"<{count}H", self.read_bytes(2 * count)))

    def read_int16(self) -> int:
        return struct.unpack("<h", self.read_bytes(2))[0]

    def read_int16s(self, count: int) -> list[int]:
        if count == 0:
            return []
        return list(struct.unpack(f"<{count}h", self.read_bytes(2 * count)))

    def read_float(self) -> float:
        return struct.unpack("<f", self.read_bytes(4))[0]

    def read_floats(self, count: int) -> list[float]:
        if count == 0:
            return []
        return list(struct.unpack(f"<{count}f", self.read_bytes(4 * count)))

    def read_string(self, length: int) -> str:
        return self.read_bytes(length).decode("latin-1", errors="ignore")

    def length(self) -> int:
        return self._data_len
