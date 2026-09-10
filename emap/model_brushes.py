"""Walks a BSP model's node tree down to its leaves to collect brush indices."""
from __future__ import annotations


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
