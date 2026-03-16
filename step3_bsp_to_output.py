from __future__ import annotations

import configparser
import csv
import json
from pathlib import Path

from bsp.brushes import read_brush_sides, read_brushes
from bsp.edges import read_edges, read_face_edges
from bsp.entities import read_entities
from bsp.faces import read_faces
from bsp.leafs import read_leaf_brushes, read_leaf_faces, read_leafs
from bsp.lightmaps import write_lightmaps_bin
from bsp.models import read_models
from bsp.nodes import read_nodes
from bsp.planes import read_planes
from bsp.reader import load_bsp
from bsp.texinfo import read_texinfo
from bsp.vertices import read_vertices
from bsp.visibility import write_visibility_csv

_conf = configparser.ConfigParser()
_conf.read(Path(__file__).parent / "conf.ini")
BASE_DIR = Path(_conf["paths"]["base_dir"])


def write_json(out_dir: Path, filename: str, obj) -> None:
    target = out_dir / filename
    with target.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    print(f"  wrote {target.name}")


def write_csv(out_dir: Path, filename: str, rows: list[dict]) -> None:
    target = out_dir / filename
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {target.name}")


def _load_texture_extensions(textures_file: Path) -> dict[str, str]:
    ext_map: dict[str, str] = {}
    if not textures_file.exists():
        return ext_map
    with textures_file.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            key = p.with_suffix("").as_posix()
            ext_map[key] = p.suffix
    return ext_map


def _apply_texture_extensions(texinfos: list[dict], ext_map: dict[str, str]) -> list[dict]:
    for t in texinfos:
        name: str = t["texture"]
        key = name.removeprefix("textures/")
        if key in ext_map:
            t["texture"] = name + ext_map[key]
    return texinfos


def convert_bsp(bsp_path: Path, out_dir: Path, ext_map: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"parsing {bsp_path} ...")
    lumps = load_bsp(bsp_path)

    texinfos = _apply_texture_extensions(read_texinfo(lumps), ext_map)
    texinfo_rows = [
        {
            "ux": t["u_axis"][0], "uy": t["u_axis"][1], "uz": t["u_axis"][2],
            "u_offset": t["u_offset"],
            "vx": t["v_axis"][0], "vy": t["v_axis"][1], "vz": t["v_axis"][2],
            "v_offset": t["v_offset"],
            "flags": t["flags"], "value": t["value"],
            "texture": t["texture"], "next_texinfo": t["next_texinfo"],
        }
        for t in texinfos
    ]
    write_csv(out_dir, "texinfo.csv", texinfo_rows)

    write_json(out_dir, "entities.json", read_entities(lumps))
    write_json(out_dir, "faces.json", read_faces(lumps))
    write_json(out_dir, "leaf_faces.json", read_leaf_faces(lumps))
    write_json(out_dir, "leaf_brushes.json", read_leaf_brushes(lumps))
    write_json(out_dir, "face_edges.json", read_face_edges(lumps))

    node_rows = [
        {
            "plane_num": n["plane_num"],
            "child0": n["children"][0], "child1": n["children"][1],
            "min_x": n["mins"][0], "min_y": n["mins"][1], "min_z": n["mins"][2],
            "max_x": n["maxs"][0], "max_y": n["maxs"][1], "max_z": n["maxs"][2],
            "first_face": n["first_face"], "num_faces": n["num_faces"],
        }
        for n in read_nodes(lumps)
    ]
    write_csv(out_dir, "nodes.csv", node_rows)

    write_visibility_csv(out_dir, lumps)

    model_rows = [
        {
            "min_x": m["mins"][0], "min_y": m["mins"][1], "min_z": m["mins"][2],
            "max_x": m["maxs"][0], "max_y": m["maxs"][1], "max_z": m["maxs"][2],
            "origin_x": m["origin"][0], "origin_y": m["origin"][1], "origin_z": m["origin"][2],
            "headnode": m["headnode"],
            "first_face": m["first_face"], "num_faces": m["num_faces"],
        }
        for m in read_models(lumps)
    ]
    write_csv(out_dir, "models.csv", model_rows)

    leaf_rows = [
        {
            "contents": l["contents"], "cluster": l["cluster"], "area": l["area"],
            "min_x": l["mins"][0], "min_y": l["mins"][1], "min_z": l["mins"][2],
            "max_x": l["maxs"][0], "max_y": l["maxs"][1], "max_z": l["maxs"][2],
            "first_leaf_face": l["first_leaf_face"], "num_leaf_faces": l["num_leaf_faces"],
            "first_leaf_brush": l["first_leaf_brush"], "num_leaf_brushes": l["num_leaf_brushes"],
        }
        for l in read_leafs(lumps)
    ]
    write_csv(out_dir, "leafs.csv", leaf_rows)

    plane_rows = [
        {"nx": p["normal"][0], "ny": p["normal"][1], "nz": p["normal"][2], "distance": p["dist"], "type": p["type"]}
        for p in read_planes(lumps)
    ]
    write_csv(out_dir, "planes.csv", plane_rows)

    write_csv(out_dir, "brushes.csv", read_brushes(lumps))
    write_csv(out_dir, "brush_sides.csv", read_brush_sides(lumps))

    edge_rows = read_edges(lumps)
    if edge_rows:
        write_csv(out_dir, "edges.csv", edge_rows)

    vertex_rows = read_vertices(lumps)
    if vertex_rows:
        write_csv(out_dir, "vertices.csv", vertex_rows)

    write_lightmaps_bin(out_dir, lumps)
    print(f"  done -> {out_dir}")


def main() -> None:
    maps_dir = BASE_DIR / "maps"
    bsp_files = sorted(maps_dir.glob("*.bsp"))
    if not bsp_files:
        print(f"no .bsp files found in {maps_dir}")
        return

    print(f"found {len(bsp_files)} BSP file(s) in {maps_dir}:")
    for p in bsp_files:
        print(f"  {p.name}")
    print()

    out_root = Path(__file__).parent / "output"
    textures_file = Path(__file__).parent / "input" / "textures.txt"
    ext_map = _load_texture_extensions(textures_file)

    for bsp_path in bsp_files:
        out_dir = out_root / bsp_path.stem
        convert_bsp(bsp_path, out_dir, ext_map)

    print("all done.")


if __name__ == "__main__":
    main()
