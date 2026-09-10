"""Q2 <-> Prodeus coordinate conversion, player start selection, and the
generic trigger-volume node builder shared by movers, buttons and level exits.
"""
from __future__ import annotations

from .config import SCALE
from .templates import _NODE_TEMPLATES


def _fmt_pos(origin: str) -> str:
    x, y, z = (float(v) for v in origin.split())
    return f"{x * SCALE},{z * SCALE},{y * SCALE}"


def _select_player_start(entities: dict) -> dict | None:
    # Q2 spawns a new game at the info_player_start without a targetname;
    # targetname'd starts are level-transition arrival points (e.g. from base2).
    starts = entities.get("info_player_start", [])
    for ent in starts:
        if not ent.get("targetname") and ent.get("origin"):
            return ent
    for ent in starts:
        if ent.get("origin"):
            return ent
    return None


def _player_rotation(ent: dict) -> str:
    # Q2 angle is yaw CCW about +X (Z-up); Prodeus yaw is about +Y (left-handed).
    angle = float(ent.get("angle") or 0)
    yaw = (90.0 - angle) % 360.0
    return f"0,{yaw:g},0"


def _parse_origin(origin: str | None) -> tuple[float, float, float]:
    if not origin:
        return 0.0, 0.0, 0.0
    x, y, z = (float(v) for v in origin.split())
    return x, y, z


def _q2_to_emap(x: float, y: float, z: float) -> tuple[float, float, float]:
    return x * SCALE, z * SCALE, y * SCALE


def _build_trigger_node(pos: tuple[float, float, float], size: tuple[float, float, float],
                        target_structs: str, node_id: int) -> str:
    return (_NODE_TEMPLATES["mover_trigger"]
            .replace("%POS%", ",".join(str(v) for v in pos))
            .replace("%SIZE%", ",".join(str(v) for v in size))
            .replace("%TARGETS%", target_structs)
            .replace("%ID%", str(node_id)))


def _model_center_size(model: dict, origin: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = [float(model[f"min_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
    maxs = [float(model[f"max_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
    center = _q2_to_emap((mins[0] + maxs[0]) / 2, (mins[1] + maxs[1]) / 2, (mins[2] + maxs[2]) / 2)
    size = _q2_to_emap(maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2])
    return center, size
