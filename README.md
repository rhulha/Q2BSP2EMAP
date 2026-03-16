# BSPParserPythonQ2

Converts Quake 2 maps (`.bsp`) into Prodeus `.emap` files, including material setup from neural-upscaled textures.

## Pipeline

Run the steps in order:

| Step | Script | What it does |
|------|--------|--------------|
| 0 | `q2unpacker.py` | Extracts `.bsp` and texture files from Q2 `.pak` archives |
| 1 | `step3_bsp_to_output.py` | Parses a BSP file and writes CSVs / JSON to `output/<mapname>/` |
| 2 | `step2_gen_materials.py` | Copies neural-upscale PNGs into the Prodeus Materials folder and writes `.mat` sidecars |
| 3 | `step4_output_to_emap.py` | Reads the CSV/JSON output and produces a Prodeus `.emap` file |

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
