# macros/travel.py — measures behind the tuned numbers

Moved out of the code comments in phase 4 of the cleanup (2026-10-19). Git keeps the full wording.

## Casting delay (DELAY_SHOWN, DELAY_STALE, the clock rule)

- State 185 (`Player.cooldown`) is set at the cast's action frame and cleared when the delay is over. Blade Warp,
  four takes of 21:42 on 2026-10-13, 123 keys from the key's down: set after 0.17–0.24 s (p10–p90; p99 0.35, max
  0.40), cleared after 0.96–1.03 s (p50 1.00; p99 1.09 in a clean take, 1.17 with the recorder starved).
- A key before the clear is refused: 36 of 46 keys 0.8–1.0 s after the one before (2026-10-11 to 13).
- With no state read the delay is timed from the key's **release** (2 refused of 296 keys); timed from the key's
  down, 1.05 s is under the clear's p99 and would refuse some.
- PLAN_AHEAD: the look and choice take 130–150 ms in a clean game, 500–770 ms under load
  (rca/2026-10-13/latency-findings.md §2.2).
- NEAR_AIM: a landing is off its aim by 1.0 units at the median, 2.6 at p90.
- `press_skill` already waits for the character: a separate wait cost 0.39 s median decision-to-key (2026-10-11).
- Re-aim from where the character is at the key: held-key scenes, seed 11, took a walk's 2.3 units for the landing.

## Staff charges (LOW_CHARGES, HOP_FROM, LOOPED, LOOPED_TELEPORT)

- LOW_CHARGES (user, 2026-10-11): a staff of 69 came to 2 clearing a level after Nihlathak (15:10); some 20 are
  needed to reach him.
- KP_6 loop, 2026-10-17 (the player: "it looks like we're constantly low on tp charges"): with charges 282 chests
  an hour of cycles, without 258, but ~7 charges a cycle (~11,900 gold) for ~4 s, more than the sales bring; most
  on the last short hop to a chest. At 13:36: with 3.3 casts a stay the chests leg was 27.3 s against 27.7 with
  none; the sessions to pay for them cost ~12.7 s a cycle (221 chests/h against 279). The player chose "No TP,
  high-value trade only" → HOP_FROM = inf. At 15:24 the player allowed Teleport again while gold is high
  (LOOPED_TELEPORT, macros/loop.py `teleports`).
- LOOP_SHORT: a Teleport aimed onto a chest's own spot was not cast ("nothing 0.6s after the key, no charge
  spent", 19:56:40.4 on 2026-10-16, at (4427.0, 3012.0)).

## Walked ways

- `Walked`: 13:05 on 2026-10-13, a seal 286 units off in a straight line and 318 by the walked way, which led north
  out of the wing while every straight move went west into its pocket.
- `around_of`: Drifter Cavern, 09:43 on 2026-10-12, staff empty, the firing spot 26 units behind a wall; thirteen
  presses ended with "no Blade Warp or walk leads".
- `planning` / `Fields`: Plains of Despair, 23:48 on 2026-10-14: a field regrown at every room read, 74,725 cells
  and 0.43 s of CPU each time; one look took 5.1 s under load with the strike and the drinker waiting
  (rca/2026-10-14/run-2040-findings.md §1.2.2).
- `landing_in_reach`: replayed on 152 Blade Warps toward goals over 30 units away (games of 22:50 on 2026-10-16):
  24.0 units of the way per hop against the descent's 20.8, and 22.0 as made then. Settled cells only: at 00:13
  on 2026-10-17 growing there raised `Unplanned` every look ("the chests again and again").
- `way_leg` end on the way's own line: the arena's Icy Cellar door, an off-line cell 4 units from it with no walk
  there and no jump that short.
- WALK_LEG: game of 22:32 on 2026-10-14, 37 walk legs 1.65 s apart at the median (8 units median leg); Icy
  Cellar's six walks of 15 at 22:54:59–55:08.7 took 9.7 s; Blade Warps key to key 1.065 s median (265 legs,
  22 units). A warp of 26 saves 26 units in 1.05 s against a walk's 16 in 1.6 s.

## Clicks and opens

- HURRY: live, click to character seen going under 0.1 s (a free walk's leg 0.25–0.29 s p10–p90, aim + hover +
  press ~0.2 s); arena 0.11 s. A step decided in a cast left 0.67 s after the decision at 15:19
  (rca/2026-10-14/diablo-handling.md fix 3).
- `cut`: 22:54:40.78 on 2026-10-14 the player's mouse cut a Blade Warp at its aim and the next 15 s were walked
  (rca/2026-10-14/run-1932-findings.md §1.2.4).
- ROUND_CLICK: a drop round a wall corner 18.3 units off, 19.4 by walking, took four clicks never walked (Chaos
  Sanctuary, 15:18:31–35 on 2026-10-14, run-1214-findings.md §3.2); the 00:25 game's 13 unmoved clicks were 18.1
  off. Inferred from those two cases.
- `walked_length`: a drop 26 units off across lava was 226 by walking (River of Flame, 22:36:09 on 2026-10-14).
  `walk_reaches`: one 17 off across lava was 43 by walking (00:26:36, run-0025-findings.md §2.2).
- ROUND_OPEN: a shack chest clicked from 12 off outside its wall was walked round 43–55 units, the open's 1.5 s
  ran out and the leg lost 7–8 s (19:54:36 and 20:03:47 on 2026-10-17). Of 933 opens in Lower Kurast 17:43–20:08
  the rule refuses none of the 896 that opened (corners clipped: 7.5–11.7 by walking, 1.12× the line at most) and
  all 34 across a wall (rca/2026-10-17/slow-legs-findings.md §5).
