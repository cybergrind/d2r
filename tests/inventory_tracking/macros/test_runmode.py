"""The pickup key's run mode (macros/runmode.py; the player's ruling of 2026-10-14, rca/2026-10-14/kp1-mode.md):
the level's goal, clearing the way, by default; a full clear on a terror zone or after a double press of the key,
for the level it was made on. The River of Flame's run goes to the Chaos Sanctuary's door and ends there."""

import json
import logging
import math
from dataclasses import replace
from pathlib import Path

from inventory_tracking.builds import pursuing
from inventory_tracking.builds.warlock.movement import BLADE_WARP_SOURCE
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros import goals
from inventory_tracking.macros.build import MoveFacts, NoWay, Step
from inventory_tracking.macros.goals import (
    CLEAR_WAY,
    REACH,
    Goal,
    boss_ahead,
    clear_way,
    rest_of_level,
)
from inventory_tracking.macros.hunt import BOSS_AHEAD, CLEAR_SECONDS, Bearings
from inventory_tracking.macros.pursuit import FULL, Defer, Ended, Facts, Hold, Move, Pursuit, decide
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.runmode import (
    DOUBLE,
    SWITCHED,
    TERROR,
    Mode,
    Taps,
    aim_of,
    badge,
    doubled,
    doubles,
    mode_of,
    said,
    tapped,
)
from inventory_tracking.macros.travel import AROUND_LEAST, NO_SPOT_ON_WAY, PRESSED, way_leg
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, USE, Script
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter


RIVER, SANCTUARY = 107, 108
STEP = Step((1.0, 1.0), None)


def presses(*at: float) -> Taps:
    taps = Taps()
    for each in at:
        taps = tapped(taps, each)
    return taps


def scripts() -> dict[int, Script]:
    return {script.area: script for route in ROUTES for script in route.scripts}


# -- the double press ---------------------------------------------------------------------------------------------


def test_two_presses_within_the_window_are_a_double_press_once_the_window_after_them_is_over() -> None:
    pair = presses(10.0, 10.23)  # the player's own pairs came 0.20 to 0.29 s apart
    assert not doubled(pair, 10.23 + DOUBLE)  # a third may still come
    assert doubled(pair, 10.23 + DOUBLE + 0.01)
    assert not doubled(replace(pair, judged=True), 20.0)  # acted on once


def test_a_mashed_key_or_two_presses_apart_switch_nothing() -> None:
    assert not doubled(presses(10.0, 10.25, 10.5), 20.0)  # three: a mashed key
    assert not doubled(presses(10.0, 10.25, 10.5, 10.75), 20.0)
    assert not doubled(presses(10.0, 10.0 + DOUBLE + 0.05), 20.0)  # two presses, each its own
    assert presses(10.0, 10.25, 10.5, 11.0) == Taps(11.0, 11.0, 1)  # a press after the window starts a new group
    # ... and a double press it ends that no look acted on is owed: its window closed by the clock
    assert presses(10.0, 10.2, 11.0) == Taps(11.0, 11.0, 1, owed=((10.0, 10.2),))


def test_a_double_press_is_judged_by_the_clock_whether_or_not_a_look_came_in_its_window() -> None:
    """The game of 22:04 on 2026-10-14 (run-1904-findings.md §3.3): two of the player's pairs (22:07:19.30/19.52
    and 31.07/31.23) were lost: no look came in their windows (a Blade Warp in flight, then the run paused for the
    player's hand), and the next press 1.2 s and 2.3 s later began a new group over them."""
    taps = presses(19.30, 19.52, 20.72)
    found, after = doubles(taps, 20.80)
    assert found == ((19.30, 19.52),)  # owed: the next look acts on it
    assert after == Taps(20.72, 20.72, 1)  # acted on once
    assert doubles(after, 30.0) == ((), after)
    both = presses(19.30, 19.52, 20.72, 31.07, 31.23)
    found, after = doubles(both, 31.23 + DOUBLE + 0.01)
    assert found == ((19.30, 19.52), (31.07, 31.23))  # each, in the order made
    assert after.judged
    assert doubles(presses(10.0, 10.25, 10.5, 11.0), 20.0)[0] == ()  # a mash owes nothing


# -- the mode -----------------------------------------------------------------------------------------------------


def test_the_goal_by_default_a_full_clear_on_a_terror_zone_and_the_switch_for_its_own_level_only() -> None:
    assert mode_of(RIVER, None, None) == Mode(False)
    assert mode_of(RIVER, False, None) == Mode(False)
    assert mode_of(RIVER, True, None) == Mode(True, TERROR)
    assert mode_of(RIVER, False, (RIVER, True)) == Mode(True, SWITCHED)
    assert mode_of(RIVER, True, (RIVER, False)) == Mode(False, SWITCHED)  # a terror zone run to its goal
    assert mode_of(SANCTUARY, False, (RIVER, True)) == Mode(False)  # switched on another level


def test_the_log_says_where_the_run_goes_and_the_hud_a_word_for_a_full_clear() -> None:
    levels = scripts()
    assert aim_of(levels[RIVER]) == 'Chaos Sanctum'
    assert aim_of(levels[SANCTUARY]) == 'Diablo'
    assert aim_of(None) is None
    assert said(Mode(False), 'Chaos Sanctum') == 'to Chaos Sanctum, clearing the way'
    assert said(Mode(True, TERROR), 'Diablo') == 'full clear (terror zone)'
    assert said(Mode(True, SWITCHED), None) == 'full clear (switched by the player)'
    assert said(Mode(False, SWITCHED), 'Diablo') == 'to Diablo, clearing the way (switched by the player)'
    assert (badge(Mode(False)), badge(Mode(True, TERROR)), badge(Mode(True, SWITCHED)), badge(None)) == (
        None, 'CLEAR TZ', 'CLEAR', None,
    )  # fmt: skip


# -- the goals ----------------------------------------------------------------------------------------------------


DOOR = Goal('Chaos Sanctum', (5000.0, 5300.0), ENTER, goals.PLACE_NEAR, PRESSED, route='Diablo')


def test_what_is_on_the_way_is_fought_first_and_the_route_kept() -> None:
    near = [foe(31, 5010.0, 5000.0), foe(32, 5020.0, 5000.0)]
    found = clear_way(DOOR, (5000.0, 5000.0), near, 22.0)
    assert (found.do, found.unit, found.near, found.route, found.clearing) == (FIGHT, 31, 22.0, 'Diablo', True)
    assert found.label == 'Chaos Sanctum: clearing the way (2 near)'


def test_a_full_clears_goal_is_a_monster_fought_or_a_room_gone_to() -> None:
    monster = rest_of_level(((10.0, 0.0), 'Fallen', 7), None, 22.0, PRESSED)
    assert (monster.do, monster.unit, monster.near, monster.route, monster.clearing) == (FIGHT, 7, 22.0, '', True)
    room = rest_of_level(((50.0, 0.0), 'an unexplored room', None), DOOR, 22.0, PRESSED)
    assert (room.do, room.unit, room.known, room.route, room.label) == (
        REACH, None, False, 'Diablo', 'full clear: an unexplored room',
    )  # fmt: skip


def test_the_stages_that_bring_a_boss_are_its_fight_and_the_last_seal_of_its_arm() -> None:
    stages = scripts()[SANCTUARY].stages
    named = {stage.text(): boss_ahead(stages, stage) for stage in stages}
    assert named['use Vizier seal 1'] is False
    assert named['use Vizier seal 2'] is True
    assert named['use De Seis seal'] is True
    assert named['use Infector seal 1'] is False
    assert named['use Infector seal 2'] is True
    assert named['fight Diablo'] is True
    assert named['loot'] is False
    (door,) = scripts()[RIVER].stages
    assert not boss_ahead(scripts()[RIVER].stages, door)


# -- the decision: the River's door -------------------------------------------------------------------------------


RUN = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=RIVER)


def facts(goal, *, there=False, in_reach=False, way=lambda: STEP, now=100.0) -> Facts:
    return Facts(now, goal, there, in_reach, True, way, RIVER)


def test_the_river_run_goes_to_the_door_fights_on_the_way_and_ends_there() -> None:
    """The game of 15:13 on 2026-10-14 (run-1214-findings.md §3.8): every press in the River was one sweep, 15 of
    them in 54 s. The run now goes to the Chaos Sanctuary's door itself; going through takes a press (U13)."""
    assert decide(facts(DOOR), RUN) == Move(STEP, DOOR)
    assert decide(facts(DOOR, in_reach=True), RUN) == Hold(DOOR)
    assert decide(facts(DOOR, there=True), RUN) == Ended('at Chaos Sanctum: going through takes a press')
    arrived = facts(DOOR, way=lambda: NoWay('there', arrived=True))
    assert decide(arrived, RUN) == Ended('at Chaos Sanctum: going through takes a press')
    pressed = replace(RUN, pressed_at=100.0)  # a fresh pickup press: the run, not the old sweep
    assert decide(facts(DOOR), pressed) == Move(STEP, DOOR)
    assert decide(facts(DOOR, there=True), pressed) == Defer(DOOR)  # at the door: the key's own step, as before
    assert decide(facts(DOOR), replace(RUN, key='teleport', pressed_at=100.0, advance=True)) == Defer(DOOR)


def test_the_river_door_run_ends_where_no_step_toward_the_door_is_left() -> None:
    """22:08:45 on 2026-10-14 (run-1904-findings.md §3.4): a pad warp landed at (7797.2, 5602.2), 5.5 units from the
    door's mark, 0.5 past the door goal's PLACE_NEAR of 5, and the run stood there 23 s: "No way toward Chaos Sanctum:
    no spot on the walked way ...". On the ground the game had loaded (the take's), the way's last cell is 3.7 units
    off at the edge of the loaded rooms, which no straight walk reaches, and a pad warp is 15-19 units long. The rule
    is the goal's, not the River's: a way with no step left, the goal nearer than the shortest move (AROUND_LEAST)
    past its arrival distance, is an arrival."""
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'river-door-ground.json').read_text())
    ground = Ground(tuple(Walkable(**grid) for grid in fixture['ground']))
    mark, here = (7800.0, 5597.5), (7797.2, 5602.2)
    move = MoveFacts(here, 100.0, (BLADE_WARP,), None, ground, (), 2560 / 1418, pad=True)
    leg = way_leg(move, mark, PRESSED, jumps=(BLADE_WARP_SOURCE.pad_jump(),))
    assert leg == NoWay(NO_SPOT_ON_WAY)  # the navigator as the game had it: no move from here
    door = replace(DOOR, place=mark)
    stood = replace(facts(door, way=lambda: leg), beyond=math.dist(here, mark) - door.near, least_move=AROUND_LEAST)
    assert decide(stood, RUN) == Ended(
        f'at Chaos Sanctum (no step toward it is left, 0.5 units past its 5: {NO_SPOT_ON_WAY}): going through takes '
        'a press'
    )
    assert decide(replace(stood, beyond=AROUND_LEAST + 0.1), RUN) == NoWay(
        f'no way toward Chaos Sanctum: {NO_SPOT_ON_WAY}'
    )
    place = Goal('the mark', mark, goals.REACH, goals.PLACE_NEAR, PRESSED, route='a route')  # any place goal
    assert decide(replace(stood, goal=place), RUN) == NoWay(
        f'at the mark (no step toward it is left, 0.5 units past its 5: {NO_SPOT_ON_WAY})', arrived=True
    )


def test_a_full_clear_works_a_level_with_no_route_and_its_end_is_the_runs() -> None:
    room = rest_of_level(((50.0, 0.0), 'an unexplored room', None), None, 22.0, PRESSED)
    assert decide(facts(room), RUN) == Move(STEP, room)
    assert isinstance(decide(facts(None), RUN), Ended)  # nothing left: the level is clear


# -- the hunt: the mailbox, the mode at a look, the clearing goal -------------------------------------------------


def test_a_double_press_switches_the_level_to_a_full_clear_and_both_presses_run_it(caplog) -> None:
    play = game(area=RIVER)
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: False))
    run = play.run()
    hunt.post(Pursuit('pickup', 10.0, advance=False, leash=FULL))
    hunt.post(Pursuit('pickup', 10.24, advance=False, leash=FULL))
    assert hunt.pursuit is not None
    assert (hunt.pursuit.pressed_at, hunt.pursuit.leash) == (10.24, FULL)  # the second press keeps the run
    with caplog.at_level(logging.INFO):
        play.clock.now = 10.3
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(False)  # the window is not over
        play.clock.now = 10.24 + DOUBLE + 0.01
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, SWITCHED)
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, SWITCHED)  # once a double press
        assert hunt.run_mode(run, SANCTUARY, hunt.pursuit) == Mode(False)  # another level: the switch lapses
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(False)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: run:')]
    assert lines == [
        'Macro: run: to Chaos Sanctum, clearing the way',
        'Macro: run: a double press of the pickup key (0.24 s apart): goal -> full clear',
        'Macro: run: full clear (switched by the player)',
        'Macro: run: to Diablo, clearing the way',
        'Macro: run: to Chaos Sanctum, clearing the way',
    ]


def test_a_pair_no_look_came_in_the_window_of_still_switches_the_level(caplog) -> None:
    """A double press while the run was looking elsewhere (a warp in flight, the hand's pause) and a press after its
    window: the next look switches the level all the same, said with how late."""
    play = game(area=RIVER)
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: False))
    run = play.run()
    for at in (19.30, 19.52, 20.72):
        hunt.post(Pursuit('pickup', at, advance=False, leash=FULL))
    with caplog.at_level(logging.INFO):
        play.clock.now = 20.80
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, SWITCHED)
        play.clock.now = 25.0
        assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, SWITCHED)  # once
    lines = [r.getMessage() for r in caplog.records if 'double press' in r.getMessage()]
    assert lines == [
        'Macro: run: a double press of the pickup key (0.22 s apart, its window closed 0.93 s before this look): '
        'goal -> full clear'
    ]


def test_a_mashed_pickup_key_switches_nothing_and_a_terror_zone_is_a_full_clear() -> None:
    play = game(area=RIVER)
    hunt = hunter(play)
    hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: area == RIVER))
    run = play.run()
    for at in (10.0, 10.25, 10.5):
        hunt.post(Pursuit('pickup', at, advance=False, leash=FULL))
    play.clock.now = 20.0
    assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, TERROR)
    hunt.post(Pursuit('teleport', 20.1))  # the teleport key is no press of the pickup key's
    hunt.post(Pursuit('teleport', 20.2))
    play.clock.now = 30.0
    assert hunt.run_mode(run, RIVER, hunt.pursuit) == Mode(True, TERROR)


def test_a_run_to_its_goal_fights_what_is_on_its_way_and_passes_what_it_cannot_strike(caplog) -> None:
    play = game(area=RIVER)
    hunt = hunter(play)
    run = play.run()
    hunt.mode = Mode(False)
    ground = Ground(())
    near, far = foe(31, 5010.0, 5000.0), foe(32, 5000.0 + CLEAR_WAY + 5.0, 5000.0)
    play.clock.now = 50.0
    found = hunt.cleared(run, play.world, [near, far], ground, DOOR)
    assert found is not None
    assert (found.do, found.unit, found.clearing, found.route) == (FIGHT, 31, True, 'Diablo')
    assert hunt.cleared(run, play.world, [far], ground, DOOR) == DOOR  # off the way: not gone for
    # A goal of the route's own that is a fight, a drop or a level with no route keeps its goal
    fight = replace(DOOR, do=FIGHT, unit=99)
    assert hunt.cleared(run, play.world, [near], ground, fight) is fight
    no_route = replace(DOOR, route='')
    assert hunt.cleared(run, play.world, [near], ground, no_route) is no_route
    # The way to an object is not cleared first: a seal calls its pack, and what stands at it is priced there (the
    # arena's seal moment, test_pursuit_situations.py: the 12 by Vizier seal 1 fought first left the Vizier alive)
    seal = replace(DOOR, label='Vizier seal 1', do=USE, near=goals.USE_NEAR)
    assert hunt.cleared(run, play.world, [near], ground, seal) is seal
    hunt.mode = Mode(True, SWITCHED)  # a full clear clears it all first
    assert getattr(hunt.cleared(run, play.world, [near], ground, seal), 'unit', None) == 31
    hunt.mode = Mode(False)
    # The same monster as the goal CLEAR_SECONDS with no strike: passed, and the run goes on to the door
    hunt.cleared(run, play.world, [near], ground, DOOR)
    play.clock.now = 50.0 + CLEAR_SECONDS + 0.1
    with caplog.at_level(logging.INFO):
        assert hunt.cleared(run, play.world, [near], ground, DOOR) == DOOR
    assert 'Macro: run: passing Chaos Sanctum: clearing the way (1 near)' in caplog.text
    hunt.struck_at = play.clock.now  # a strike keeps it the goal
    other = foe(33, 5012.0, 5000.0)
    hunt.cleared(run, play.world, [other], ground, DOOR)
    play.clock.now += CLEAR_SECONDS
    assert getattr(hunt.cleared(run, play.world, [other], ground, DOOR), 'unit', None) == 33


def test_a_full_clear_goes_for_what_is_in_sight_then_what_is_remembered_before_the_route() -> None:
    play = game(area=RIVER)
    hunt = hunter(play, remembered=[(41, 5200.0, 5000.0, False)])
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    seen = foe(31, 5000.0 + CLEAR_WAY + 20.0, 5000.0)  # in sight, off the way
    found = hunt.cleared(run, play.world, [seen], ground, DOOR)
    assert found is not None
    assert (found.do, found.unit, found.route) == (FIGHT, 31, 'Diablo')
    remembered = hunt.cleared(run, play.world, [], ground, DOOR)
    assert remembered is not None
    assert (remembered.do, remembered.unit, remembered.place) == (FIGHT, 41, (5200.0, 5000.0))
    assert getattr(hunt.cleared(run, play.world, [], ground, None), 'unit', None) == 41  # a level with no route too


def test_the_buffs_are_asked_with_a_boss_ahead_at_the_last_seal_and_the_fight() -> None:
    play = game(area=SANCTUARY)
    hunt = hunter(play)
    dead: set[str] = set()
    progress = Progress(ROUTES, PERFORMED, dead=lambda: frozenset(dead))
    progress.note('game', SANCTUARY)
    hunt.bearings = Bearings(progress)
    assert hunt.ahead(SANCTUARY) == 0.0  # Vizier seal 1
    progress.used(SANCTUARY, 'Vizier seal 1', (1.0, 1.0), ((1.0, 1.0),))
    assert hunt.ahead(SANCTUARY) == BOSS_AHEAD  # Vizier seal 2 calls the Grand Vizier
    assert hunt.ahead(RIVER) == 0.0
    assert hunt.ahead(None) == 0.0
    assert math.isclose(BOSS_AHEAD, 60.0)


def test_the_runner_gives_the_hud_the_run_modes_word_and_none_in_town() -> None:
    import threading
    from pathlib import Path

    from inventory_tracking.macros.runner import MacroRunner
    from tests.inventory_tracking.macros.fakes import BUILD

    made = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path(), execute=lambda cancelled, routine: None)
    try:
        assert made.run_badge is None  # no hunt
        made.hunter = hunter(game(area=RIVER))
        made.build = made.fallback = BUILD
        assert made.run_badge is None  # before any look
        made.hunter.mode = Mode(True, TERROR)
        assert made.run_badge == 'CLEAR TZ'
        made.hunter.mode = Mode(False)
        assert made.run_badge is None
    finally:
        made.close()
