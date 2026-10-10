# Combat viewer

A Godot 4 project that replays recorded Echoing Strike fights ("takes", `inventory_tracking/combat/`)
beside what an attack policy would have cast in the same situation. The monsters walk their recorded
paths in both; only the casts differ. The player's recorded casts are always **orange**, the policy's
always **blue**.

It shows the level in the game's isometric layout (walls, doors, the character, monsters with life
bars, elites, companions, the recorded pointer), the blades of each run in flight with the cast's
line and focal point, the running totals of both runs and their difference, and a list of moments
where the two differ most, to jump to.

## Run it

```
make combat-viz     # export every take to inventory_tracking/runs/combat/viz/ (a few minutes)
make combat-view    # open the viewer
```

One take: `uv run --offline python -m inventory_tracking.combat.viz inventory_tracking/runs/combat/<take>`
(it also refreshes `index.json`). Other policies: `--policies live,yield,free,nearest,slots`.
Elsewhere: `--out <directory>`, then `godot --path combat_viewer -- <directory>` or the viewer's
"Choose folder" button.

The viewer needs Godot 4.4 or later (written for 4.7) and reads only the exported JSON: no Python at
view time. It looks for `../inventory_tracking/runs/combat/viz/index.json` from the project directory.

## Keys

| Key | Does |
| --- | --- |
| Space | play / pause |
| Left, Right | step one tick (with Shift: one second) |
| `[`, `]` | slower, faster (0.25x to 8x) |
| Tab | next policy (Shift+Tab: previous) |
| N, P | next, previous moment (seeks a second before it) |
| L | loop the chosen moment |
| V | side by side / overlaid |
| F | follow the character |
| Home | fit the level in view |
| mouse wheel, drag | zoom, pan (panning stops following) |
| Esc | back to the take list |

## What is on screen

- Side by side: the left view is the recorded run, the right one the policy's. Overlaid: one view with
  both runs' blades, and two life bars over each monster (orange above blue).
- A monster's life bar is its life **in that run's simulation**. The thin grey bar under it is the
  life the game recorded. A monster killed in a run turns into a cross in that run's colour and
  fades; it keeps walking in the other run until it dies there or the recording loses it.
- Elites are pink diamonds. Companions are green. The white cross is where the recorded pointer was.
- A cast draws a line from the caster to its focal point (a ring) while its blades fly; a dashed line
  when its blades touched nothing.
- Walls that stop a blade are light, cells that only block walking are dim. A closed door is a red
  box, an open one a grey outline.
- The numbers: "life per combat second" is the simulator's score (life the blades took, directly and
  through Health Link, per second with a monster in reach); "gain" is the policy's over the recorded
  casts'. "Gate" in the take list says whether the simulator reproduces that take's recorded damage
  well enough to trust the comparison (`combat/plan.md`).

## The exported file

Written by `inventory_tracking/combat/viz.py`, read by `take_data.gd`. This section is the contract
between the two.

Conventions:

- **Ticks** are the simulator's (`Situation` frames): game ticks, 25 a second, from `start` to `end`.
- **Coordinates** are integers in file units: `scale` (10) to a world unit, measured from `origin`
  (world units). World x grows down-right on screen, world y down-left: across = x - y, down = x + y,
  a world unit being 16 x 8 pixels at zoom 1.
- A **track** is a position over time: `{"seen": [[first, last], ...], "k": [tick, x, y, tick, x, y, ...]}`.
  The thing is there during the `seen` spans (inclusive); it stands at the last keyframe at or before
  the tick.
- A **step series** is a value over time, flat: `[tick, value, tick, value, ...]`; the value holds from
  its tick until the next entry.
- **Spans** are `[[first, last], ...]`, inclusive, ascending.

```
{
 "schema": 1,
 "take": "20261010T154051Z-35", "recording": "...", "character": "...", "started_at": "...",
 "area": 35, "area_name": "Catacombs Level 2",
 "rate": 25.0, "start": 1, "end": 8952, "seconds": 358.0, "late_ticks": 50,
 "scale": 10, "origin": [22518, 6513], "bounds": [x0, y0, x1, y1],   // file units, holds everything
 "aspect": 1.8054,                 // the recorded game window, width / height
 "birth_lag": 5,                   // ticks from a cast's start to its blades' first tick
 "blade_life": 38,                 // ticks a blade can live
 "contact_radius": 20,             // file units: a blade this near a monster touches it
 "player": {"seen": ..., "k": ...,         // a track
            "mode": [tick, mode, ...],     // step series of the character's mode
            "run": [[first, last], ...]},  // spans the recorded character was walking or running
 "pointer": track,                 // the ground under the recorded pointer
 "monsters": [{"unit": 123, "txt": 310, "name": "Ghoul", "elite": false,
               "points": 5200,     // life points at full health
               "life0": 1000,      // thousandths of `points` it had when first seen
               "seen": ..., "k": ...,                     // its recorded path while alive
               "recorded": {"death": 4411 | null,         // tick of the recorded kill
                            "life": [tick, thousandths, ...]}}],  // step series from the recorded drops
 "companions": [{"unit": 5, "txt": 359, "name": "...", "seen": ..., "k": ...}],
 "doors": [{"unit": 9, "txt": 47, "x": -90, "y": -20, "r": 45,    // r: half extent, file units
            "seen": spans, "closed": spans}],
 "walls": null | {"x": -540, "y": -1120,   // file units of the first cell's corner
                  "w": 110, "h": 155,      // cells; a cell is one world unit (`scale` file units)
                  "flight": true,          // whether the level map told blades from feet
                  "cells": "<base64 of zlib of w*h bytes, row by row>"},
                  // a byte: 0 not read, 1 floor, 2 blocks walking only, 3 stops a blade
 "recorded": {"kills": 25, "life_taken": 180000, "taken": [tick, total, ...]},  // what the game recorded
 "gate": {"passes": false, "fails": ["damage ratio 0.81"], "damage_ratio": 0.81},
 "runs": [RUN, RUN, ...],          // the first is always "recorded", then one per policy
 "moments": {"live": [MOMENT, ...], "yield": [...]}   // per policy, against the recorded run
}
```

A RUN is one pass of the simulator over the situation:

```
{"name": "recorded" | "live" | "yield" | ...,
 "label": "the player's recorded casts",
 "policy": false,
 "casts": [{"t": 147,              // the blades' first tick (the cast started birth_lag earlier)
            "o": [x, y],           // where the caster stood then
            "f": [x, y],           // the focal point
            "n": 3,                // monsters its blades touched in this run
            "b": [BLADE x 5]}],    // ascending by t
 "life": {"<unit>": [tick, thousandths, ...]},   // step series of simulated life; before its first
                                                 // entry a monster has its life0
 "deaths": {"<unit>": tick},       // simulated deaths
 "taken": [tick, total, ...],      // step series: life points taken so far, every source
 "score": {"placement_per_combat_second": 2854, "placement_points": 205000, "combat_seconds": 71.9,
           "life_taken": 230000, "kills": 32, "casts": 14, "contacts": 61, "blades_walled": 0,
           "gain": 0.359 | null}}  // gain over the recorded run; null for the recorded run
```

A BLADE is `[x0, y0, x1, y1, n, dx, dy, dx, dy, ...]`: at the cast's tick `t` it is at (x0, y0), it
flies straight to reach (x1, y1) at tick `t + n` (the way out; `n` is below 19 when a wall stopped it,
and then nothing follows), and each (dx, dy) after that is its step in the next tick (the way back to
the caster). It is gone after its last position.

A MOMENT is `{"first": 3001, "last": 3075, "kind": "policy_ahead", "label": "live took 50,163 more
life in 3.0 s", "value": 50163.3}`; the list is sorted by `first`. Kinds
(`inventory_tracking/combat/viz_moments.py`):

| Kind | What | `value` |
| --- | --- | --- |
| `policy_ahead` | a 3 second window where the policy took more life than the recorded casts | the difference in life points |
| `recorded_ahead` | the same the other way round | the difference |
| `idle` | the policy cast on monsters at least twice while the player did not cast for 2 seconds or more | those casts |
| `miss` | recorded casts in a row that touched nothing | how many |
| `kill` | an elite dies at least a second apart in the two runs | seconds the policy was earlier (negative: later) |

`index.json` beside the takes: `{"schema": 1, "takes": [{"take", "file", "bytes", "area", "area_name",
"started_at", "seconds", "ticks", "monsters", "recorded_kills", "gate_passes", "runs": {name: score},
"moments": {policy: count}}]}`.

## The scripts

| File | Holds |
| --- | --- |
| `main.gd` | the window: loading, playback, keys, the two map views in step |
| `take_data.gd` | one exported file decoded: tracks, step series, blades |
| `map_view.gd` | one isometric view of the level at a tick, for one run or both |
| `timeline_bar.gd` | the scrub bar with casts, kills and moments |
| `side_panel.gd` | the legend, scores, running totals and the moments list |
| `take_list.gd` | the opening list of takes |
| `palette.gd` | every colour |
| `tests/smoke.gd` | a headless check of the decoder: `godot --headless --path combat_viewer --script res://tests/smoke.gd -- <take.json>` |
| `tests/drive.gd` | the whole viewer driven headless: every listed take opened, every key above pressed (`make combat-view-check`) |

## Checking it

- The exporter: `uv run --offline pytest tests/inventory_tracking/combat/test_viz.py tests/inventory_tracking/combat/test_viz_moments.py -q`.
- The viewer without a person: `make combat-view-check` prints one line of state per key and per take; a
  script error would show as a `SCRIPT ERROR` line.
- A picture without a person: `godot --path combat_viewer -- <take.json> --tick=1040 --policy=live
  --overlay --fit --shot=tmp/combat_viewer/shot.png` opens the window, saves what it shows and quits.
