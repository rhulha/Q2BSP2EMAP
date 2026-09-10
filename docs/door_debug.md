# Base1 exit-area door

The automatic upward door (`func_door *19`) was exported as mover ID 0.
Widening its trigger did not fix its broken object references. The existing
Prodeus play-test save, `base1.emap_qp`, demonstrates both failures:

| Connection | Export | Prodeus play-test save |
| --- | --- | --- |
| Door mover | `id=0` | `id=1697` |
| Door slab | `parent=0` | Still `parent=0`, with no matching node |
| Door trigger | `OnFirstEnter,SetDestEnd,0` | `targetStructs` removed |
| Other door movers | IDs 1, 2, 3 | Parents and targets remapped correctly |

Step 4 now starts node IDs at 1. It keeps the 60-Q2-unit horizontal trigger
expansion and the confirmed `SetDestEnd` action. The door moves upward 120 Q2
units (4 Prodeus units) in 1.2 seconds. The base1 regression verifies the real
door slab, reachable trigger, unique positive node IDs, and valid references.

Regenerate just base1 with:

```powershell
python -c "from pathlib import Path; import step4_output_to_emap as c; c.convert_to_emap(Path('output/base1'), c.EMAP_DIR / 'base1.emap')"
```

Reopen the generated `base1.emap` in the editor before starting play mode.
An already loaded map or an old `_qp` save contains the previous connections.

For a short walk directly toward the same door, run `python debug_door.py`
and open `q2_debug_base1_door_v3`. This fixture uses the generated door and
trigger, adds a stationary floor, and puts the player on a straight approach.
It preserves existing test maps. Restart play mode to repeat the test; automatic
door closing is not implemented.

The old v2 fixture tested a different, button-controlled door (`*31`). It
renumbered that mover to 7 while leaving its trigger pointed at nonexistent
node 1, omitted a floor, and placed the player off the trigger's approach.
Its failed test therefore did not establish a problem with `SetDestEnd`.
