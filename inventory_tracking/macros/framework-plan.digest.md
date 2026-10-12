# Framework plan — digest

Full plan: [framework-plan.md](framework-plan.md). Spec: [architecture.md](architecture.md).

**Goal:** `macros/` + `combat/` become a framework that names no skill; the Echoing Strike Warlock
moves to `inventory_tracking/builds/`; a closed-loop test arena fed from recorded battles proves
the end logic. Harness first, then the move with no change of behavior, then safety.

**Always:** no behavior change in Stages 0–3 (golden net identical, suite green); decisions pure;
player input wins; `make osd` independent; no commits unless asked; `rg --no-config`.

**Precondition:** the uncommitted tree is frozen by the user before Stage 0.

**Who:** H = Haiku 5.5 (one small pure module or tests only, disjoint files, full interface in the
brief, parallel in groups). C = capable sub-agent (drives production code, multi-file moves).
M = main session (stage entry detailing, integration, gates, anything against the game).

| Stage | Delivers | Gate |
| --- | --- | --- |
| 0 | golden net: `scenarios/golden/` decisions.json (through `Hunter` entry points, one adapter `cases.py`), replay logs, loop counts, pinned xfail list | recorded on the frozen base |
| 1 | arena = `Arena(fakes.Game)` + `combat/sim/monsters.py`: scene, result, moments, CLI (H); mobs, game, driver, cut, calibrate, threat scenes (C) | 16 threat scenes play with production code; calibration table; deterministic |
| 2 | `macros/build.py` contracts (`Attack` = `policy` + `dealt`) + `Build` + `choose`; `builds/generic.py`; test-only dummy build; contract tests; AST ratchet | contract suite green on two builds |
| 3 | Warlock into `builds/` (tasks 3.1–3.9), incl. `mechanics/echoing_strike.py` | `decisions.json` byte-identical, dummy build fights in the arena, ratchet down to a listed residue |
| 4 | osd burst rule; `taken` + caution + veto; `serve` drinking | six standing threat xfails green |
| 5 | rule at 15, `LowCharges`, careful landing, `eta` | navigation no worse |
| 6 | goal queue, leashes (KP_1 full; KP_4/KP_2/KP_3-on middle), drop lanes | TZ/route scenes, thrash tests |
| 7 | swap by threat, tactics (cows, dolls, archers, Heralds) | per-tactic scenes |
| 8 | buff plan: Call to Arms on swap, openings | buff scenes |

Stages 0–2 are fully tasked in the plan. Stages 3–8 are outlined; each is detailed by M at entry
and reviewed before any H task is briefed.

**Stage 0 groups:** 0.1 (M) → {0.2 C, 0.3 H, 0.4 H, 0.5 C} → 0.6 (M) → gate.
**Stage 1 groups:** 1.0 (M) → {1.1, 1.3, 1.4 H; 1.2 C} → {1.5 C} → {1.6 C} → {1.7 C, 1.8 C then H} → {1.9 C} → gate.
**Stage 2 groups:** {2.1 C} → {2.2, 2.3, 2.4 H} → {2.5 C} → gate.

**Review focus:** arena disagrees with the game (calibration gates every safety verdict); a
decision changed that nobody watched (goldens over all fixtures); timing drift (loop bounds);
a part answering with silence (`Leg = Step | NoWay`); two actors pressing at once; a play
depending on the wall clock (runner limits patched, determinism test).

**Status (2026-10-12):** Stages 0–3 done and committed; the refactor to framework and builds is
complete with no change of behavior. Suite: 5863 passed, 8 skipped, 63 xfailed (the pinned list).
- Layout now: `macros/` + `combat/` = the framework (contracts in `macros/build.py`; `movement.py`,
  `buffs.py`, `travel.py`, `hunt.py`, `runner.py`; `combat/{policy,controller,stance}.py`,
  `combat/sim/monsters.py`). `inventory_tracking/builds/` = the registry (`BUILDS`, `FALLBACK`),
  `generic.py`, `characters.py`, `warlock/{skills,movement,buffs,casters}.py`,
  `warlock/echoing_strike/{attack,build,mechanics,damage,hits,validate,scoreboard,compare,viz}.py`
  and `sim/`. The runner is handed the registry by `appraisal/service.py` and chooses per run.
- Guards: golden net (`scenarios/golden/`), the ratchet at 7 named pairs
  (`tests/inventory_tracking/builds/test_ratchet.py`), contract tests over every build
  (`builds/test_contracts.py`), the test-only second build that fights in the arena.
- Commands that moved: the combat gate and simulator tools are
  `python -m inventory_tracking.builds.warlock.echoing_strike <gate|validate|calibrate|simulate|inputs|policy|compare>`.
- **Arena calibration: 1 of 72 scenes trusted** (architecture.md §6.2.1): not yet a judge of safety.

**Stage 3½ (2026-10-12 night): done.** Evidence from 674 takes (`arena/evidence/EVIDENCE.md`), the monster
model refitted on the train half (`combat/data/monsters_fit.json`), moves take time in the arena. The model
matches the check half by mechanism (93 of 111 rows within 0.5–2); per-scene calibration is not a usable
measure for rare blows (architecture.md §6.2.2). Also that night: the full-inventory pickup fix (`b383d19`,
not a refactor change: plan.md entry of 20:30), found in the user's first live session on the framework.

**Next:** Stage 4 (safety) changes behavior in the game — the user's go-ahead is needed. Before its rules:
a seeds × scenes runner that compares scorecards as distributions; the Lightning Enchanted sparks refitted;
scenes cut at fixed times. The branch `combat-framework` is not merged to main.
