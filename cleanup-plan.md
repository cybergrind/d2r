# Cleanup plan (2026-10-19)

The player, 2026-10-19: "we need to analyze our code and prepare plan for cleanup: improve architecture ... remove
context noise: dead code, dead comments, make comments terse, remove tests that we dont need ... optimize overall test
suite: speed up tests, better tests".

Evidence: five read-only studies in `rca/2026-10-19/cleanup/` (git-ignored, local):
[loop-and-level-run.md](rca/2026-10-19/cleanup/loop-and-level-run.md),
[town-items-world.md](rca/2026-10-19/cleanup/town-items-world.md),
[other-packages.md](rca/2026-10-19/cleanup/other-packages.md), [tests.md](rca/2026-10-19/cleanup/tests.md),
[pricing.md](rca/2026-10-19/cleanup/pricing.md); raw timings in `durations.txt`. Each item below names its study
(L, T, O, S = tests, P) and its proposal id there.

## Progress

- 2026-10-19 phase 0 done (goldens, `engine.protected`, `cube.open_inventory`, one scope filter `pricing/knowledge/
  scope.py`; 61 pricing reds fixed or skipped, ≈ 15 + 8 item-bank reds known, rca/…/phase0-pricing.md).
- 2026-10-19 phase 1 done but for: `appraisal_service.py` (the running service re-execs it: delete after the player's
  next `make serve`); `spirit_loadout_audit.py` (pinned by frozen artifacts: ruling 2); `JAMELLA_FIRST`,
  `Rulings.drop_junk`, `PARK_JUNK`/`KEEPER_IN_CUBE` off-paths (ruling 1); the switches (once measured). Kept on
  checking: `routes/table.embedded` (its test keeps routes.md in sync), `Travel.jump_by`, the second `HURT_SECONDS`
  (import cycle). Loot-policy shadow gone: every site asks `verdict` (no disagreement in any live log).
- 2026-10-19 phase 2 in part: `no_card_wait` fixture, test_curses hermetic, `slow` marker (routine run 600 → 120 s),
  determinism merged (≈ 28 s), module cache clearing. P9's premise was wrong: the 1.84 GB peak is the appraisal/items
  KB loads (test_base_defense, test_commodity, …), not the arena; it is under the 2 GB measured before, left as is.
  Then: pinned panel pixels (test_cube), one `Memory` fake (tests/inventory_tracking/fake_memory.py, 5 copies out).
  Left: `test_tick_cost` (deliberate time budgets, slow lane), `harm_path` (L, behaviour risk), the ruled rows.
  Pricing (test side only): session caches for `build_profiles.build`/`compile_stat_configurations` (mtime-checked,
  `D2R_PRICING_CACHE=off`), item bank default = 1,927-case stratified subset (`D2R_ITEM_BANK=full` for all; required
  before publishing): default `tests/pricing` ≈ 4.7 h → ≈ 1.1 h (extrapolated from samples).
- 2026-10-19 phase 3:
  - step 1: `macros/stops.py` `first`/`decide` (pure, table test test_stops.py against the old chain); the stand-by
    is typed (`Run.stand_by`, runner `standing`), no warning text read; `classify` logs any stop it still reads by
    its words ("a stop with no cause read as room by its words"): delete `ROOM_WORDS` after a day with none.
  - step 6, first part: kind branches are `Kind` data (`agenda`, `trips`, `swaps_gheeds`, `boss`, `badge`,
    `fortress_ends_game`, `full_clear`) and `LEGS` (each kind's leg chooser); shared `Loop.begin_trip`,
    `back_through_portal`, `note_portal`, `prebuff_once`, runner `_way_on`. Then one `LegHands` (loop.py) replacing the
    runner's eight leg callbacks and `TzHands`: built once a leg by runner `_loop_hands`; the kind picks its level run
    (the agenda's for the TZ kinds), so Andariel's `down` and a zone's `door` are one `way_on`. Skipped on reading:
    P7 `LoopWatch` (`overdue`/`still`/`beset` are ~50 cohesive lines reading `abandon`, `cooling`, the kind and the
    trips; out of `Loop` each call and test would pass them in: churn in the near-death guard for little gain).
  - step 8, part: map data in `levels/map_card.py`, drawing in `hud/map.py`, `hud/direction.py`; one `ARROWS`.
  - step 9, part: one session/date reader in logwords.py (`sessions`, `local`, `newest`), tool outputs byte-identical.
  - step 2 done (`items/grid.py` `Grid`, parity test against every old helper; `room_for`/`inventory_rows` gone).
  - step 5, part: `Run.reads` (engine.py `Reads`): 85 `run.X() if run.X is not None else None` guards gone.
  - step 7, part: `cleared`/`agenda_cleared` share `_forget_passed`, `_on_the_way`, `_clear_through`; the drop
    give-up memory is `macros/drop_ledger.py` `DropLedger` (`Hunter.drops`). Skipped on reading: `LevelMemory` (the
    memories have no common lifetime: each is pruned on its own clock), P5 `RunSpec` (three flags left after the old
    TZ coordinator went; little gain). Then the split: `Hunter` (hunt.py, 1,457 lines) keeps its state, the
    fight and attack mode; its other 79 methods are module functions in `macros/hunting/` (`choice.py` goal,
    `judging.py`, `moves.py`, `sweep.py`; constants and helpers in `base.py`), bound as class attributes
    (`judge = judging.judge`; `self: Hunter`, which pyrefly checks; mixins with `self: Hunter` it rejects). Tests patch
    module names through `fakes.patch_hunt` (each module reads its own import) and import constants from their home.
  - step 3 done: `native/memory.py` is the one /proc/<pid>/mem open (`ProcessMemory`, `BoundedReader`, `bounded`,
    `game_read`, `stable_read`, `one_unit_table`); ~30 opens and ~17 table picks moved onto it; hud/live.py's reader
    is `LiveMemory` (it reads raw and rebinds per pid: kept apart from the macro's). Left: macros/probe.py's two opens,
    the table picks in takes/record.py and levels/guide.py.
  - step 4, first part: world.py (1,998 lines) split as pure moves into `game/`: `layout.py` (addresses,
    offsets, classes), `records.py` (`Player` … `World`, `prized`, `has_room`), `kept.py` (`BeltKept`, `PutDown`),
    `decode.py` (the `read`-taking decoders, the census), `memory.py` (`GameMemory`); 173 importers rewritten, no
    shim. Then one `Monster` record (game/records.py; terror's fields optional on it, `path_at`/`unit_at`) and one
    walk entry (`decode.monster_table`) for the look, terror's tracker and the HUD; the monster flags, `NO_OWNER`
    and `ACTING` defined once in game/layout.py. The per-unit reads stay two on purpose: the look reads owner,
    flags and life every pass, the tracker and HUD only a path (data and stats on first sight). `Point` is defined
    once (levels/geometry.py; 59 copies gone). Kept in game/ on reading: `prized`/`shown_source` (the memory reader
    classifies a drop's source as it reads: in lootpolicy, game would import macros). Left: terror's player readers
    against `local_player` (they pick the unit with the most life; they now share `game.units.walked`).
  - batch A (2026-10-19): the object table walked once a ground look (`shrines_among`, `super_chests_among`); the
    decoders' caches reset in every test (tests/inventory_tracking/conftest.py); `make test` (routine), `test-all`,
    `lint`; the six research notes in `inventory_tracking/history/`; tests take up to 6 workers while D2R.exe is not
    running (routine lane 125 s -> 35 s). Skipped on reading: one world-to-screen projection (`Viewport` is the one
    the macros use; the HUD, the minimap and `arrow` each have their own scale and origin, sharing only
    `(dx - dy, dx + dy)`).
  - step 4, second part: the game package is `inventory_tracking/game/`, below macros (study O A2): combat, terror,
    hud and probes read the game without importing macros. Step 8, second part: `inventory_tracking/takes/` holds
    the recorder and the take readers (record, retain, takes, timeline, hurts, macro_state, legs, analysis,
    viz_moments, the `python -m inventory_tracking.takes` CLI) and their tests; combat/ keeps the decisions. The
    ratchet scans both as framework packages.
  - step 10 done: `pricing/api.py` (47 names, lazy); inventory_tracking imports only it (boundary test
    tests/pricing/test_api.py); `detail`/`guarded_retrieve` moved to `appraisal/retrieval.py`; the replay and guide
    reports run as `python -m inventory_tracking.corpus.replay [--guides]`. Left: two frozen maintenance tools
    (`named_gate.py`, `maintenance/replay.py`) still import appraisal presentation (study A2).

- 2026-10-19 phase 4 (batch B): comments and docstrings of macros, combat, takes, builds, levels, config, game,
  terror, hud, loot, routes, tracking, native, osd made terse by five agents; each file's code checked equal to HEAD's
  but for comments and docstrings (an AST comparison). Prose (comments + docstrings) of inventory_tracking: 32.2 % ->
  24.1 % (3.84 -> 3.42 M characters); macros 40.6 -> 29.0 %, combat 41.3 -> 31.0 %, levels 37.7 -> 24.3 %. What is left is mostly one-line constant and
  field comments and dated rulings. Kept stories went to `<package>/history/<module>.md`; the take format is
  `takes/README.md`. Not in this pass: appraisal/, items/, shop/, identify/, collection/, pricing/, tests/.

- 2026-10-19 batch C (the player's rulings of 2026-10-19): `ROOM_WORDS` gone (no untagged room stop in the logs since
  13:27 or in the code: stops are told by their named cause or type); `appraisal_service.py` deleted; `grow.py` and
  `binja_grow.py` in `inventory_tracking/native/`; the Traderie client is `pricing/knowledge/traderie_client.py`;
  `pricing/` under pyrefly (0 errors; `assessment/maintenance/` excluded until ruling 2), type-level edits only;
  `pricing/api.py` in the validation code. Bugs fixed: safety's shorter approaches read the move's own price when
  fire is on the way (and the offered stand has its own lap); an unreadable gold pile is left out, not the whole
  look; waypoint.py's own panel wait is gone (`use_thing`'s PANEL_GRACE does it: 282 acts, all the same). Unit-type
  constants from game/layout.py; `macros/view.py` is `game/view.py` (takes import no macros). Pricing tests: the
  same 74 red as HEAD (checked on a copy of HEAD). Open: one unreadable belt item still empties a look (ruling).

## Where we are

| | Now |
|---|---|
| `inventory_tracking` tests (serial) | 616–631 s, 7,835 tests; 66 tests take 74 % of it (arena scenarios) |
| `tests/pricing` (serial) | ≈ 4.7 h, 41,824 tests; 76 % is the item bank |
| Red | 5 arena goldens (a new log line, b3757e4); ≈ 250 pricing tests (sampled), incl. the frozen market-sha one |
| Largest files | hunt.py 4,254 (Hunter: 120 methods; 1,457 after step 7), runner.py 2,300, world.py 2,025, travel.py 1,742 |
| Prose share | comments + docstrings ≈ 39 % of characters in the loop area, 29–42 % in combat/levels/config |
| Dead or superseded | the old TZ coordinator (≈ 1,350 + 1,400 test lines), 15 dead pricing modules, town types, hover legacy |
| Disk (git-ignored) | `tmp/` 65 GB, `runs/` 60 GB (`alt-d/` 36 GB, no retention), `pricing/data` 20 GB (16 GB old generations) |

## Rules for every step

- Behaviour does not change unless the step says so; pure moves and deletions first, each its own commit.
- The live loop: each production step is a restart with focused tests, the wide suite, ~30 clean cycles before the next
  (the loop-watch cadence). Steps that touch the same file go in sequence, never in parallel agents.
- Comment cleanup comes after the moves (phase 4), so moved code is not edited twice.
- A full `tests/inventory_tracking` run takes over 10 min: run it in the background, never behind a 600 s call.

## Phase 0 — correctness first (S, now)

1. **Green the tree** (S1). Re-pin the 5 arena goldens if "firing stand jump source" is intended, and make goldens
   compare decision lines only, so a diagnostic line cannot break them again. Fix the 4 sampled pricing failures (P);
   retire the market-sha test pinned to a frozen snapshot.
2. **One guard for every destructive action** (T1). Selling checks "theirs" and "kept by stats", dropping only
   "theirs", parking junk on the ground nothing. One `protected(run, item)` for sell, drop, park and the junk set, and a
   test that fails when an action bypasses it. Adds checks only.
3. **One Traderie scope filter** (P3). Four implementations disagree: `knowledge/market.py` rejects a listing with no
   game version, `tools/pricecheck.py` and `wp_b_buckets.py` keep it, so pricecheck can quote what the KB rejects. Use
   `scope_status` everywhere.
4. **Regression for the cube's inventory key** (S gap): `cube.unpack` taps the key unconditionally (cube.py:449) and
   closes an inventory already open.

## Phase 1 — delete what is verified dead (S each, low risk)

| Item | Lines | Study |
|---|---|---|
| Old TZ coordinator: `routes/tz_leveling.py` (keep `Capability`, `route_inventory` → `tz_routes.py`), `tz_execution.py`, `tz_runtime.py`, `tz_pilot.py`; runner `TZ_*` routines, `tz_start`/`tz_pickup`, service.py's `--tz-active-*`, KP_7, "HUNT TZ" mode | ≈ 1,350 + ≈ 1,400 tests | L P1 |
| Town: `town.Itinerary`, `ShopStop`, `Buy`, `Transmute`, `StashStop.transmutes`/`keys_to`, `shop.MISC_TAB`; `JAMELLA_FIRST=False` + `_stranded` + 3 tests; `Rulings.drop_junk`; off-paths of `PARK_JUNK`/`KEEPER_IN_CUBE` | few hundred | T3 |
| Loot-policy shadow: finished (37 lines, all agreeing): call sites to `verdict()` | — | T3 |
| Loop: `Loop.selling`, `Travel.jump_by`, `routes/table.embedded`, `MOUSE_WORK`, `Player.battle_command`, the duplicate `HURT_SECONDS` | small | L P8 |
| Hover legacy chain: `hover/legacy.py`, `probes/hover_legacy.py`, `hover_probe.py` + test (APPRAISAL.md:314 TODO) | — | O1 |
| Five 7-line wrapper scripts (after `make serve` → `-m inventory_tracking.appraisal serve`) | — | O1 |
| Pricing: 9 `maintenance/zeal_*` templates + `spirit_loadout_audit.py`; the removed paid-property scorer and the field `triage/replay.py` still writes | ≈ 1,600 | P4 |
| Stale docs: tzloop/README/goals-plan say the TZ loop is off; `GameId` docstring; test_loop_incidents "xfail" | — | L |
| Feature switches flipped on 2026-10-18/19 (`tzloop.ENABLED`, `RUSH_THE_BOSS`, `QUIET_BY_THE_BOSS`, town ones): delete each once its trial is measured | — | L |

## Phase 2 — test suite speed (S each)

| Step | Saving | Study |
|---|---|---|
| `CARD_SECONDS = 0` fixture for all of test_runner (6 tests wait a real 4 s; 33 patch it by hand) | ≈ 40 s; wide suite 88 → 48 s | S2, L |
| `test_curses` hermetic: it reads 735 MB of live `runs/alt-d/*/terror-probe.jsonl` | ≈ 16 s, and stops growing | S3 |
| `slow` marker by path for `scenarios/` (428 tests, 437 s): routine runs `-m "not slow"`, full run before commits and after combat/hunt/pursuit changes; add the fast golden/replay files to the loop-watch wide suite; fix its text (`-n` is ignored, 88 s not 1 min) | routine run ≈ 130 s | S4 |
| One determinism test per harness instead of ≈ 32 | ≈ 20–25 s | S5 |
| `test_viz.py`: one export per fixture | ≈ 8 s | O3 |
| Pricing: session cache for `build_profiles.build()` (3.5 s, 341 call sites), `compile_stat_configurations`, the 6–151 MB JSON reads | ≈ 1.8 h | P1 |
| Pricing: the item bank opt-in (31.7k cases), a stratified 1–2k subset by default, full bank before publishing a generation | ≈ 2.1 h | P2 |
| `harm_path` (half of each arena play, ≈ 7 ms a call; the live loop pays it every look): profile and speed up | tests and the live look | S |

Expected: routine `inventory_tracking` run ≈ 130 s (from ≈ 625 s), full ≈ 535 s; pricing default ≈ 20–30 min (from
≈ 4.7 h).

Test quality: test_runner pins privates (82 uses, 33 SimpleNamespace, real threads) — move it to the fake `Game` and
public seams as the runner splits (phase 3); fakes.py builds its clicks from the constants it tests — one pinned golden
per panel (T); `test_tick_cost` bounds wall time and can fail under nice 19 — bound work, not time.

## Phase 3 — architecture (in this order; each step behind its tests)

1. **Typed stop causes, then a pure `decide()` for `_loop_stopped`** (L P6, S per step). Only 5 of 253 `raise Abort(`
   pass a cause; the room rules read message text (`ROOM_WORDS`, `'make room' in warned`); `_loop_stopped` is a chain
   of 11 ifs setting one-shot flags. A table test then pins the rule order.
2. **One inventory-grid type** (T4, M): `items/grid.py` `Grid` replacing ≈ 10 fit/occupancy copies (`has_room`,
   `fits`/`room_for`, `charms._fits`, `town._spot`, `townplan._first_fit`, the fakes'), which disagree on unread rows.
   Parity property test first.
3. **One memory-access layer** (O2, M): `native/memory.py` reader (28 hand-written `/proc/<pid>/mem` opens, two
   `GameMemory` classes, "pick the one unit table" ×23, the guarded reader living in a probe module).
4. **Split world.py** (T5, O5, M): `game/{records,layout,decode,memory}.py` as pure moves; then read each unit table
   once a look (`loot()` walks the item table ≈ 7 times). One `Monster` type (terror/ and macros/ each have one).
5. **A typed game-reads object** (T, L P8): `Run`'s ≈ 30 optional closures guarded 105 times
   (`run.X() if run.X is not None`).
6. **One strategy object per loop kind** (L P2, M, after 1): kind branches live in `Loop.leg` (336 lines), runner's LOOP
   closures + `_tz_hands`, and `tzloop.perform`, with real duplicates (door, trip resets, prebuff-on-waypoint, the
   drops wait, through-portal). One `LegHands` replaces the closures and `TzHands`; leg names and log lines unchanged.
7. **Split `Hunter`** (L P4, M–L): `LevelMemory`, then goal choice, then moves, `Hunter` a façade; `cleared` and
   `agenda_cleared` share their ≈ 60 common lines. Also `RunSpec` for the four run-mode booleans (L P5), the watchdogs
   in one pure module (L P7), `Safety.price` (505 lines) split.
8. **Package boundaries** (O5): HUD drawing out of osd/ (S); `takes/` package for recording and loop analytics out of
   combat/ (M); later the arena out of `tests/` (L: production data is written by a test module, `make stance-viz` runs
   one).
9. **Skill tools** (O4): one serve-log reader (the date parser ×6, session discovery ×3); later serve writes
   `events.jsonl` so the tools stop parsing prose (logwords + a 652-line line-shape test exist only for that).
10. **Pricing** (P): a narrow pricing API for `inventory_tracking` (30 deep imports today, an import cycle with
    `pricing.triage.runtime`); one Traderie client; bring `pricing/tools` under ruff (1,213 findings) and `pricing/`
    under pyrefly (626 errors), or delete the unused tools.
11. Later, large: LK and Andariel through the agenda too, one game-level state machine (L P3), only after 6 and the TZ
    live checks.

## Phase 4 — comments and docs

Policy (all three studies converge on it):
- A comment says **why**, in one or two lines. A ruling keeps its date and a short quote:
  `# Never a game left with a valuable on the ground (the player, 2026-10-17).`
- The incident's evidence (clock times, takes, numbers, the story) moves to the journal or `rca/` with a pointer,
  not the code. No comment restates the code.
- Module docstrings: what the module is and its boundaries, ≤ 10 lines; design history goes to the plan/README.
- Each file's cleanup is checked by an AST comparison: only comments and docstrings changed.

Measured target: prose from ≈ 39 % to 20–25 % of characters; runner/loop/hunt each 15–20 % shorter; ≈ 1,500–2,000 lines
out of combat/levels/config; the 17 longest module docstrings (combat/sim/monsters.py 154 lines, record.py 108) cut to
summaries. Research and old plan notes (six of them) into a history folder (O1).

## Phase 5 — hygiene (S)

- Makefile: `make test` runs only the collection tests; add `test` (routine, not slow), `test-all`, `lint` (O).
- Retention for `runs/alt-d/` (425 of 901 sessions older than 7 days) and `tmp/`; prune pricing generations with
  `python -m pricing.knowledge.publication --prune-only` (≈ 13 GB) (O, P).
- Module-level state not reset between tests: world's `GOLD_SEEN`/`BASE_ROLLS_SEEN` (T).
- The worktrees' saved patches in `rca/2026-10-19/cleanup/worktrees/` can go once judged (worktrees removed 10:21).

- 2026-10-19 batch D (the rulings below): the beset guard fights back (stops.py `Remedy.FIGHT`, loop.py
  `after_beset`), leaving only under the healer's 65 % floor, a second beset within 60 s, or no attacker and nothing on
  the ground; an unreadable belt item leaves the belt unread for the look (`Loot.belt_read`: no refill, drink or
  alarm from it; the safety prices it as empty); townplan deleted (the visit snapshots stay fixtures); the stash view
  is read once more (0.2 s) before the page-by-page scan; the Echoing Strike stage 3–6 harness (compare, scoreboard,
  validate, CLI; the sim viz uses stays), terror exposure/bursts and probes/buff deleted; 18 pursuit-off arena tests
  deleted (the study's 34 counted other "today"s); the frozen pricing work in `pricing/archive/2026-10-19/` (150
  maintenance modules, 217 test files, 23 rules JSON, the per-item planning files, STATUS/handoff/history): the
  pricing test run 12,053 → 9,020 tests, 13 → 5 min, the same 35 red; the 50 live maintenance modules under pyrefly.

- 2026-10-19 batch E: runner.py split into `macros/running/` (1,775 → 714 lines; execution, legs, recovery,
  valuables, watch, base; AST-checked pure moves); harm_path ×1.7 a call, bit-identical (106k captured calls;
  `test_harm_parity.py`); `assessment/maintenance` → `assessment/compile`; probe and the take recorder on
  `open_memory`/`one_unit_table`; slow wall-time tests marked, `test_viz` export cached; disk: alt-d sessions over 14
  days, tmp/ and 14 old pricing generations deleted (`make prune-runs`); `BuildSettings.pursuit` on by default (serve
  passes `macro_pursuit` through `builds.pursuing(build, on)`). With it, at the player's asks: a game begun in any other
  town takes the kind's waypoint, the `loop-kind` request (tools/kind.py; the service starts as Andariel), owned copies
  deciding the identify verdict (identify/service.py `owned_verdict`).

## The player's rulings (2026-10-19, batch D)

1. Town shadow planner: delete townplan, `_predict`, `_matched` (≈ 520 lines with tests); the visit snapshots stay
   as fixtures.
2. Frozen pricing work: archive (a dated folder outside the test run and pyrefly; nothing deleted).
3. Delete the 34 "pursuit off" arena baselines. Not asked: seeds a setting, `-n` on the slow tests (done: -n 6).
4. Delete the Echoing Strike stage 3–6 harness, `terror/exposure.py`, `terror/bursts.py`, `probes/buff.py` (check
   no live import first).
5. Stash read: one short re-read before the page-by-page scan.
6. Beset guard: fight the attacker back first, then the valuable; leave only on low life (the death rules win).
7. Belt read: skip an unreadable belt item, keep the ground drops, the belt "unread" for that look (no refill from it).
8. Fire on the way: shorter approaches only when the move itself is over budget or vetoed (as fixed in batch C).
Not asked yet: full exploration of levels before a TZ boss; an instant first aim instead of the flick.

## The player's rulings (2026-10-19, batch E)

1. Serve logs: delete `runs/alt-d` sessions older than 14 days; `make prune-runs` repeats it.
2. `tmp/` at the root: delete what is older than 7 days.
   All of `tmp/` went (65 GB), the MrLlamaSC transcript that `appraisal-leveling-candidates-2026-09-23.json` names
   with it; the player: "we're fine to delete tmp" (not fetched again).
3. Pricing generations: prune with the publication tool (`--prune-only`).
4. Arena: `BuildSettings.pursuit` defaults to on, as the live loop runs; changed goldens re-pinned after a check.

## Suggested order of work

Phase 0 → phase 1 (old TZ coordinator first: it shrinks runner.py before anything else touches it) → phase 2 → phase 3
steps 1–5 → 6–7 → phase 4 per file as each file settles → 8–11. Pricing (phase 0.3, phase 1 pricing rows, phase 2
pricing rows, phase 3.10) is independent of the loop and can run in parallel with it.
