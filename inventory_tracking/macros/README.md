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
| KP_4 | `teleport` | One route-stage step or movement toward the level card's mark; may handle a drop or fight first |
| KP_2 | `hunt-elites` | Seek an elite (or exploration fallback), then attack mode |
| KP_3 | `hunt-any` | Toggle attack mode |
| KP_1 | `pickup` | Pickup, container or combat movement/sweep, depending on current facts. With the pursuit loop on (`macro_pursuit`): one press runs the level's route to its end through attack mode ([pursuit](pursuit.py) leash; rca/2026-10-13/kp1-level-run.md). The player's hand (a click, a panel open) pauses the run, which goes on by itself once the hand rests (`SETTLE`); a valuable with no room is stood by; potions are side goals ([supply](supply.py)) |

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
(`TILE_UNITS`, [view.py](view.py)) before passing coordinates.

## Where changes belong

| Change | Start here |
| --- | --- |
| Request lifecycle, queue, cancellation | [runner.py](runner.py), [waiting.py](waiting.py) |
| Fight orchestration / player intervention | [hunt.py](hunt.py), [combat/controller.py](../combat/controller.py) |
| Aim/damage specific to this build | [Echoing Strike attack](../builds/warlock/echoing_strike/attack.py) and its sibling mechanics/data |
| Position scoring | [combat/stance.py](../combat/stance.py); pure, shared by live play and simulation |
| Movement decisions / execution | [movement.py](movement.py), [travel.py](travel.py), [teleport.py](teleport.py); class capability in [Warlock movement](../builds/warlock/movement.py) |
| Buff execution / build plan | [buffs.py](buffs.py) / [Warlock buffs](../builds/warlock/buffs.py), [casters](../builds/warlock/casters.py) |
| Potion judgement / delivery | [combat/survival.py](../combat/survival.py) / [drinking.py](drinking.py); settings via `BuildSettings.drink` |
| Character weapon choices / build registration | [characters.py](../builds/characters.py) / [builds/__init__.py](../builds/__init__.py) |
| Level stages and progress | [route.py](route.py), [levels/routes.md](../levels/routes.md) |
| Controller mode: the pad back end, the mode policy | [pad.py](pad.py), `runner.py` `play_by`; [rca/2026-10-13/controller-mode.md](../../rca/2026-10-13/controller-mode.md) §10 |

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
