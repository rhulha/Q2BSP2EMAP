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


def _parse_axis(s: str) -> tuple[float, float, float]:
    parts = s.strip("[] ").split(",")
    return float(parts[0]), float(parts[1]), float(parts[2])


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
    ux, uy, uz = _parse_axis(ti["u_axis"])
    vx, vy, vz = _parse_axis(ti["v_axis"])
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
    "info_player_start":      "player",
    "info_player_deathmatch": "player",
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

    emap_brushes: list[tuple[list, list]] = []

    for br in brushes_rows:
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

        if any(len(p) > MAX_FACE_PTS for p in polys):
            continue

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
            face_pts: list[int] = []
            face_uvs: list[tuple[float, float]] = []

            for v in poly:
                idx = len(brush_pts)
                brush_pts.append((v.x * SCALE, v.z * SCALE, v.y * SCALE))
                face_pts.append(idx)
                face_uvs.append(_compute_uv(v, ti))

            brush_faces.append((mat_id, face_pts, face_uvs))

        if brush_faces:
            emap_brushes.append((brush_pts, brush_faces))

    node_id = 0
    node_texts: list[str] = []

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
        for brush_pts, brush_faces in emap_brushes:
            fw.write("Brush{\r\n")
            fw.write("parent=-1\r\n")
            fw.write("layer=-1\r\n")
            fw.write("pos=0,0,0\r\n")
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

    print(f"  wrote {emap_path} ({len(emap_brushes)} brushes, {node_id} nodes)")


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
