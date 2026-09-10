"""target_changelevel -> a LevelEnd node plus a touch trigger per exit brush."""
from __future__ import annotations

from pathlib import Path

from .coords import _build_trigger_node, _model_center_size, _parse_origin, _q2_to_emap
from .io_utils import _load_csv
from .templates import _NODE_TEMPLATES

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
