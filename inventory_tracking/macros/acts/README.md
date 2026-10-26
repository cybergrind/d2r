# Act scripts — how to add an act

A shard act kind (`act1` … `act5`, "Shard: Act N", HUD word `ACTN`) uses the act's Worldstone Shard in the Fortress
(`macros/actloop.py`, `macros/terrorize.py`), then plays the act in the order its script declares, then the rotation.
Design: [act-terrorize-plan.md §11](../../routes/act-terrorize-plan.md). Act 4 ([act4.py](act4.py)) is the worked
example; it is live.

## What an act agent owns

- `macros/acts/act<N>.py`: the act's `SCRIPT`. Nothing else in `macros/acts/` (the engine and the registry are shared).
- `tests/inventory_tracking/macros/acts/test_act<N>.py`: its tests, with the [harness](../../../tests/inventory_tracking/macros/acts/harness.py).
- Any new route the act needs, in `routes/catalog/act<N>.py` (e.g. Duriel's Lair 73 for act 2), and any new level
  handler in `levels/handlers/` (one module per level or chain; discovered by itself).

Do not edit `loop.py`, `actloop.py`, `tzroutine.py`, `tz_routes.py`, `acts/engine.py`, `acts/__init__.py`, the
picker or the watch tools: the kind, its picker entry, `restart.py --kind act<N>` and `elites.py --kind act<N>` exist
already. A need there goes to the coordinator (the game cap `loop.ACT_GAME_SECONDS` 2700 s is shared too).

## Declaring the steps

```python
from inventory_tracking.macros.acts.engine import AFTER, WORKED, ActScript, Rest, Trip

SCRIPT = ActScript(
    1,
    (
        Trip('Andariel', 37, waypoint=35, crossed=WORKED),  # Catacombs 2 -> 3 -> 4 -> Andariel, worked on the way
        Trip('Countess', 25, waypoint=6, crossed=WORKED),  # the Black Marsh -> the Tower -> the Countess
        Rest(zone='Act1-Tower'),  # the zone's levels no step worked yet (the Hole: 11, 15)
    ),
    ready=False,
)
```

- `Trip(route, target, waypoint=None, crossed=AFTER, missing='')`: catalogue route `route`'s trip to level `target`
  (the boss's). `waypoint` None: the route's waypoint nearest the target. `crossed=AFTER`: the levels on the way are
  only crossed (the leaders near) and each gets its own trip right after the target, nearest it first (Act 4's
  River of Flame); `WORKED`: worked on the way; `ONLY` (2026-10-26): only crossed, no trip of their own (a later
  step or the act's rest may still take them). A toured level (a tomb) tours them all, one by one.
- `Rest(levels=(…))`, `Rest(zone='Act2-ArcaneSanctuary')` (a rotating zone's name in the installed table),
  `Rest(route='Summoner')` (the route's levels): what no earlier step works, covered by `zone_route_plan`.
- `ActScript(alone=(…), whole=frozenset(…), extras=(…))` (2026-10-25, act2.py TZ_LEVELING_STEPS): the steps of an
  alone kind's game (loop.py `Kind.alone`, ALONE_KINDS: `act2tz`, "Act 2 TZ leveling", last in the picker) only, then
  the acts of `extras` a shard over the limit terrorized in that game, then the game's end: no rest of the act, no
  rotation, no other act (`actloop.alone`, `actloop.extra_acts`); `whole` levels toured whole whatever their size
  (`tzroutine.WHOLE`, TZ+). `extras` (2026-10-26, act2.py TZ_LEVELING_EXTRAS): other acts' scripts of their own
  `alone` steps and `whole` levels: act 4's Chaos Sanctuary whole and Diablo (the River of Flame `ONLY` crossed),
  act 5's Worldstone Keep 2 and 3 whole, the Throne and Baal; a Deep or Northern over the limit is used (the overflow's
  ways: a carried one first, else one from its stack; at the shard step, a town visit, the game's end) once act 2 is
  terrorized, its act played after act 2's steps, act 4 before act 5. The act's own kind ("Shard: Act 2") and act 2 in
  any other game play `steps` as below; "Shard: Act 4" and "Shard: Act 5" their own scripts.
- After the steps, always: the rest of the act's levels, then the rotation. "Rest of zones one by one" needs no step;
  list `Rest(zone=…)` steps to fix the zones' order.
- Your own step: any object with `label` and `plan(self, act: ActPlan)`; inside, `act.route_trip(route, target,
  waypoint)`, `act.add(trip, passes)`, `act.rest(levels, label)`, `act.skip(self, why)`, `act.covered`, `act.zone`.

## A route the catalogue lacks

Mark the step: `Trip('Duriel', 73, missing="no route into Duriel's Lair yet (the Orifice)")`. The engine skips it and
says `Macro: act: act 2 step 2 (Duriel to 73): no route into Duriel's Lair yet (the Orifice): skipped`; its levels
fall to the later steps, and those no trip covers are the itinerary's skipped (`Macro: tz: zone … skipped [73 (no
catalogue excursion covers it)]`). A route name the catalogue lacks, a path that does not exist from the waypoint
given, or a pending stage are skipped and said the same way. Add the route, drop `missing`, and the step plays.

## Testing, then ready

```python
from tests.inventory_tracking.macros.acts.harness import ActGame, plan_of, trips_of


def test_the_act_1_plan(monkeypatch):
    plan = plan_of(monkeypatch, 1)  # the script forced ready; `rotation=` adds a rotating zone
    assert trips_of(plan)[:2] == [('Andariel', 35, (35, 36, 37)), ('Countess', 6, (6, 20, 21, 22, 23, 24, 25))]


def test_an_act_1_game(monkeypatch):
    walk = ActGame(1, monkeypatch).play()  # the shard, then every leg until the game is left
    assert walk.shard == [1]
    assert walk.waypoints[:2] == [35, 6]
    assert walk.kills[:2] == ['Andariel', 'The Countess']
    assert walk.stopped is None, (walk.stopped, walk.where)
```

`Walk`: `legs`, `moves` (`('waypoint' | 'door' | 'portal' | 'walk out' | 'through', level)`), `runs`, `levels` (first
runs in order), `kills`, `shard`, and `stopped`/`where`: the Abort that stopped the walk and the level (None: the game
was left). A level run does its route stages (fights, uses, stands, loot) by itself; the way on goes through a door
or a portal stage; `game.on_run = lambda area: …` adds more (`game.game` is test_tzloop's `Script`: `killed`,
`progress`, `sightings`). The act's game must end in `LEAVE` (`walk.stopped is None`) with every playable level run.

Draft walks of 2026-10-20 (the player's orders, routes as they stand): act 5 walks to its end; act 1 stops at the Cold
Plains (3) on its second trip from that waypoint (the Cave after the Crypt: "TZ next level again and again"); act 2
at the Canyon (46), the tombs tour (test_tzloop.py's tomb tests show the tour's fakes: entrances, `tour_back`); act 3
at Travincal's waypoint (81) after the Durance trip. Each is the act agent's to explain: a fake's gap or a real one.
`test_engine.py` checks every script (`check`) and that a ready script has its `test_act<N>.py`.

Then set `ready=True`: the kind is offered by `loop_kinds()` (KP_6's picker, `restart.py --kind act<N>`), and the act
terrorized by hand in TZ/TZ+ plays the script's order too. Before, the generic boss-first order plays it
(`tzroutine._route_trips`). Run the wide suite (`-m "not slow" -n 3`) before you say done; the coordinator restarts.

## Log lines

- `Macro: act: act N step K (<label>): <why>: skipped`: a step not played.
- `Macro: act: act N <rest label>: <route> from <wp> blocked: <why>`: a rest's trip with a blocked hop.
- `Macro: tz: zone ActN-Manual + <rotation>: <trips>; skipped [...]`: the plan (`tzroutine.trips_said`).
- `Macro: act: …` / `Macro: terrorize: …`: the shard step (actloop.py, terrorize.py).
