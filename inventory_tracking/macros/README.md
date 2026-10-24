# Macro framework — start here

Checked against code on **2026-10-13**. `macros/` executes player requests;
`combat/` supplies combat decisions and shared models; `builds/` supplies the
character-specific behavior. Start with this map, then follow the source links.

## How it runs

`make serve` starts the host service. [appraisal/service.py](../appraisal/service.py)
hands [the build registry](../builds/__init__.py) to [MacroRunner](runner.py).
[Compositor bindings](../input/compositor.py) send these requests:

| Key | Request | Behavior |
| --- | --- | --- |
| Mod+X | `macro` | Prebuff / game cycling according to place |
| KP_4 | `teleport` | **The jump** ([jump](running/jump.py), the player's ruling 2026-10-19: "force jump to the next goal", "Ignore mobs, resume on arrival"): hop after hop to the goal the HUD shows as `NEXT:` (the teleport key's pursuit goal), each look priced with attack mode off, so no hold for a fight and no strike gap on the way. The safety stays: a vetoed hop is not made, and a retreat or firing stand it makes instead ends the jump; the drinker looks at every hop and a life under the safety floor ends it; a valuable in a stop's reach is picked up first. With no pursuit goal it is the plain step toward the level card's mark, again and again. It ends at the goal (arrival, the object used, the level changed), at the player's hand (a key, a button, the pointer, a panel), at a death (nothing more is pressed, the loop stops), or after 60 hops / 30 s since the last press. A press during it extends it, and the key held on after its end is that press; at attack mode's own fight (the boss in reach) the press is posted to the mode as before. Attack mode pauses for it and resumes after; on the jump's own end it comes on for a level run or a fight goal unless the player turned it off or the loop is on. Log: `Macro: jump: <goal>: N hops in S s, <why>`. `MacroRunner.jumps` off: one step a press (the arena's recorded presses) |
| KP_2 | `hunt-elites` | Seek an elite (or exploration fallback), then attack mode |
| KP_3 | `hunt-any` | Toggle the active mode, attack mode by default; a **double press** (exactly two within 0.35 s, the first toggling at once, judged once the window closes; a mashed key switches nothing) cycles the active mode ATTACK ↔ BUFF, switching a mode that was on in place (`Macro: Active mode: BUFF`; [buffing](running/buffing.py), the player's ruling 2026-10-19). **Buff mode** ([buffmode](buffmode.py)) keeps the build's upkeep rows up while the player plays by hand (Hex: Purge, Psychic Ward, Battle Orders from the Call to Arms, Consume renewed within 15 s of its end, a Defiler): no strike, no move; a cast only after the hand (pointer, keys, buttons, the character moving or casting) has rested 1.5 s, never in town, with a panel open or by the pad; a weapon swap only with no hostile within 30, the set found in hand put back after. It pauses for a step, yields to the KP_1 run and the loop and resumes after them; a death ends it (`Macro: buff mode: …`; HUD `BUFF`). Attack mode: With the pursuit loop off it still takes the loop's priced step against a read model (Baal, Diablo): out of or across an act under way, or to a priced place within strike reach ([hunt](hunt.py) `guard`), then strikes again; no other move (`Macro: attack mode: stepping …`; rca/2026-10-14/baal-sim.md fix 3). With the loop on and no press, it goes to the route's boss only within `ALONE_BOSS_UNITS` (twice the fight's `SIGHT`, 60): a farther one is KP_1's or KP_4's (`Macro: attack mode: <boss> is N away …: not gone to without a press`; the player's ruling 2026-10-15, run-2040-findings.md "Fixes: walls, better place, far boss") |
| KP_1 | `pickup` | Pickup, container or combat movement/sweep, depending on current facts. With the pursuit loop on (`macro_pursuit`): one press runs the level's route to its end through attack mode ([pursuit](pursuit.py) leash; rca/2026-10-13/kp1-level-run.md). The player's hand (a click, a panel open) pauses the run, which goes on by itself once the hand rests (`SETTLE`); a valuable with no room is stood by; potions are side goals ([supply](supply.py)). **Run mode** ([runmode](runmode.py), ruling 2026-10-14): by default the run goes to the level's goal (the route's stages). A way out behind a warp (stairs, a door, a cave's mouth) ends the run at it: going through is a press (KP_4). An **open passage** (no warp joins the levels: levels.txt Warp -1 or a border, [presets](../levels/presets.py) `open_passage`; the River of Flame into the Chaos Sanctuary) is aimed a tile inside the next level ([exits](../levels/exits.py) `through`), gone to by the navigation class in hand and walked across (`pursuit.through`, 2026-10-15), and the run goes on as the run of the level it leads into, once, in the same mode where the player switched to a full clear (a switch to the goal does not carry: that level's own rules decide, a terror zone being a full clear): `pursuit.carried`, `Macro: run: on into <level>`, waiting up to `ENTERING` 3 s for that level's card (2026-10-15); a level left any other way (a waypoint, the town) ends the run. A run fights what is on its way (hostiles within 30 with a clear line, before a door, a place or a stand; not before a seal); a **full clear** of the level first on a terror zone, or after a **KP_1 double press** (exactly two presses within 0.35 s, judged by the clock: a pair no look came in the window of still switches; a mashed key switches nothing), which toggles goal ↔ full clear for the current level only and lapses on a level change (a town visit included) other than a full clear carried on across a passage. Log: `Macro: run: …`; HUD: `CLEAR` / `CLEAR TZ` beside the attack line ([kp1-mode](../../rca/2026-10-14/kp1-mode.md)) |
| KP_6 | `loop` | The Lower Kurast loop on/off ([loop](loop.py), [plan](../routes/lower-kurast-loop-plan.md) phase 4; every kind's rounds, rulings and restarts in [the loop journal](loop-journal.md)): from where the character is, one leg a run — the next game and its prebuff, Jamella for keys and Town Portal scrolls when either is under 3 ([shop](shop.py); no scrolls, none counted, with the Sling worn: its own Town Portal, [portal](portal.py) `portal_source`, [sling-plan](sling-plan.md)), the waypoint to Lower Kurast ([waypoint](waypoint.py)), the KP_1 level run for the chests, the pickup of what is left, Town Portal ([portal](portal.py)), the waypoint to Pandemonium Fortress, the loop's items into the cube ([cube](cube.py)), Save and Exit — until toggled off or a leg stops (`Macro: loop stopped: …`; a leg made again and again in a game stops it too). Mouse mode only. HUD: `Loop: game N, <leg>`. A single press acts 0.35 s later; a **double press** switches the pickup level of every loop and activity ([pickmode](pickmode.py), 2026-10-19): `GOOD` (the default: runes, gems, charms, jewels, rare rings, priced uniques, what the loot marks point at — shards, essences, uniques the filter shows — plus gold and potions) or `MOST` (the regular pickup: what KP_1 took before); **three presses** open the kind picker on the HUD ([kindpick](kindpick.py), 2026-10-20, the player: "pop some kind of dialogue to chose the mode on 3 clicks"): the loop's kinds ([loop](loop.py) `loop_kinds`) with name, word and metric, the one running marked `now`, the next highlighted, and the kinds announced but not built shown as `coming` (`COMING`: `Shard: Act 4`, gone by itself once a kind `act…` is offered); while it is open **one press** moves the highlight, **two** choose (at once, as the old cycle: `Macro: loop kind: <name> (picked)`, then `Loop run: <name>`), **three** close it, and 6 s with no press close it with nothing changed; the loop's on/off is never touched by it. Without a HUD canvas (`--no-osd`, or none holding `canvas.lock`) three presses cycle the kind as before (`… (cycled: no HUD for the picker)`). The `loop-kind` request (d2-loop-watch `tools/kind.py`) still sets the kind and closes an open picker. HUD mode line: `<mode> PICK:<level> NEXT:<leg or goal>` (runner.py `run_badge`; mode: the kind's word LK, AND, TZ+ (TZ with `tzroutine.TZ_PLUS` off), TZC with the loop on, else ATT) |
| KP_7 | `pad` | Loot to Cube: one tap of the virtual pad's button ([gamepad](../input/gamepad.py); KP_5 before 2026-10-19) |

The runner owns one working run at a time. [Waiting](waiting.py) keeps at most
one queued request per routine, ordered by priority and subject to expiry.
Requests can cancel a run or pause attack mode; queued steps run before the
mode resumes. Shutdown cancels work and prevents successors.

Each run gets a [Run](engine.py): game reads, guarded input, clock/pacing,
cancellation and callbacks. On its first read containing a player, the runner
chooses the first matching build; character layers precede the general build.
[Generic](../builds/generic.py) is the fallback, with shared movement and no attack.

[Hunter](hunt.py) owns attack mode and its memory across steps: observe the game,
respect player input, maintain buffs, choose an aim/place, fight or move, gather
when appropriate. [Actuator](actuator.py) guards actual keyboard/mouse delivery.
Decisions consume observations; execution checks what the game actually did.

## Vocabulary and contracts

The authoritative interfaces are in [build.py](build.py).

| Term | Meaning here |
| --- | --- |
| Build | Frozen composition of attack, movement sets, buff rows/casters, weapon loadout, settings and tactic hooks; layers use `dataclasses.replace` |
| World / Observation | `World` is a game snapshot; `combat.policy.Observation` is the combat decision view derived from it |
| Run / routine / mode | Execution context / requested operation / persistent attack behavior that can pause and resume |
| Attack | `sees` enriches an observation, `aim` chooses a cast, `dealt` estimates raw damage per foe; also supplies skill and reach |
| MovementSet | An applicable movement capability/composition; the navigator asks the first matching set |
| MoveFacts / Intent | Current movement evidence / constraints for this move (reserve, swap, wait, stand-off, forbidden landings) |
| Leg / Step / NoWay | Movement answer / destination plus jump skill (`None` means walk) / explicit reason, distinguishing arrival from blockage |
| Camp | A scored place to stand, including how to reach it; stance chooses it, travel executes it |
| Buff / caster | Declarative row with phase, due/target/state checks / optional custom execution for more than aim-and-key |
| Loadout | Weapon sets named by purpose (`prebuff`, `battle`); a character layer supplies them |
| Tactic | Enemy-specific positioning/opening contract; its presence does not mean the planned tactic system is wired |

Movement and combat positions normally use **world units**. Room/route geometry
also uses tiles; screen input uses pixels. Check the boundary's conversion
(`TILE_UNITS`, [game/view.py](../game/view.py)) before passing coordinates.

## Where changes belong

| Change | Start here |
| --- | --- |
| Request lifecycle, queue, cancellation | [runner.py](runner.py) (the state, the requests, the runs' lifecycle), [waiting.py](waiting.py) |
| The runner's other methods (module functions bound on `MacroRunner`) | [running/](running/__init__.py): [execution.py](running/execution.py) (a run's making, `perform`, the teleport press's steps), [legs.py](running/legs.py) (the loop's legs, `_loop_hands`), [recovery.py](running/recovery.py) (the loop's stops, `classify`, the Gheed's swap), [valuables.py](running/valuables.py) (the ground's valuables, the trips back), [watch.py](running/watch.py) (`poll`'s watchdogs), [room.py](running/room.py) (the no-room routine every activity shares: the cube, then a trip by the room package; ROOM for a hand activity, 2026-10-19), [jump.py](running/jump.py) (the teleport press as a jump to the next goal, 2026-10-19); constants in [base.py](running/base.py) |
| Fight orchestration / player intervention | [hunt.py](hunt.py), [combat/controller.py](../combat/controller.py) |
| The stand guard: after a stop the KP_6 loop made itself, in a level, a hit or a hostile within SIGHT turns attack mode on (the hunt's own fight and safety), off again once quiet; the player's KP_6 or attack key, the loop on, a death or another game end it; never a leg, a leave or Save and Exit (2026-10-22, `guard.GUARD`; [findings](../../rca/2026-10-22/guard-findings.md)) | [guard.py](guard.py) (the rules), [running/guarding.py](running/guarding.py) (armed by recovery.py `_stop_loop`, looked at by watch.py `poll`) |
| Aim/damage specific to this build | [Echoing Strike attack](../builds/warlock/echoing_strike/attack.py) and its sibling mechanics/data |
| Position scoring | [combat/stance.py](../combat/stance.py); pure, shared by live play and simulation |
| Movement decisions / execution | [movement.py](movement.py), [travel.py](travel.py), [teleport.py](teleport.py); class capability in [Warlock movement](../builds/warlock/movement.py). A far goal's way is planned by the navigation class in hand (`Ways.means`: Teleport crosses walls; Blade Warp and walk goes by the walked way, a warp only over a clear line where it beats the walk; walk), for the pursuit loop and the old keys' empty-staff step alike ([navigation-classes](../../rca/2026-10-14/navigation-classes.md)) |
| A companion kept alive by a jump that brings it (Blade Warp and the mercenary) | [combat/escort.py](../combat/escort.py), `hunt.py` `escorted` |
| Buff execution / build plan | [buffs.py](buffs.py) / [Warlock buffs](../builds/warlock/buffs.py), [casters](../builds/warlock/casters.py) |
| The strike back on the right mouse button (keyboard mode, after a controller stint) | [skillpanel.py](skillpanel.py), `hunt.py` `strike_back`; the icon's place per character in [characters.py](../builds/characters.py) `ICONS` |
| Potion judgement / delivery | [combat/survival.py](../combat/survival.py) / [drinking.py](drinking.py); settings via `BuildSettings.drink` |
| Character weapon choices / build registration | [characters.py](../builds/characters.py) / [builds/__init__.py](../builds/__init__.py) |
| Level stages and progress | [route.py](route.py), [levels/routes.md](../levels/routes.md) |
| The goal queue and the terror zone kinds (TZ leveling, Full clear TZ; on since 08:58 on 2026-10-19: `tzloop.ENABLED`; TZ leveling is TZ+ since 2026-10-20: every level under 300 hostiles explored and its groups of 4+ taken, a big one's groups of 8+ and leaders, `tzroutine.TZ_PLUS`, [findings](../../rca/2026-10-20/tz-level-leave-findings.md)) | [goals-plan.md](goals-plan.md): [agenda.py](agenda.py), [tzroutine.py](tzroutine.py), [navigation.py](navigation.py), [tzloop.py](tzloop.py) |
| The shard act kinds (`act1` … `act5`, "Shard: Act N"; the act's Worldstone Shard, then the act in its script's order, boss first, then the rotation; each offered once its script is `ready`, 2026-10-20) | [acts/README.md](acts/README.md) (how to add an act), [acts/engine.py](acts/engine.py), [actloop.py](actloop.py), [terrorize.py](terrorize.py), [act-terrorize-plan.md](../routes/act-terrorize-plan.md) §11 |
| Controller mode: the pad back end, the mode policy | [pad.py](pad.py), `runner.py` `play_by` (a flip under a run ends it, `Flipped`, and the runner makes the same request again in the new mode: `again`); [rca/2026-10-13/controller-mode.md](../../rca/2026-10-13/controller-mode.md) §10 |

Keep class/skill-specific logic under `builds/`. Builds import framework contracts;
the service injects builds into the framework. Prefer settings and composition,
then a protocol implementation for genuinely different behavior. Keep decisions
pure and input behind the guarded execution layer; preserve cancellation,
player intervention and observation-based completion. Follow
[development.md](../../development.md).

## Current limits and verification

The framework/build split, shared movement and buff executors are implemented.
Attack mode drinks from the belt and stance includes crowd escape. `make osd`
remains an independent potion actor; macro drinking observes belt depletion.
The complete threat-based safety model, goal queue/full-middle leashes, tactic
composition and planned swap/buff extensions remain work in the plan. Several
shared combat constants still reflect Echoing Strike tuning.

For a change, run the relevant module tests plus the build contracts and import
ratchet (which permits only listed remnants of build-specific framework code):

```sh
uv run --offline pytest tests/inventory_tracking/builds/test_contracts.py tests/inventory_tracking/builds/test_ratchet.py -q
uv run --offline pytest tests/inventory_tracking/macros tests/inventory_tracking/combat tests/inventory_tracking/builds -q
```

The whole tree (about 10 minutes serially, mostly the arena plays) runs on all
cores with pytest-xdist in about a minute. Use `--dist loadgroup`: the tree's conftest
keeps each file's cached plays on one worker and spreads the heavy arena files'
`xdist_group` families over the others (development.md). Single files and tests run
faster without `-n`.

```sh
uv run --offline pytest tests/inventory_tracking -q -p no:cacheprovider -n auto --dist loadgroup
```

[Scenario tests](../../tests/inventory_tracking/scenarios/) add recorded battle
replays, golden decisions and a closed-loop arena. Use the
[dummy build](../../tests/inventory_tracking/builds/dummy.py) as a second-build
example. Arena evidence is model-dependent; a passing replay is not live-game
validation. Inspect `probe.log` and `latency.jsonl` for host behavior; summarize
press traces with `uv run --offline python -m inventory_tracking.macros.latency`.

[framework-plan.md](framework-plan.md) holds the staged work;
[architecture.md](architecture.md) describes current boundaries and links to the
historical design; [plan.md](plan.md) records live incidents and decisions. Dated
snapshots can lag the code—do not treat a proposed interface as active.
