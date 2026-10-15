# The Lower Kurast loop: KP_6 runs games until toggled off (plan, 2026-10-15)

**Goal** (the player, 2026-10-15): one key, KP_6, toggles a closed loop:
create game → Pandemonium Fortress → prebuff → waypoint to Lower Kurast → each super chest: go, open, pick up →
no chest left → Town Portal (`x`, the key detected, not assumed) → Kurast Docks → waypoint to Pandemonium Fortress →
Save and Exit → again.

The chest part is `lower-kurast-plan.md` (tasks 1–5); this plan is the legs around it and the loop itself.

## What exists (code at `cb555a8`)

| Leg | Exists | Where |
| --- | --- | --- |
| Lobby → next game, prebuff | yes (the macro request, Mod+X), mouse mode only | `routines.py` `create_next_game`, `prebuff`, `run_macro` |
| Save and Exit | yes, mouse mode only | `routines.py` `leave_game` |
| A level run in Lower Kurast | the run mode exists; the chest marks do not (pending) | `pursuit.py`, `lower-kurast-plan.md` |
| Walk in town | no: the hunter and the pursuit refuse in town (`hunt.py:2005`, `2048`); towns have no level handler | — |
| Waypoint panel | its open flag only (`layout.py PANEL_FLAGS['waypoint']` 0x13); no tab or row clicks | — |
| Town Portal | no | — |
| KP_6 | not bound (`compositor.py BINDS`: KP_1–5) | — |

Facts read for this plan (d2data, 2026-10-15): skill 220 Book of Townportal (219 the scroll); object 59
`TownPortal`; waypoints 237 `WaypointAct3` (Kurast Docks, Lower Kurast), 398 `WaypointAct4Town`.

## Phases

### 0. Evidence first (no code that clicks)

- **The portal key.** `skills.skill_keys` with skill 220: the slot table holds the tome when it is on a skill key.
  Log `Macro: loop: Town Portal is on <key>` at the loop's start; refuse to start when it is on none (say which
  key action to bind). Confirm `x` on the player's key file before any cast.
- **Waypoint spots.** Pandemonium Fortress and Kurast Docks are fixed presets: the waypoint objects' spots from the
  DS1 files (`levels/build_objects.py`, add 237 and 398 to the wanted set) and a town handler for each (`levels/
  handlers/towns.py`: the waypoint mark only).
- **The waypoint panel.** Which pixels are the act tabs and the rows, at the player's resolution: from one
  screenshot of the open panel per act (the player takes them; nothing is clicked). The open act and the
  highlighted row are read from memory if `world.py`'s waypoint bytes near 0xC8 hold them (not yet checked live);
  otherwise the click is confirmed by the area changing.
- **Where a new game starts.** Logs since 2026-10-06: the first area of each game against the last area of the
  game before (`probe.log` `Level guide:` lines). This says whether the trip back to act 4 is needed (Open, Q1).

### 1. Town walking

- `macros/town.py`: `walk_to(run, mark)`: the navigator over the town's ground (`travel.py`, walking only: no
  Teleport or Blade Warp in town), clicks within the view toward the mark, done within USE_NEAR. The game's own
  walk-to-click is the step; no pathing beyond the navigator's.
- Tests: a fixture of each town's rooms (one Win+C dump of each, the player standing at the start); the walk from
  the start to the waypoint in the arena's terms (offline ground).

### 2. Waypoint travel

- `macros/waypoint.py`: `travel(run, to_area)`: walk to the town's waypoint (phase 1), click it (`use_thing`
  with a `Use` for 237/398 whose `took` is the panel open), click the act tab, click the level's row, wait for
  the area. Mouse mode only, refused in controller mode as Save and Exit is.
- A waypoint the character has not got (greyed row) or a panel that does not open: `Abort` with its reason.
- Tests: the panel's clicks against a fake world whose area changes on the right row.

### 3. Town Portal

- `macros/portal.py`: `to_town(run)`: the tome's key (phase 0), the cast, the portal object (59) that appears
  beside the character (its owner: the character, if the unit says so), clicked with the object aims, done when
  the area is a town. No tome charges left (`Abort`, "no Town Portal charges").
- Tests: the key from a key file with 220 on a slot; the portal click on a fake world.

### 4. The loop

- `macros/loop.py`: a state machine read from where the character is, so it resumes from any point:

  | Where | Does |
  | --- | --- |
  | lobby | `create_next_game` |
  | Pandemonium Fortress, game fresh | `prebuff`, then `waypoint.travel(LOWER_KURAST)` |
  | Lower Kurast, chests left | the level run (`lower-kurast-plan.md`), pickups as the pickup rules have them |
  | Lower Kurast, chests done and the ground clean | `portal.to_town` |
  | Kurast Docks | `waypoint.travel(PANDEMONIUM_FORTRESS)` |
  | Pandemonium Fortress, the run done | `leave_game` |

- **KP_6** (`KP_Right`, `compositor.py BINDS` → kind `loop`): on starts the loop, off ends it at once (the run is
  cancelled; the character stays where it is). The HUD shows "Loop: game N, <state>".
- **It stops by itself, saying why** (the character left where it is; `Macro: loop stopped: <why>`):
  a stage that `Abort`s; the character dead; life below the safety's leave line (the existing harm model,
  `combat/harm.py`); a valuable that does not fit (the "stop near it" ruling); potions below the reserve; the game
  not created; controller mode.
- **The player's hand** pauses it as it pauses a level run, and it goes on by itself after SETTLE seconds
  (the ruling of 2026-10-13).
- Tests: the state machine over a scripted world (every row above, each stop reason); KP_6 on/off.

### 5. Played checks

One game by hand-held stages first (each leg with its own key, the loop off), then the loop for a few games.
RCA after each session as usual: time per game by leg, chests opened, drops left, every stop and its reason.

## Open (for the player)

1. **Why back to act 4?** If a new game starts in the town of the act the character was saved in, ending in
   Kurast Docks would make the next game start there, one waypoint from Lower Kurast: no Town Portal, no second
   waypoint, no act 4. Phase 0 checks this in the logs; is there another reason for act 4 (the prebuff, the
   merc, a vendor)?
2. ~~Lower Kurast's own waypoint~~ Answered (the player, 2026-10-15): "in LK we prefer to use portal because it is
   usually faster way, then a navigating back". After the last chest the loop always casts Town Portal.
3. **Stops**: is the list in phase 4 right? A cap on games or hours?

## Order

LK plan 1–2 (the chests work) → phase 0 → 3 → 1 → 2 → 4 → LK plan 3–5 → 5. Each phase its own commit with its
tests (serial, one run at a time).
