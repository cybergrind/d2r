"""The KP_6 loop's Baal kind (macros/loop.py BAAL, `baal_leg`; the player, 2026-10-25 ~12:17: "build a baal runner,
very similar to andariel runner"): the Worldstone Keep 2 by waypoint, down to the Throne, its waves before the
Chamber, Baal's fight, his drops waited for, Save and Exit; trips and the Gheed's swap from Harrogath. Modelled on the
Andariel tests of test_loop.py, over the fakes."""

from contextlib import suppress
from dataclasses import replace

import pytest

from inventory_tracking.macros import loop as looping
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import (
    BAAL,
    CHAMBER,
    DOWN_THE_KEEP,
    FIGHT_BAAL,
    FIGHT_THRONE,
    HARROGATH,
    LEAVE,
    PICK_UP,
    REPEATS,
    THRONE,
    THROUGH_PORTAL,
    TO_HARROGATH,
    TO_THE_CHAMBER,
    TO_THE_FORTRESS,
    TO_THE_KEEP,
    TOWN,
    TRADE_ROOM,
    TRIP,
    WORLDSTONE_KEEP_2,
    WORLDSTONE_KEEP_3,
    LegHands,
    Loop,
    kind_of,
    loop_kinds,
    next_leg,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


PANDEMONIUM_FORTRESS, LOWER_KURAST = 103, 79
GAME = 'cyber32'  # the fakes' game
LISTER = 'Lister the Tormentor'  # the route's Throne fight (routes/catalog/act5.py)


def at(area: int, **changes):
    return world(area, player=player(area, **changes))


def progress(killed: set[str], area: int) -> Progress:
    found = Progress(ROUTES, PERFORMED, lambda: frozenset(killed))
    found.note(GAME, area)
    return found


def keys(_world, skills=None):
    return {skill: {**KEYS, 220: 'x'}[skill] for skill in skills or ()}


def test_the_baal_kind_is_offered_in_the_kind_picker_and_found_by_where_the_character_is():
    from inventory_tracking.macros.kindpick import entries

    assert loop_kinds()['baal'] is BAAL
    row = next(row for row in entries() if row.key == 'baal')
    assert (row.name, row.word, row.metric, row.enabled) == ('Baal', 'BAAL', 'Baal kills an hour', True)
    assert (BAAL.trips, BAAL.swaps_gheeds, BAAL.boss, BAAL.lair) == (True, True, 'Baal', CHAMBER)
    assert kind_of(HARROGATH) is BAAL
    assert kind_of(THRONE) is BAAL
    assert kind_of(PANDEMONIUM_FORTRESS) is None  # the kinds' shared town: the kind chosen


def test_the_baal_levels_are_the_games_and_the_routes():
    # levels.txt (third-parties/d2data/json/levels.json): 109 Harrogath, 129-132 the Keep 2, 3, the Throne, the Chamber
    import json
    from pathlib import Path

    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.macros.waypoint import WaypointRow, waypoint_of
    from inventory_tracking.routes.model import FIGHT, LOOT, STAND, USE

    levels = Path(__file__).resolve().parents[3] / 'third-parties' / 'd2data' / 'json' / 'levels.json'
    if levels.exists():
        rows = json.loads(levels.read_text())
        rows = rows.values() if isinstance(rows, dict) else rows
        named = {int(row['Id']): row.get('LevelName') for row in rows if 'Id' in row}
        assert named[HARROGATH] == 'Harrogath'
        assert named[WORLDSTONE_KEEP_2] == 'The Worldstone Keep Level 2'
        assert named[WORLDSTONE_KEEP_3] == 'The Worldstone Keep Level 3'
        assert named[THRONE] == 'Throne of Destruction'
        assert named[CHAMBER] == 'The Worldstone Chamber'
    assert (THRONE, CHAMBER) == (throne.THRONE, throne.CHAMBER)
    assert waypoint_of(WORLDSTONE_KEEP_2) == WaypointRow(4, 8)
    assert BAAL.start == WORLDSTONE_KEEP_2
    found = progress(set(), THRONE)
    step = found.step(THRONE)
    assert step is not None
    assert step.route == 'Baal'
    assert [stage.kind for stage in step.script.stages] == [STAND, FIGHT, LOOT, USE]
    chamber = found.chosen(CHAMBER)
    assert chamber is not None
    assert [stage.kind for stage in chamber[1].stages][:2] == [FIGHT, LOOT]


def test_a_baal_game_goes_down_the_keep_clears_the_throne_then_kills_baal_and_is_left_in_the_chamber():
    killed: set[str] = set()
    found = progress(killed, HARROGATH)
    loop = Loop(kind=BAAL)

    assert next_leg(at(HARROGATH), found, loop) == TO_THE_KEEP
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_KEEP  # a game begun there, or after a session
    assert next_leg(at(1), found, loop) == TO_THE_KEEP  # any other town: its waypoint
    found.note(GAME, WORLDSTONE_KEEP_2)
    assert next_leg(at(WORLDSTONE_KEEP_2), found, loop) == DOWN_THE_KEEP
    found.note(GAME, WORLDSTONE_KEEP_3)
    assert next_leg(at(WORLDSTONE_KEEP_3), found, loop) == DOWN_THE_KEEP
    found.note(GAME, THRONE)
    assert next_leg(at(THRONE), found, loop) == FIGHT_THRONE  # the stand first
    found.stood(THRONE, 'Throne')
    assert next_leg(at(THRONE), found, loop) == FIGHT_THRONE  # the waves, Lister's the last
    killed.add(LISTER)
    assert next_leg(at(THRONE), found, loop) == PICK_UP
    found.looted(THRONE)
    assert next_leg(at(THRONE), found, loop) == TO_THE_CHAMBER
    found.note(GAME, CHAMBER)
    assert next_leg(at(CHAMBER), found, loop) == FIGHT_BAAL
    killed.add('Baal')
    assert next_leg(at(CHAMBER), found, loop) == PICK_UP
    found.looted(CHAMBER)
    assert next_leg(at(CHAMBER), found, loop) == LEAVE
    with pytest.raises(Abort, match='nothing to do in'):
        next_leg(at(LOWER_KURAST), found, loop)


def test_the_throne_never_goes_to_the_chamber_while_its_waves_are_owed():
    # The Chamber's portal opens only once Baal walked into it, after the fifth wave (hunting/throne.py): with Lister
    # alive every Throne leg is the waves' level run, bounded by REPEATS
    found = progress(set(), THRONE)
    found.stood(THRONE, 'Throne')
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    posted: list[str] = []
    hands = LegHands(
        lambda: None, lambda: False, fight=lambda: posted.append('fight'), way_on=lambda: posted.append('way')
    )
    play = Game(at(THRONE))
    for _ in range(REPEATS[FIGHT_THRONE]):
        assert loop.leg(play.run(), keys, found, hands) == FIGHT_THRONE
    assert posted == ['fight'] * REPEATS[FIGHT_THRONE]
    with pytest.raises(Abort, match='again and again'):
        loop.leg(play.run(), keys, found, hands)


def test_the_loops_run_on_the_throne_waits_for_the_waves_at_the_stand_as_the_zones_does(monkeypatch):
    # hunting/choice.py `goal`: the Throne's waves for the KP_6 loop's runs too (2026-10-25), not for a KP_1 press
    from inventory_tracking.macros.goals import Goal
    from inventory_tracking.macros.hunt import Bearings
    from inventory_tracking.macros.hunting import choice, throne
    from inventory_tracking.macros.pursuit import FULL, Pursuit
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import FIGHT, fight
    from tests.inventory_tracking.macros.test_hunt import game, hunter, me

    stand = (15080.0, 5015.0)  # the Throne mark of the takes of 2026-10-11 to 2026-10-20
    play = game(area=throne.THRONE)
    play.world = replace(play.world, player=replace(me(play.world), x=stand[0] + 1, y=stand[1]))
    hunt = hunter(play)
    hunt.bearings = Bearings(marks=lambda label: ((3016.0, 1003.0),) if label == 'Throne' else ())
    stage = fight(LISTER)
    seek = Goal(f'seek {LISTER}: toward an unexplored room', (15150.0, 5130.0), FIGHT, 20.0, PRESSED,
                known=False, route='Baal', stage=stage)  # fmt: skip
    monkeypatch.setattr(choice.route, 'staged', lambda progress, area: ('Baal', stage))
    monkeypatch.setattr(choice, 'goal_of', lambda *_a, **_k: seek)
    run = play.run()
    run.clock = lambda: 100.0

    # the Baal kind's fight leg: running/legs.py `_loop_level_run(hunter, rush=False)`
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, rush=False, looped=True)
    found = hunt.goal(run, play.world, [], False, hunt.pursuit)
    assert found is not None
    assert found.label.endswith(throne.WAVES_STAND)
    assert hunt.waves.due(100.0)  # the no-move watchdog waits with it (loop.py `still`)
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL)  # a KP_1 press: the route's goal as before
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) == seek


def test_baals_drops_are_waited_for_in_the_chamber_but_lister_s_loot_on_the_throne_is_not(monkeypatch):
    # As her level's (test_loop.py): Save and Exit 0.6 s after Andariel's kill once; drops land through the death
    monkeypatch.setattr(looping, 'KILLED_AT', {})  # no kill the service saw: DROPS_LAND from the first loot leg
    killed = {LISTER, 'Baal'}
    found = progress(killed, THRONE)
    found.stood(THRONE, 'Throne')
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    hands = LegHands(lambda: None, lambda: False)

    play = Game(at(THRONE))
    run = play.run()
    begun = run.clock()
    assert loop.leg(run, keys, found, hands) == PICK_UP
    assert run.clock() - begun < 0.5  # Lister's: no boss wait on the Throne (`Kind.lair`)
    assert loop.fought is None
    assert next_leg(at(THRONE), found, loop) == TO_THE_CHAMBER

    found.note(GAME, CHAMBER)
    play = Game(at(CHAMBER))
    run = play.run()
    begun = run.clock()
    assert loop.leg(run, keys, found, hands) == PICK_UP
    assert run.clock() - begun >= looping.DROPS_LAND - 0.01  # waited from the Chamber's first loot leg
    assert next_leg(at(CHAMBER), found, loop) == PICK_UP  # the ground looked at again
    assert loop.leg(run, keys, found, hands) == PICK_UP
    assert next_leg(at(CHAMBER), found, loop) == LEAVE  # landed, nothing: left


def test_a_click_on_the_shut_portal_makes_the_leg_again_and_is_no_stop():
    # teleport.py `baal_gone`: "the throne hall is not clear: fought first", "Baal did not leave his throne": the next
    # way on's level run fights the hall or waits (running/legs.py `_way_on`), REPEATS bounding it
    from inventory_tracking.macros.teleport import Untook

    found = progress({LISTER}, THRONE)
    found.stood(THRONE, 'Throne')
    found.looted(THRONE)
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    tried: list[int] = []

    def way_on() -> None:
        tried.append(1)
        raise Untook('Worldstone Chamber: the throne hall is not clear: fought first')

    hands = LegHands(lambda: None, lambda: False, way_on=way_on)
    play = Game(at(THRONE))
    for _ in range(REPEATS[TO_THE_CHAMBER]):
        assert loop.leg(play.run(), keys, found, hands) == TO_THE_CHAMBER
    assert len(tried) == REPEATS[TO_THE_CHAMBER]
    with pytest.raises(Abort, match='again and again'):
        loop.leg(play.run(), keys, found, hands)


def test_a_baal_game_trades_in_the_fortress_and_trips_home_to_harrogath():
    # The player, 2026-10-18: "inventory management and trading - same as LK"; "one game can do several trips"
    found = progress({LISTER}, HARROGATH)
    loop = Loop(kind=BAAL, free=TRADE_ROOM - 1, carrying=True)
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TOWN
    loop.carrying = False
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_KEEP

    loop = Loop(kind=BAAL, trip_due=True)
    assert next_leg(at(THRONE), found, loop) == TRIP
    loop.trip_due, loop.trip = False, GAME  # (the leg's own)
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_FORTRESS
    loop.fortressed = GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_HARROGATH
    assert next_leg(at(HARROGATH), found, loop) == THROUGH_PORTAL
    loop.returned = GAME
    assert next_leg(at(THRONE), found, loop) == FIGHT_THRONE  # back to the waves


def test_the_gheeds_swap_of_a_baal_game_goes_by_harrogath():
    from inventory_tracking.macros.charms import Parked
    from inventory_tracking.macros.loop import CHOOSE, GHEED_CHOOSE, GHEED_STASH, OUT, PICK, RETURN, SWAP_BACK, SWAP_OUT

    found = progress({'Baal'}, CHAMBER)
    loop = Loop(kind=BAAL, swap_due=True)
    assert next_leg(at(CHAMBER), found, loop) == SWAP_OUT
    loop.swap_due, loop.swap, loop.gheed = False, GAME, OUT
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_STASH
    loop.parked, loop.gheed = Parked(1, 2, (620, 0, 0), 31), PICK
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_HARROGATH
    assert next_leg(at(HARROGATH), found, loop) == THROUGH_PORTAL
    loop.fresh = True
    assert next_leg(at(CHAMBER), found, loop) == SWAP_BACK
    loop.gheed = CHOOSE
    assert next_leg(at(HARROGATH), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_CHOOSE
    loop.parked, loop.gheed, loop.fresh = None, RETURN, False
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_HARROGATH
    assert next_leg(at(HARROGATH), found, loop) == THROUGH_PORTAL
    loop.gheed = None
    found.looted(CHAMBER)
    assert next_leg(at(CHAMBER), found, loop) == LEAVE
    loop.done = GAME  # a game given up from town: left there
    assert next_leg(at(HARROGATH), found, loop) == LEAVE


def test_the_waypoint_legs_travel_to_the_keep_and_home_to_harrogath(monkeypatch):
    went: list[int] = []
    monkeypatch.setattr(looping, 'travel', lambda run, area, marks=None: went.append(area))
    monkeypatch.setattr(looping, 'gold', lambda run: 500_000)
    found = progress(set(), HARROGATH)
    loop = Loop(kind=BAAL, prebuffed=GAME, chosen=True)
    loop.start()
    hands = LegHands(lambda: None, lambda: False)
    with suppress(Abort):
        assert loop.leg(Game(at(HARROGATH)).run(), keys, found, hands) == TO_THE_KEEP
    loop.trip, loop.fortressed = GAME, GAME  # a trip's session over
    found.note(GAME, PANDEMONIUM_FORTRESS)
    with suppress(Abort):
        assert loop.leg(Game(at(PANDEMONIUM_FORTRESS)).run(), keys, found, hands) == TO_HARROGATH
    assert went == [WORLDSTONE_KEEP_2, HARROGATH]
