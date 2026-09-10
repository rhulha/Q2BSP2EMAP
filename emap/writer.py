"""Assembles one .emap file: brushes rebuilt from BSP planes, plus movers,
triggers, the level exit and the entity nodes."""
from __future__ import annotations

from pathlib import Path

from .config import CONTENTS_DETAIL, CONTENTS_SOLID, FIRST_NODE_ID, MAX_FACE_PTS, SCALE, SKYBOX
from .coords import _fmt_pos, _player_rotation, _select_player_start
from .geometry import _Plane, _compute_polys
from .io_utils import _load_csv, _load_json
from .level_end import _build_level_end
from .movers_door import _build_button_triggers, _build_door_movers_with_targets
from .movers_plat import _build_plat_movers
from .templates import _ENTITY_MAP, _HEADER, _NODE_TEMPLATES, _SURF_TEMPLATE
from .textures import _compute_uv, _is_sky, _should_skip


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
