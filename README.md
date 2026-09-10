# BSPParserPythonQ2

Converts Quake 2 maps (`.bsp`) into Prodeus `.emap` files, including material setup from neural-upscaled textures.

## Pipeline

Run the steps in order:

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `step1_q2unpacker.py` | Extracts `.bsp` and texture files from Q2 `.pak` archives |
| 2 | `step2_gen_materials.py` | Copies neural-upscale PNGs into the Prodeus Materials folder and writes `.mat` sidecars |
| 3 | `step3_bsp_to_output.py` | Parses a BSP file and writes CSVs / JSON to `output/<mapname>/` |
| 4 | `step4_output_to_emap.py` | Reads the CSV/JSON output and produces a Prodeus `.emap` file |

## Movement support

The normal step 4 exporter now handles the first upward trip of ordinary
`func_plat` lifts: they start lowered, activate when the player enters their
trigger, and animate upward using `SetDestEnd`. The isolated `base2` lift was
confirmed in-game to move correctly and carry the player. The full-map export
uses Quake 2's trigger bounds and `distance / speed` timing; acceleration is
not reproduced yet.

Automatic return and repeated trips are unfinished. Lifts with a `targetname`
remain at the top awaiting external trigger support. Ordinary sliding
`func_door` entities without a `targetname` now export as touch-triggered
movers, including teamed double doors opening together. Buttons that directly
target named sliding doors activate them through a player touch trigger.
Rotating doors and more complex target chains still need conversion logic, so
full single-player progression is not supported yet.

Exported node IDs start at 1. Prodeus loses event targets and brush parenting
to node 0 during import, which previously disconnected base1's first automatic
door near the exit elevator. 
See [the door debugging notes](docs/door_debug.md).

If the BSP data and materials have already been exported, run just
`python step4_output_to_emap.py` to regenerate the maps with the lift change.
See [the lift debugging notes](docs/lift_debug.md) for the repeatable test.

## Configuration

All paths are set in `conf.ini`:

```ini
[paths]
pak_dir           = C:/Action/id/q2unpacked
base_dir          = C:/Action/id/q2unpacked
emap_dir          = <Prodeus LocalData/Maps folder>
neural_upscale_dir = <quake2-neural-upscale/textures folder>
materials_dir     = <Prodeus StreamingAssets/Materials folder>
```

## Requirements

- Python 3.12+
- [Quake 2 neural-upscale textures](https://github.com/Calinou/quake2-neural-upscale) (for `step2_gen_materials.py`)
- Prodeus (Steam)

## Coordinate system

Quake 2 is Z-up (right-handed). Prodeus/Unity is Y-up. The converter swaps Y↔Z on all output positions and reverses polygon winding order to compensate for the resulting handedness flip.
