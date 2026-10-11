# Review: context and architecture of the movement work

Reviewed 2026-10-11 against the working tree on `main` (uncommitted). Scope is the attack-mode step, the sweep, jumps, teleport reach, and the room tour: `macros/hunt.py`, `macros/teleport.py`, `macros/view.py`, `macros/tour.py`, `combat/stance.py`, and the stance and explore scenarios. This is a review, not a change.

Two questions: what is left over from the nights this was built, and where a one-off from a single run is doing the job of a structure.

## Context

The behavior is real. A lot of the text around it is the lab notebook, copied into the modules a reader has to load to change one function.

### 1. The session log lives in three places, and the contract at the top of the macro plan is the old one

`inventory_tracking/macros/plan.md` is about 2,100 lines. Its "Current contract (2026-10-10)" still says the pickup step waits out the fight, and that the seek step goes to elites first. The header says that section wins when a later note disagrees. The later notes are the code: the sweep, Blade Warp, the tour, Hex: Purge, untouched monsters. `inventory_tracking/combat/plan.md` has the same shape for path records and `lead`.

The same nights are then retold in the modules:

- `hunt.py` lines 131–237, a hundred lines of constants whose comments are take ids, clock times, and what a run did.
- `combat/stance.py` lines 1–26, including the first rule that `camp` replaced and a scoring variant that was tried and dropped.
- `teleport.py` around `FAR_FAILED` and the corner abort, and `landed_from`'s docstring, which is the story of one false landing.

A constant's comment should say what the number means (`SWEEP_GAIN`: how many times the worth here a place must be). The take, the clock time, and why 1.3 was rejected belong in the plan, once, under a contract that matches the code.

`ENGAGE_UNITS` in `hunt.py` is only assigned (`= SIGHT`) and never read. It is the name of a rule the sweep replaced.

### 2. `Camp.casts` is two fields, so the log line for a stride is wrong

`combat/stance.py` `Camp.casts` is how many casts finish the pack. `hunt.py` `toward` and `take_step` store a skill id in the same field (`casts=skill` for Blade Warp or Teleport). `stand_line` then prints that id as a cast count ("390 casts"). `stride_line` is the one that knows it is a skill. One dataclass is being used as the decision and as the move order, and the decision's fields are what the log trusts.

### 3. The replaced rules are still a second codebase

These exist only to show that the current rule beat the previous one:

- `tests/inventory_tracking/scenarios/stance/first_rule.py` — the straight-walk rule `camp` replaced, plus `export_viz.py` running it as the left-hand viewer track.
- `tests/inventory_tracking/scenarios/explore/nearest_rule.py` — the "nearest room, turn costs tiles" rule `tour` replaced.
- `tests/inventory_tracking/scenarios/stance/fixtures/` — 39 recorded moments, each a few hundred lines, built so those two rules could be scored against each other.

The open-field test and a handful of moments are the regression. The full comparison set, the exporter, and both retired rules are the evidence of a decision that is already written down in the plan. They are what a reader opens when they are looking for the rule that runs.

`tests/inventory_tracking/scenarios/threat/` and `revivers/` are the same kind of weight (`threat_table.json` alone is about 15,000 lines) for a later worth term. Nothing under `inventory_tracking/` imports them. Until that term is in `camp` or `taken`, they are a dataset, not the suite.

### 4. Three walkers, two of them the same click

`walk_to` (`hunt.py`, two clicks, `WALK_SECONDS` each, used by `go` for a firing spot) and `step_walk` (one click, `STEP_WALK_SECONDS`, used by the sweep) are the same act with the retry policy of the night each was written. `jump` and `hop_toward` are the same act again: aim at ground, press a skill, wait for `landed_from`. The comments on `step_walk` and `walk_to` explain the failure of the other.

## Architecture

Each of these is a rule added after one run, stored as a flag or a second function, beside the function it corrects.

### 1. Where to stand and how to get there are different programs

`camp` (`combat/stance.py`) picks a cell by the points the next three seconds would take, and prices a teleport at `HOP_SECONDS` (1.5 s, the staff swap from the Tower run). `Hunter.better_stand` never passes `hop=True`, so that price is unused on the live path. `take_step` then throws the walk away and jumps when the spot is at least `JUMP_LEAST` away and `jump_by` has a skill. The place was chosen as a walk. The character jumps.

`toward` is a third chooser for the same sweep: a point on the line to the nearest hostile, its own three strides, its own view and footing checks, and it writes the skill id into `Camp`. `go` / `firing_target` / `hop_toward` is a fourth, for the wall case, on the room potential.

One move is: a spot, a budget in seconds, and a way there that the chooser and the executor share. The way is a walk, a Blade Warp along a clear line, or a Teleport hop, in that preference, at the seconds each one actually takes. `camp` should see those seconds. `toward` is the case where no cell wins and the pack is still out of reach, which is a fallback inside that choice, not a second `Camp` built by hand.

### 2. The sweep is five clocks and two loops

After a pickup press with hostiles near, the mode may move on its own. That policy is spread over:

- `step` — sets `follow` and `follow_until`, moves nothing
- `follow_on` — when nothing is in reach: `better_stand`, else `toward`, else `go`
- `fight` — every `FOLLOW_CHECK`, `better_stand` again at `SWEEP_GAIN`, and breaks out so `take_step` can run
- `asked_step` — a press during a fight, another `better_stand` at `SWEEP_GAIN`, and it also resets `follow`
- `take_step` — executes, and may end the sweep on `step_fails`

`follow`, `follow_until`, `follow_checked`, `step_fails`, `shunned`, `stepped_at`, and `step_asked_at` are the memory. Ending the sweep is whichever of those a given path remembers to zero. A sweep is one object: active until a deadline, a step budget, the player moves, or two failed steps; each look asks the one chooser from finding 1; the fight loop only notices that a step is pending.

### 3. "This failed, so turn the feature off" is process state

Three session switches sit on the modules, not on the run:

- `teleport.FAR_FAILED` — one miss from the current tile bans the far potential for that destination until 64 other bans clear the set. The far graph depends on where the character stands. The comment in `hop_toward` describes the ban as the design.
- `view.CORNERS` — a one-element list so every `Viewport` sees a write. The first hop aimed beside the skill bar that moves nothing turns corners off for the process, and that check runs before the lost-Teleport-key check.
- `way_for`'s cache — cleared by hand when `CORNERS` flips, because the potentials closed over the old switch.

`Hunter` already keeps this kind of memory for jumps (`jump_failed`) and bad cells (`shunned`), on the hunter, with a timeout. The far hop and the corner aim want the same: a failure at a place, for a while, not a feature flag on the interpreter. Tests replace `FAR_FAILED` with a fresh set per case, so the ban they would need to pin is exactly what the fixture erases.

The near potential (`REACH_TILES`, `hop_in_view`) and the far one (`FAR_TILES`, `hop_between`) are two graphs over the same rooms. `Hunter.frontier` builds only the near one, then `hop_toward` may travel with the far one. The rooms the tour is allowed to stand in and the hops that can reach them are different maps. One potential whose hop length is whatever the window can show from that tile removes `FAR_FAILED` and makes `frontier` and `hop_toward` agree.

### 4. A clear line is implemented three times, and a walk twice

| Question | Copies |
|---|---|
| Does a missile cross this ground? | `policy.clear_line`, `Field.clear` (the docstring names `clear_line`, then repeats it with `1.5` and `0.5` written out), `sight.clear_shot` (grids and doors, the one the hunt uses for a shot) |
| Can the character walk this? | `stance.way` (straight sample), `Field.ways` (cells, corners), `teleport.clear_walk` (a short door approach) |

`Field.clear` can call `clear_line`. `clear_shot` stays the hunt's shot, because it knows doors and the flight layer. `way` is the straight case of `Field.ways`; `toward` and `step_walk` still use the straight one while `camp` uses the cell one, so a spot `camp` would walk around a corner is a spot `toward` refuses.

### 5. Skipping a monster is a type list and a memory, applied at different gates

`hostiles` drops hydras by id and vultures in modes 1 and 8. `untouched` / `untouchable` drops whatever was the line's monster for four casts without losing life, for twenty seconds, and `foes` applies that on top. The fight loop keeps its aim while the unit is still in `world.monsters` (`alive`), then looks it up in `foes`. A bird that takes off, or a monster just marked untouchable, is in one set and not the other.

One filter should answer "is this a foe right now", used both to choose and to keep an aim. The vulture modes are the fast case of the same idea (life will not move); the four-cast memory is the slow case for everything else. Hydras can stay a type exclusion. They never become foes.

### 6. `Hunter` is the rotation, the navigator, and the motor

`Hunter` is about a thousand lines and about twenty-five fields: mark, sigil, engorge, purge, warp, jump distrust, shun list, tour route, vanished remembers, tested casts, weapon-swap failure, the player's pending click, and the sweep clocks. `attack_mode` and `fight` interleave all of them in one loop.

The split that matches the calls already there:

- **Cast rotation** — strike hold, Death Mark, sigil, Engorge, Hex: Purge, resume. It already has its own clocks.
- **Where to stand** — `camp` / the fallback stride, pure, as `LinePolicy` is for where to cast.
- **Travel** — one executor for walk, Blade Warp, and Teleport, shared with the seek step and the door hop.
- **Sweep** — the small state from finding 2, asking the chooser and calling travel.

`tour` is already a pure function. `frontier` should only be "stops from `tour`, costs from the same potential `hop_toward` uses."

## What to do first

1. Rewrite the macro plan's current contract to the sweep, the jump order, the tour, and the foe filter. Cut the module comments back to the numbers. Delete `ENGAGE_UNITS`.
2. Make `Camp` the place and the worth only. Put the skill and the hop on the move the executor takes, and fix `stand_line`.
3. One travel function, and pass its seconds into `camp` so `take_step` does not reverse the choice.
4. Move `FAR_FAILED` and `CORNERS` onto the run, as timeouts at a place. Plan `frontier` with the same potential as the hop.
5. Keep the open-field test and a few moments. The retired rules, the 39-moment export, and the threat and reviver tables wait outside the tree a normal edit has to read, until something in `stance.py` consumes them.
