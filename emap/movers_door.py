"""func_door (and the func_button that can target them) -> Func_Mover pairs
plus the touch/press triggers that drive them."""
from __future__ import annotations

import math
from pathlib import Path

from .coords import _build_trigger_node, _parse_origin, _q2_to_emap
from .io_utils import _load_csv, _load_json
from .model_brushes import _collect_model_brushes
from .templates import _NODE_TEMPLATES

DOOR_DEFAULT_LIP   = 8.0
DOOR_DEFAULT_SPEED = 100.0
DOOR_START_OPEN    = 1
BUTTON_TRIGGER_DEPTH = 48.0
DOOR_TRIGGER_EXPAND  = 60.0


def _door_move_dir(ent: dict) -> tuple[float, float, float]:
    angle = float(ent.get("angle", "0") or 0)
    if angle == -1:
        return 0.0, 0.0, 1.0
    if angle == -2:
        return 0.0, 0.0, -1.0
    radians = math.radians(angle)
    return math.cos(radians), math.sin(radians), 0.0


def _door_trigger_bounds(specs: list[dict]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    # Q2 game/g_func.c: Think_SpawnDoorTrigger. The volume covers the whole door
    # team and is widened horizontally, so it reaches into the room instead of
    # staying inside the solid door slab where the player can never enter it.
    mins = [min(float(s["model"][f"min_{axis}"]) + s["origin"][idx] for s in specs)
            for idx, axis in enumerate("xyz")]
    maxs = [max(float(s["model"][f"max_{axis}"]) + s["origin"][idx] for s in specs)
            for idx, axis in enumerate("xyz")]
    for axis in (0, 1):
        mins[axis] -= DOOR_TRIGGER_EXPAND
        maxs[axis] += DOOR_TRIGGER_EXPAND
    center = _q2_to_emap((mins[0] + maxs[0]) / 2, (mins[1] + maxs[1]) / 2, (mins[2] + maxs[2]) / 2)
    size = _q2_to_emap(maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2])
    return center, size


def _button_move_dir(ent: dict) -> tuple[float, float, float]:
    angle = float(ent.get("angle", "-1") or -1)
    if angle == -1:
        return 0.0, 0.0, 1.0
    if angle == -2:
        return 0.0, 0.0, -1.0
    radians = math.radians(angle)
    return math.cos(radians), math.sin(radians), 0.0


def _button_trigger_bounds(model: dict, origin: tuple[float, float, float], ent: dict) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = [float(model[f"min_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
    maxs = [float(model[f"max_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
    move_dir = _button_move_dir(ent)
    lower = mins[:]
    upper = maxs[:]
    for axis in range(3):
        direction = move_dir[axis]
        # A Q2 button plate sinks into its wall along movedir, so the player
        # reaches it from the opposite side.
        if direction > 0.5:
            upper[axis] = lower[axis]
            lower[axis] = lower[axis] - BUTTON_TRIGGER_DEPTH
        elif direction < -0.5:
            lower[axis] = upper[axis]
            upper[axis] = upper[axis] + BUTTON_TRIGGER_DEPTH
    center = _q2_to_emap((lower[0] + upper[0]) / 2, (lower[1] + upper[1]) / 2, (lower[2] + upper[2]) / 2)
    size = _q2_to_emap(upper[0] - lower[0], upper[1] - lower[1], upper[2] - lower[2])
    return center, size


def _build_door_movers_with_targets(entities: dict, out_dir: Path, next_id: int) -> tuple[
        list[str], dict[int, int], dict[int, tuple[float, float, float]], dict[str, str], int]:
    doors = entities.get("func_door", [])
    if not doors:
        return [], {}, {}, {}, next_id

    models_rows = _load_csv(out_dir / "models.csv")
    nodes_rows = _load_csv(out_dir / "nodes.csv")
    leafs_rows = _load_csv(out_dir / "leafs.csv")
    leaf_brushes = _load_json(out_dir / "leaf_brushes.json")

    node_texts: list[str] = []
    brush_parent: dict[int, int] = {}
    mover_offsets: dict[int, tuple[float, float, float]] = {}
    door_specs: list[dict] = []

    for ent in doors:
        model_ref = ent.get("model", "")
        if not model_ref.startswith("*"):
            continue
        model = models_rows[int(model_ref[1:])]
        move_dir = _door_move_dir(ent)
        lip = float(ent.get("lip", 0)) or DOOR_DEFAULT_LIP
        size_x = float(model["max_x"]) - float(model["min_x"])
        size_y = float(model["max_y"]) - float(model["min_y"])
        size_z = float(model["max_z"]) - float(model["min_z"])
        travel = abs(move_dir[0]) * size_x + abs(move_dir[1]) * size_y + abs(move_dir[2]) * size_z - lip
        if travel <= 0:
            continue

        speed = float(ent.get("speed", 0)) or DOOR_DEFAULT_SPEED
        move_time = travel / speed if speed > 0 else 1.0

        cx = (float(model["min_x"]) + float(model["max_x"])) / 2
        cy = (float(model["min_y"]) + float(model["max_y"])) / 2
        cz = (float(model["min_z"]) + float(model["max_z"])) / 2
        origin = _parse_origin(ent.get("origin"))
        spawnflags = int(ent.get("spawnflags", 0))
        start_open = bool(spawnflags & DOOR_START_OPEN)
        start_offset_q2 = tuple(-axis * travel if start_open else 0.0 for axis in move_dir)
        pos = _q2_to_emap(cx + origin[0] + start_offset_q2[0],
                          cy + origin[1] + start_offset_q2[1],
                          cz + origin[2] + start_offset_q2[2])
        delta_q2 = tuple((-axis if start_open else axis) * travel for axis in move_dir)
        delta = _q2_to_emap(*delta_q2)
        offset = _q2_to_emap(*start_offset_q2)
        mover_id = next_id
        next_id += 1

        text = (_NODE_TEMPLATES["mover"]
                .replace("%POS%", f"{pos[0]},{pos[1]},{pos[2]}")
                .replace("%DELTA%", f"{delta[0]},{delta[1]},{delta[2]}")
                .replace("%TIME%", f"{move_time:.6g}")
                .replace("%ID%", str(mover_id)))
        node_texts.append(text)
        mover_offsets[mover_id] = offset

        for brush_idx in _collect_model_brushes(int(model["headnode"]), nodes_rows, leafs_rows, leaf_brushes):
            brush_parent[brush_idx] = mover_id

        door_specs.append({
            "entity": ent,
            "model": model,
            "mover_id": mover_id,
            "origin": origin,
            "start_open": start_open,
            "team": ent.get("team"),
        })

    targetname_targets: dict[str, str] = {}
    for spec in door_specs:
        targetname = spec["entity"].get("targetname")
        if not targetname or targetname in targetname_targets:
            continue
        target_ids = [str(item["mover_id"]) for item in door_specs if item["entity"].get("targetname") == targetname]
        targetname_targets[targetname] = ";".join(f"OnFirstEnter,SetDestEnd,{mover_id}" for mover_id in target_ids)

    # Q2 gives a door team a single trigger, spawned by the team master.
    teams: dict[object, list[dict]] = {}
    for spec in door_specs:
        teams.setdefault(spec["team"] or ("solo", spec["mover_id"]), []).append(spec)

    for members in teams.values():
        master = members[0]["entity"]
        model_ref = master.get("model", "")
        if master.get("targetname"):
            print(f"  func_door {model_ref}: targetname={master['targetname']} awaits external activation (no proximity trigger)")
            continue
        for spec in members:
            if spec["start_open"]:
                print(f"  func_door {spec['entity'].get('model', '')}: start_open is exported but does not yet mirror Q2 activation semantics")
        center, size = _door_trigger_bounds(members)
        targets = ";".join(f"OnFirstEnter,SetDestEnd,{m['mover_id']}" for m in members)
        node_texts.append(_build_trigger_node(center, size, targets, next_id))
        next_id += 1

    return node_texts, brush_parent, mover_offsets, targetname_targets, next_id


def _build_door_movers(entities: dict, out_dir: Path, next_id: int) -> tuple[
        list[str], dict[int, int], dict[int, tuple[float, float, float]], int]:
    node_texts, brush_parent, mover_offsets, _, next_id = _build_door_movers_with_targets(entities, out_dir, next_id)
    return node_texts, brush_parent, mover_offsets, next_id


def _build_button_triggers(entities: dict, out_dir: Path, targetname_targets: dict[str, str], next_id: int) -> tuple[list[str], int]:
    buttons = entities.get("func_button", [])
    if not buttons or not targetname_targets:
        return [], next_id

    models_rows = _load_csv(out_dir / "models.csv")
    node_texts: list[str] = []

    for ent in buttons:
        target = ent.get("target")
        model_ref = ent.get("model", "")
        if target not in targetname_targets or not model_ref.startswith("*"):
            continue
        model = models_rows[int(model_ref[1:])]
        origin = _parse_origin(ent.get("origin"))
        center, size = _button_trigger_bounds(model, origin, ent)
        node_texts.append(_build_trigger_node(center, size, targetname_targets[target], next_id))
        next_id += 1

    return node_texts, next_id
