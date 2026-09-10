# Lift debugging

The user confirmed that the cube in their Prodeus `Default.emap` rises when
entering the left trigger. `input/lift_debug_reference.emap` preserves that
editor save. This confirmed activation and endpoint placement; animated travel
and player carrying were not established by that cube test. It provides the
brush, mover, trigger, lighting, and player serialization used by the experiment.

## Current experiment: base2 *50

Open `q2_debug_base2_lift_v2` in the Prodeus editor and start play mode.
The map title is **Q2 Debug - base2 lift (SetDestEnd)**.

The first experiment, `q2_debug_base2_lift`, reached approximately the correct
endpoint, but the user reported almost instantaneous movement and falling off.
Its mover has `moveTime=3`, also preserved in the editor's play-test save.
Shipped Prodeus door prefabs use `SetDestEnd` to command their movers. Version 2
changes only `OnFirstEnter,GoToEnd,7` to `OnFirstEnter,SetDestEnd,7` and the map
title. Geometry, spawn, trigger volume, travel distance, and move time are
identical. The user confirmed that version 2 works perfectly: the lift animates
over the configured time and carries the player to the correct upper position.
This establishes `SetDestEnd` as the working input for the upward lift trip.
`GoToEnd` produced an effectively instantaneous relocation in the first test.

1. Start on the blue landing, facing the lowered lift.
2. Walk forward onto the lift.
3. Check whether all its visible parts rise together and carry the player.
4. It should move upward 6.266667 units in three seconds and stop with the
   walking surface at the height of the green upper landing.

Restart play mode to repeat. Automatic return is deliberately absent from
this experiment. The next runtime checks are return motion, waiting while
occupied, and activation on a second trip. The confirmed upward setup should
be extended with that behavior after those tests pass.

## Normal exporter integration

Step 4 now incorporates the confirmed upward-motion setup for ordinary
`func_plat` entities: a lowered initial brush/mover position, positive Y travel,
`startOn=False`, `repeat=False`, and a player trigger sending `SetDestEnd`.
Brush points and UVs stay unchanged; the saved brush position supplies the
initial world offset. Trigger bounds follow Q2's `plat_spawn_inside_trigger`,
including low-trigger flags and narrow-platform fallbacks.

Full exports use `travel / speed` timing with linear movement, so the `base2`
lift is configured for 0.94 seconds rather than the experiment's slow three
seconds. Q2 acceleration and deceleration are not reproduced yet. The isolated
version 2 runtime result establishes the movement action and player carrying;
the full-map trigger placement and timing still need an in-game check.

Lifts with `targetname` remain stationary at their authored upper position;
the exporter reports that external trigger conversion is missing. Automatic
return, repeated trips, doors, and buttons are not implemented. Regenerating
the normal maps now includes the basic lift ascent, not full Q2 game logic.

## Rebuilding

```powershell
python debug_lift.py
```

The generator reads `output/base2`, runs the current converter into a temporary
file, extracts its 16 visible lift brushes, and creates a small test map in the
configured Prodeus Maps folder. It uses `OnFirstEnter,SetDestEnd,7` by default.
The configured move time is three seconds to make observation easier; this
is not a reproduction of Quake 2 acceleration. Use `--action GoToEnd` with a
different output path to reproduce the first experiment's trigger action.

Existing destination files are preserved. For a new iteration use:

```powershell
python debug_lift.py --output "C:/Users/Anwender/AppData/LocalLow/BoundingBoxSoftware/Prodeus/LocalData/Maps/q2_debug_base2_lift_v3.emap"
```

## Door experiment: base1 *19

`python debug_door.py` now creates `q2_debug_base1_door_v3`, using the automatic
door near the exit elevator. It includes a floor, a straight player approach,
and the generated trigger connected to the correct mover. The old v2 fixture
used a different door and had a dangling event target.

See [the door debugging notes](door_debug.md) for the node-ID-zero import
failure, exporter fix, and full-map reproduction.

## Established facts

- `base2` has one `func_plat`, inline model `*50`, with `lip=132`.
- Its full model Z extent is 320 Quake 2 units; travel is 320 - 132 = 188,
  or 6.266667 Prodeus units at the converter's 1/30 scale.
- Seventeen BSP brushes belong to the model. Sixteen visible brushes are
  emitted, and the invisible clip brush contributes to the full model height.
- Its walking surface is authored at Q2 Z=0. The experiment places it at
  Prodeus Y=-6.266667 initially, then raises it to Y=0.
- `OnFirstEnter,SetDestEnd,7` with `moveTime=3` animates the lift and carries the
  player correctly, as confirmed by the user in the version 2 runtime test.
- The production converter emits the triggered upward trip for ordinary lifts.
  Doors and buttons have no movement conversion yet.

The test adds an inset trigger and two landing levels around the isolated lift.
It does not yet reproduce Quake 2's complete trigger volume, return timer,
acceleration, blocking behavior, or target-controlled platforms. Existing
converted maps pick up the integration when step 4 is run again.
