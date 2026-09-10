"""Texture skip/sky rules and UV projection from Q2 texinfo axes."""
from __future__ import annotations

import struct

from .config import DEFAULT_TEX_SIZE, MATERIALS_DIR, SKIP_ENDINGS, SKY_KEYWORDS
from .geometry import _V


def _should_skip(texture: str) -> bool:
    low = texture.lower()
    return any(low.endswith(s) for s in SKIP_ENDINGS)


def _is_sky(texture: str) -> bool:
    low = texture.lower()
    return any(kw in low for kw in SKY_KEYWORDS)


_tex_size_cache: dict[str, tuple[float, float]] = {}


def _get_tex_size(texture: str) -> tuple[float, float]:
    if texture in _tex_size_cache:
        return _tex_size_cache[texture]
    path = MATERIALS_DIR / f"{texture}.png"
    if path.exists():
        data = path.read_bytes()
        if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            if w > 0 and h > 0:
                _tex_size_cache[texture] = (float(w), float(h))
                return _tex_size_cache[texture]
    _tex_size_cache[texture] = (DEFAULT_TEX_SIZE, DEFAULT_TEX_SIZE)
    return _tex_size_cache[texture]


def _compute_uv(vertex: _V, ti: dict) -> tuple[float, float]:
    ux, uy, uz = float(ti["ux"]), float(ti["uy"]), float(ti["uz"])
    vx, vy, vz = float(ti["vx"]), float(ti["vy"]), float(ti["vz"])
    w, h = _get_tex_size(ti["texture"])
    u = (vertex.x * ux + vertex.y * uy + vertex.z * uz + float(ti["u_offset"])) / w
    v = (vertex.x * vx + vertex.y * vy + vertex.z * vz + float(ti["v_offset"])) / h
    return u, v
