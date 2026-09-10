from __future__ import annotations

import configparser
import csv
import json
import math
from pathlib import Path

import struct

_conf = configparser.ConfigParser()
_conf.read(Path(__file__).parent / "conf.ini")
EMAP_DIR      = Path(_conf["paths"]["emap_dir"])
MATERIALS_DIR = Path(_conf["paths"]["materials_dir"])

SCALE             = 1.0 / 30.0
DEFAULT_TEX_SIZE  = 64.0
EPSILON      = 1e-5
MAX_FACE_PTS = 6
# Prodeus treats zero as an unset object reference: editor import drops targets
# to node 0 and leaves brush parent=0 dangling when it renumbers the nodes.
FIRST_NODE_ID = 1

CONTENTS_SOLID  = 0x1
CONTENTS_DETAIL = 0x8000000

SKYBOX = "Skybox/Asteroid_Surface"
_SKIP_ENDINGS = ("clip", "trigger", "hint", "nodraw", "skip", "common/trigger")
_SKY_KEYWORDS = ("sky",)


# ---------- tiny vector math ----------

class _V:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float):
        self.x = x; self.y = y; self.z = z

    def dot(self, o: "_V") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "_V") -> "_V":
        return _V(self.y * o.z - self.z * o.y,
                  self.z * o.x - self.x * o.z,
                  self.x * o.y - self.y * o.x)

    def plus(self, o: "_V") -> "_V":
        return _V(self.x + o.x, self.y + o.y, self.z + o.z)

    def minus(self, o: "_V") -> "_V":
        return _V(self.x - o.x, self.y - o.y, self.z - o.z)

    def times(self, s: float) -> "_V":
        return _V(self.x * s, self.y * s, self.z * s)

    def divided_by(self, s: float) -> "_V":
        return _V(self.x / s, self.y / s, self.z / s)

    def normalize(self) -> "_V":
        l = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        return _V(self.x / l, self.y / l, self.z / l) if l > 0 else _V(0.0, 0.0, 0.0)


# ---------- plane math ----------

class _Plane:
    def __init__(self, nx: float, ny: float, nz: float, bsp_dist: float):
        self.normal = _V(nx, ny, nz)
        self.distance = -bsp_dist  # convention: distance_to_point = n·p + distance

    def distance_to_point(self, p: _V) -> float:
        return self.normal.dot(p) + self.distance


def _intersect_3(a: _Plane, b: _Plane, c: _Plane) -> _V | None:
    denom = a.normal.dot(b.normal.cross(c.normal))
    if abs(denom) < EPSILON:
        return None
    t1 = b.normal.cross(c.normal).times(-a.distance)
    t2 = c.normal.cross(a.normal).times(b.distance)
    t3 = a.normal.cross(b.normal).times(c.distance)
    return t1.minus(t2).minus(t3).divided_by(denom)


def _compute_polys(planes: list[_Plane]) -> list[list[_V]]:
    n = len(planes)
    polys: list[list[_V]] = [[] for _ in range(n)]
    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                v = _intersect_3(planes[i], planes[j], planes[k])
                if v is None:
                    continue
                if all(pl.distance_to_point(v) <= EPSILON for pl in planes):
                    polys[i].append(v)
                    polys[j].append(v)
                    polys[k].append(v)
    _sort_polys(polys, planes)
    return polys


def _sort_polys(polys: list[list[_V]], planes: list[_Plane]) -> None:
    for n_idx, polygon in enumerate(polys):
        if len(polygon) < 3:
            continue
        plane = planes[n_idx]
        cx = sum(p.x for p in polygon) / len(polygon)
        cy = sum(p.y for p in polygon) / len(polygon)
        cz = sum(p.z for p in polygon) / len(polygon)
        center = _V(cx, cy, cz)

        for i in range(len(polygon) - 2):
            a_vec = polygon[i].minus(center).normalize()
            split_n = plane.normal.cross(polygon[i].minus(center)).normalize()
            split_d = split_n.dot(polygon[i])

            best_angle = -1.0
            best_j = -1
            for j in range(i + 1, len(polygon)):
                if split_n.dot(polygon[j]) - split_d > -EPSILON:
                    b_vec = polygon[j].minus(center).normalize()
                    angle = a_vec.dot(b_vec)
                    if angle > best_angle:
                        best_angle = angle
                        best_j = j

            if best_j == -1:
                return
            polygon[best_j], polygon[i + 1] = polygon[i + 1], polygon[best_j]


# ---------- texture helpers ----------

def _should_skip(texture: str) -> bool:
    low = texture.lower()
    return any(low.endswith(s) for s in _SKIP_ENDINGS)


def _is_sky(texture: str) -> bool:
    low = texture.lower()
    return any(kw in low for kw in _SKY_KEYWORDS)


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


# ---------- emap text fragments ----------

_INPUT_DIR = Path(__file__).parent / "input"


def _load_text_template(name: str) -> str:
    return (_INPUT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", "\r\n")


_HEADER          = _load_text_template("emap_header.txt")
_SURF_TEMPLATE   = _load_text_template("emap_surf_template.txt")
with (_INPUT_DIR / "emap_node_templates.json").open(encoding="utf-8") as _f:
    _NODE_TEMPLATES: dict[str, str] = json.load(_f)

_ENTITY_MAP: dict[str, str] = {
    "weapon_shotgun":         "weapon_shotgun",
    "weapon_machinegun":      "weapon_smg",
    "monster_soldier_light":  "zombie",
    "monster_soldier":        "soldier",
    "monster_infantry":       "heavy",
    "ammo_bullets":           "ammo_bullets",
    "item_health":            "health_small",
    "light":                  "light",
}


# ---------- I/O helpers ----------

def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


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


# ---------- movers (func_plat) ----------

PLAT_DEFAULT_LIP   = 8.0
PLAT_DEFAULT_SPEED = 200.0  # Q2 units/sec (game code default 20 units per 0.1s frame)
DOOR_DEFAULT_LIP   = 8.0
DOOR_DEFAULT_SPEED = 100.0
DOOR_START_OPEN    = 1
BUTTON_TRIGGER_DEPTH = 48.0
DOOR_TRIGGER_EXPAND  = 60.0


def _collect_model_brushes(headnode: int, nodes_rows: list[dict], leafs_rows: list[dict],
                           leaf_brushes: list[int]) -> set[int]:
    result: set[int] = set()
    stack = [headnode]
    while stack:
        idx = stack.pop()
        if idx < 0:
            leaf = leafs_rows[-1 - idx]
            first = int(leaf["first_leaf_brush"])
            num = int(leaf["num_leaf_brushes"])
            result.update(leaf_brushes[first:first + num])
        else:
            node = nodes_rows[idx]
            stack.append(int(node["child0"]))
            stack.append(int(node["child1"]))
    return result


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


def _model_center_size(model: dict, origin: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = [float(model[f"min_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
    maxs = [float(model[f"max_{axis}"]) + origin[idx] for idx, axis in enumerate("xyz")]
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


# ---------- level exit (target_changelevel) ----------

LEVEL_END_LOAD_NEXT = True


def _build_level_end(entities: dict, out_dir: Path, next_id: int) -> tuple[list[str], int]:
    exits = [e for e in entities.get("target_changelevel", []) if e.get("targetname")]
    if not exits:
        return [], next_id

    exit_names = {e["targetname"] for e in exits}
    models_rows = _load_csv(out_dir / "models.csv")

    volumes: list[tuple[tuple, tuple]] = []
    for ents in entities.values():
        for ent in ents:
            if ent.get("target") not in exit_names:
                continue
            model_ref = ent.get("model", "")
            if not model_ref.startswith("*"):
                continue
            model = models_rows[int(model_ref[1:])]
            volumes.append(_model_center_size(model, _parse_origin(ent.get("origin"))))

    if not volumes:
        return [], next_id

    # Prodeus picks the destination from the campaign map order, not from the
    # node, so one LevelEnd serves every changelevel exit in the map.
    end_id = next_id
    next_id += 1
    pos = _q2_to_emap(*_parse_origin(exits[0].get("origin")))
    node_texts = [_NODE_TEMPLATES["level_end"]
                  .replace("%LOADNEXT%", str(LEVEL_END_LOAD_NEXT))
                  .replace("%POS%", ",".join(str(v) for v in pos))
                  .replace("%ID%", str(end_id))]

    for center, size in volumes:
        node_texts.append(_build_trigger_node(center, size, f"OnFirstEnter,Activate,{end_id}", next_id))
        next_id += 1

    return node_texts, next_id


# ---------- main converter ----------

def convert_to_emap(out_dir: Path, emap_path: Path) -> None:
    planes_rows     = _load_csv(out_dir / "planes.csv")
    brushes_rows    = _load_csv(out_dir / "brushes.csv")
    brush_sides_rows = _load_csv(out_dir / "brush_sides.csv")
    texinfo_rows    = _load_csv(out_dir / "texinfo.csv")
    entities        = _load_json(out_dir / "entities.json")

    bsp_planes = [
        _Plane(float(r["nx"]), float(r["ny"]), float(r["nz"]), float(r["distance"]))
        for r in planes_rows
    ]

    materials: list[str] = []
    mat_idx: dict[str, int] = {}

    def _ensure_mat(name: str) -> int:
        if name not in mat_idx:
            mat_idx[name] = len(materials)
            materials.append(name)
        return mat_idx[name]

    for ti in texinfo_rows:
        _ensure_mat(ti["texture"])
    _ensure_mat(SKYBOX)

    node_id = FIRST_NODE_ID
    node_texts: list[str] = []
    brush_parent: dict[int, int] = {}
    mover_offsets: dict[int, tuple[float, float, float]] = {}

    plat_nodes, plat_parents, plat_offsets, node_id = _build_plat_movers(entities, out_dir, node_id)
    node_texts.extend(plat_nodes)
    brush_parent.update(plat_parents)
    mover_offsets.update(plat_offsets)

    door_nodes, door_parents, door_offsets, door_targetname_targets, node_id = _build_door_movers_with_targets(entities, out_dir, node_id)
    node_texts.extend(door_nodes)
    brush_parent.update(door_parents)
    mover_offsets.update(door_offsets)

    button_nodes, node_id = _build_button_triggers(entities, out_dir, door_targetname_targets, node_id)
    node_texts.extend(button_nodes)

    exit_nodes, node_id = _build_level_end(entities, out_dir, node_id)
    node_texts.extend(exit_nodes)

    emap_brushes: list[tuple[int, list, list]] = []

    for brush_idx, br in enumerate(brushes_rows):
        contents = int(br["contents"])
        if not (contents & (CONTENTS_SOLID | CONTENTS_DETAIL)):
            continue

        first_side = int(br["first_side"])
        num_sides  = int(br["num_sides"])
        sides = brush_sides_rows[first_side: first_side + num_sides]

        if len(sides) < 4:
            continue

        brush_planes = [bsp_planes[int(s["plane_num"])] for s in sides]
        polys = _compute_polys(brush_planes)

        brush_pts: list[tuple[float, float, float]] = []
        brush_faces: list[tuple[int, list[int], list[tuple[float, float]]]] = []

        for side_idx, side in enumerate(sides):
            poly = polys[side_idx]
            if len(poly) < 3:
                continue

            ti_idx = int(side["texinfo"])
            if ti_idx < 0 or ti_idx >= len(texinfo_rows):
                continue

            ti = texinfo_rows[ti_idx]
            texture = ti["texture"]

            if _should_skip(texture):
                continue
            if _is_sky(texture):
                texture = SKYBOX

            mat_id = _ensure_mat(texture)
            poly_pts: list[int] = []
            poly_uvs: list[tuple[float, float]] = []

            for v in reversed(poly):
                idx = len(brush_pts)
                brush_pts.append((v.x * SCALE, v.z * SCALE, v.y * SCALE))
                poly_pts.append(idx)
                poly_uvs.append(_compute_uv(v, ti))

            if len(poly_pts) <= MAX_FACE_PTS:
                brush_faces.append((mat_id, poly_pts, poly_uvs))
            else:
                # Fan-triangulate oversized faces instead of dropping the brush.
                for t in range(1, len(poly_pts) - 1):
                    brush_faces.append((
                        mat_id,
                        [poly_pts[0], poly_pts[t], poly_pts[t + 1]],
                        [poly_uvs[0], poly_uvs[t], poly_uvs[t + 1]],
                    ))

        if brush_faces:
            emap_brushes.append((brush_parent.get(brush_idx, -1), brush_pts, brush_faces))

    player = _select_player_start(entities)
    if player:
        text = (_NODE_TEMPLATES["player"]
                .replace("%POS%", _fmt_pos(player["origin"]))
                .replace("%ROT%", _player_rotation(player))
                .replace("%ID%", str(node_id)))
        node_texts.append(text)
        node_id += 1

    for classname, node_key in _ENTITY_MAP.items():
        for ent in entities.get(classname, []):
            origin = ent.get("origin")
            if not origin:
                continue
            pos = _fmt_pos(origin)
            text = (_NODE_TEMPLATES[node_key]
                    .replace("%POS%", pos)
                    .replace("%ID%", str(node_id)))
            node_texts.append(text)
            node_id += 1

    emap_path.parent.mkdir(parents=True, exist_ok=True)
    with emap_path.open("w", encoding="utf-8", newline="") as fw:
        fw.write(_HEADER)
        for mat in materials:
            fw.write(mat + "\r\n")
        fw.write("}\r\n")

        fw.write("Brushes{\r\n")
        for parent, brush_pts, brush_faces in emap_brushes:
            fw.write("Brush{\r\n")
            fw.write(f"parent={parent}\r\n")
            fw.write("layer=-1\r\n")
            offset = mover_offsets.get(parent, (0, 0, 0))
            fw.write("pos=" + ",".join(str(v) for v in offset) + "\r\n")
            fw.write("points=" + ";".join(f"{x},{y},{z}" for x, y, z in brush_pts) + "\r\n")
            for mat_id, face_pts, face_uvs in brush_faces:
                surf = _SURF_TEMPLATE.replace("%MAT%", str(mat_id))
                fw.write("Face{\r\n")
                fw.write(surf)
                fw.write("points=" + ";".join(str(i) for i in face_pts) + "\r\n")
                fw.write("uvs=" + ";".join(f"{u},{v}" for u, v in face_uvs) + "\r\n")
                fw.write("}\r\n")
            fw.write("}\r\n")
        fw.write("}\r\n")

        fw.write("Nodes{\r\n")
        for text in node_texts:
            fw.write(text)
        fw.write("}\r\n")

    print(f"  wrote {emap_path} ({len(emap_brushes)} brushes, {len(node_texts)} nodes)")


def main() -> None:
    out_root = Path(__file__).parent / "output"
    out_dirs = sorted(d for d in out_root.iterdir() if d.is_dir())
    if not out_dirs:
        print("no output directories found — run step3 first")
        return

    EMAP_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in out_dirs:
        if not (out_dir / "planes.csv").exists():
            continue
        emap_path = EMAP_DIR / f"{out_dir.name}.emap"
        print(f"converting {out_dir.name} ...")
        convert_to_emap(out_dir, emap_path)

    print("all done.")


if __name__ == "__main__":
    main()
