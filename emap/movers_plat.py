"""func_plat (lifts/platforms) -> Func_Mover + auto-generated ride trigger."""
from __future__ import annotations

from pathlib import Path

from .config import SCALE
from .coords import _build_trigger_node
from .io_utils import _load_csv, _load_json
from .model_brushes import _collect_model_brushes
from .templates import _NODE_TEMPLATES

PLAT_DEFAULT_LIP   = 8.0
PLAT_DEFAULT_SPEED = 200.0  # Q2 units/sec (game code default 20 units per 0.1s frame)


def _plat_trigger_bounds(model: dict, travel: float, lip: float, spawnflags: int,
                         origin: tuple[float, float, float]) -> tuple[tuple, tuple]:
    # Q2 game/g_func.c: plat_spawn_inside_trigger. Bounds are in Q2 coordinates
    # until the final Y/Z swap. Include the whole model, including clip brushes.
    mins = [float(model[f"min_{axis}"]) for axis in "xyz"]
    maxs = [float(model[f"max_{axis}"]) for axis in "xyz"]
    lower = [mins[0] + 25, mins[1] + 25, maxs[2] + 8 - (travel + lip)]
    upper = [maxs[0] - 25, maxs[1] - 25, maxs[2] + 8]
    if spawnflags & 1:  # PLAT_LOW_TRIGGER
        upper[2] = lower[2] + 8
    for axis in (0, 1):
        if upper[axis] <= lower[axis]:
            lower[axis] = (mins[axis] + maxs[axis]) / 2
            upper[axis] = lower[axis] + 1
    center = tuple(((lower[i] + upper[i]) / 2 + origin[i]) * SCALE for i in (0, 2, 1))
    size = tuple((upper[i] - lower[i]) * SCALE for i in (0, 2, 1))
    return center, size


def _build_plat_movers(entities: dict, out_dir: Path, next_id: int) -> tuple[
        list[str], dict[int, int], dict[int, tuple[float, float, float]], int]:
    plats = entities.get("func_plat", [])
    if not plats:
        return [], {}, {}, next_id

    models_rows = _load_csv(out_dir / "models.csv")
    nodes_rows = _load_csv(out_dir / "nodes.csv")
    leafs_rows = _load_csv(out_dir / "leafs.csv")
    leaf_brushes = _load_json(out_dir / "leaf_brushes.json")

    node_texts: list[str] = []
    brush_parent: dict[int, int] = {}
    mover_offsets: dict[int, tuple[float, float, float]] = {}

    for ent in plats:
        model_ref = ent.get("model", "")
        if not model_ref.startswith("*"):
            continue
        model = models_rows[int(model_ref[1:])]

        # Q2 treats explicit zero values as unset for these fields.
        lip = float(ent.get("lip", 0)) or PLAT_DEFAULT_LIP
        bbox_height = float(model["max_z"]) - float(model["min_z"])
        travel = float(ent.get("height", 0)) or (bbox_height - lip)
        if travel <= 0:
            continue

        speed = float(ent.get("speed", 0)) or PLAT_DEFAULT_SPEED
        move_time = travel / speed if speed > 0 else 1.0

        cx = (float(model["min_x"]) + float(model["max_x"])) / 2
        cy = (float(model["min_y"]) + float(model["max_y"])) / 2
        cz = (float(model["min_z"]) + float(model["max_z"])) / 2

        origin = tuple(float(v) for v in ent.get("origin", "0 0 0").split())
        named = bool(ent.get("targetname"))
        # Ordinary Q2 plats spawn at the bottom. Target-controlled plats start
        # at the top and must not activate until their external target fires.
        offset_z = origin[2] if named else origin[2] - travel
        offset = (origin[0] * SCALE, offset_z * SCALE, origin[1] * SCALE)
        mover_id = next_id
        next_id += 1

        text = (_NODE_TEMPLATES["mover"]
                .replace("%POS%", f"{cx * SCALE + offset[0]},{cz * SCALE + offset[1]},{cy * SCALE + offset[2]}")
                .replace("%DELTA%", f"0,{(-travel if named else travel) * SCALE},0")
                .replace("%TIME%", f"{move_time:.6g}")
                .replace("%ID%", str(mover_id)))
        node_texts.append(text)
        mover_offsets[mover_id] = offset

        for b in _collect_model_brushes(int(model["headnode"]), nodes_rows, leafs_rows, leaf_brushes):
            brush_parent[b] = mover_id

        if named:
            print(f"  func_plat {model_ref}: targetname={ent['targetname']} needs external trigger conversion; kept at top")
            continue

        center, size = _plat_trigger_bounds(model, travel, lip,
                                            int(ent.get("spawnflags", 0)), origin)
        trigger = _build_trigger_node(center, size, f"OnFirstEnter,SetDestEnd,{mover_id}", next_id)
        node_texts.append(trigger)
        next_id += 1

    return node_texts, brush_parent, mover_offsets, next_id
