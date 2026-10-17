"""The pickup key's run mode (macros/runmode.py; the player's ruling of 2026-10-14, rca/2026-10-14/kp1-mode.md):
the level's goal, clearing the way, by default; a full clear on a terror zone or after a double press of the key,
for the level it was made on. A run ends at a door (a warp); the River of Flame's way into the Chaos Sanctuary is an
open passage, walked through (2026-10-15)."""

import json
import logging
import math
from dataclasses import replace
from functools import partial
from pathlib import Path

from inventory_tracking.builds import pursuing
from inventory_tracking.builds.warlock.movement import BLADE_WARP_SOURCE, MOVEMENT
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.levels.exits import passage_of
from inventory_tracking.levels.handlers.river_of_flame import bridge_end
from inventory_tracking.levels.model import Ground, Room, Target, Walkable
from inventory_tracking.levels.presets import open_passage
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
from inventory_tracking.macros.hunt import BOSS_AHEAD, CLEAR_SECONDS, REMEMBERED_NEAR, REST_SECONDS, Bearings
from inventory_tracking.macros.movement import HOPS, TELEPORT, WALKS, WARPS, Ways
from inventory_tracking.macros.pursuit import (
    ENTERING,
    ENTERING_SAID,
    FULL,
    NONE,
    PASSAGE,
    Defer,
    Ended,
    Facts,
    Hold,
    Move,
    Pursuit,
    carried,
    decide,
    heading,
)
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
from inventory_tracking.macros.travel import AROUND_LEAST, NO_SPOT_ON_WAY, PRESSED, navigator, way_leg
from inventory_tracking.macros.world import VALUABLE, Drop
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, USE, Script
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.test_hunt import EAST, ROOMS, foe, game, hunter, me


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
    them in 54 s. The run now goes to the Chaos Sanctuary's door itself; going through a door takes a press (U13).
    `DOOR` has no mark, so no open passage: a warp's way out. The River's own is walked through (below)."""
    assert decide(facts(DOOR), RUN) == Move(STEP, DOOR)
    assert decide(facts(DOOR, in_reach=True), RUN) == Hold(DOOR)
    assert decide(facts(DOOR, there=True), RUN) == Ended('at Chaos Sanctum: going through takes a press')
    arrived = facts(DOOR, way=lambda: NoWay('there', arrived=True))
    assert decide(arrived, RUN) == Ended('at Chaos Sanctum: going through takes a press')
    pressed = replace(RUN, pressed_at=100.0)  # a fresh pickup press: the run, not the old sweep
    assert decide(facts(DOOR), pressed) == Move(STEP, DOOR)
    assert decide(facts(DOOR, there=True), pressed) == Defer(DOOR)  # at the door: the key's own step, as before
    # The teleport key in the run (rca/2026-10-14/run-1932-findings.md §1.2.2): the run's way to the door, the
    # route's step for the click at it
    kp4 = replace(RUN, key='teleport', pressed_at=100.0, advance=True)
    assert decide(facts(DOOR), kp4) == Move(STEP, DOOR)
    assert decide(facts(DOOR, there=True), kp4) == Defer(DOOR)


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
    pad_jump = BLADE_WARP_SOURCE.pad_jump()
    assert pad_jump is not None
    leg = way_leg(move, mark, PRESSED, jumps=(pad_jump,))
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


def river_door() -> tuple[dict, tuple[Room, ...]]:
    """The take's ground and rooms at the River of Flame's bridge end (fixtures/river-door-ground.json)."""
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'river-door-ground.json').read_text())
    return fixture, tuple(Room.from_row(row) for row in fixture['rooms'])


# The River's take 20261014T190527Z-107 six seconds before the player's own crossing (7835.9, 5625.5), the 22:08:45
# stand by the door (7797.2, 5602.2), and a place on the bridge further back (7815.5, 5626.5)
BRIDGE = ((7835.9, 5625.5), (7797.2, 5602.2), (7815.5, 5626.5))
CLASSES = {  # a navigation class's skills on keys, and controller mode
    HOPS: ((TELEPORT, BLADE_WARP), False),
    WARPS: ((BLADE_WARP,), True),
    WALKS: ((), False),
}


def test_the_river_run_walks_through_the_open_passage_into_the_chaos_sanctuary() -> None:
    """The player, 2026-10-15: "River of Flame map with full auto: the player doesn't go to the Chaos Sanctuary when
    only KP_1 was pressed; we need to move our target slightly further so the map changes to the Chaos Sanctuary".
    No warp joins the River and the Sanctuary (levels.txt Warp1 -1): the goal of its way out is a tile inside the
    Sanctuary, past the bridge's end, which no ground of the River's reaches. By every navigation class (and the
    pad's Blade Warp) the run goes as near as the River's ground goes, walks across from there, and the level
    changed ends it. On the take's own ground the walk's end is the Sanctuary's floor (the next take, area 108)."""
    fixture, rooms = river_door()
    river, beyond = Ground(tuple(Walkable(**g) for g in fixture['ground'])), fixture['beyond']
    sanctuary = Ground(tuple(Walkable(**g) for g in beyond['ground']))
    mark = bridge_end(rooms)
    assert mark is not None
    assert (mark.spot, mark.area, beyond['area']) == ((1560.0, 1119.5), SANCTUARY, SANCTUARY)
    assert open_passage(RIVER, SANCTUARY)
    assert mark.spot is not None
    far = passage_of(RIVER, rooms, mark, mark.spot)
    card = Target(RIVER, rooms, mark.spot, mark.label, mark.kind, True, river.grids, 0, far)
    (stage,) = scripts()[RIVER].stages
    goal = goals.route_goal(BRIDGE[0], spend=PRESSED, reach=22.0, stage=stage, route='Diablo', card=card)
    assert goal is not None
    assert (goal.do, goal.place, goal.near, goal.crossed) == (ENTER, (7800.0, 5595.0), goals.PASSAGE_NEAR, True)
    assert (river.walkable(*goal.place), sanctuary.walkable(*goal.place)) == (None, True)  # the Sanctuary's floor
    walk = Move(Step(goal.place), goal, f'Chaos Sanctum: {PASSAGE}')
    for kind, (slots, pad) in CLASSES.items():
        for start in BRIDGE:
            here, legs = start, 0
            while True:
                move = MoveFacts(
                    here, 100.0 + legs * 3, slots, None, river, (), 2560 / 1418, area=RIVER, rooms=rooms, pad=pad
                )
                movement = navigator(MOVEMENT, move)
                assert isinstance(movement, Ways)  # the build's sets: `means` and `routed` are theirs
                assert movement.means(move, goal.place, PRESSED) == kind
                gap = goal.gap(here)
                way = partial(movement.routed, move, goal.place, PRESSED)
                looked = Facts(
                    100.0, goal, gap <= goal.near, False, True, way, RIVER,
                    beyond=max(gap - goal.near, 0.0), least_move=AROUND_LEAST,
                )  # fmt: skip
                act = decide(looked, RUN)
                assert isinstance(act, Move), (kind, start, here, act)
                if act == walk:
                    break
                here, legs = act.step.spot, legs + 1
                assert legs < 12, (kind, start, here)
            assert river.walkable(*here)  # the walk across begins on the River's ground
    assert card.into is None  # this card names no level behind the passage: the run is not carried on
    crossed = Facts(101.0, goal, False, False, True, lambda: NoWay('not asked'), SANCTUARY)
    assert decide(crossed, RUN) == Ended('the level was left')
    onward = heading(RUN, goals.route_goal(BRIDGE[0], spend=PRESSED, reach=22.0, stage=stage, route='Diablo',
                                           card=replace(card, into=SANCTUARY)))  # fmt: skip
    assert onward is not None
    assert onward.onward == SANCTUARY
    on = carried(onward, SANCTUARY, 101.0)  # the level guide's card names it: the Sanctuary's run goes on
    assert on is not None
    assert (on.area, on.onward, on.entered) == (SANCTUARY, None, 101.0)
    door = replace(card, passage=None)  # a warp's way out (stairs, a door): its mark, and going through is a press
    stairs = goals.route_goal(BRIDGE[1], spend=PRESSED, reach=22.0, stage=stage, route='Diablo', card=door)
    assert stairs is not None
    assert (stairs.place, stairs.near, stairs.crossed) == ((7800.0, 5597.5), goals.PLACE_NEAR, False)
    assert decide(facts(stairs, there=True), RUN) == Ended('at Chaos Sanctum: going through takes a press')


CROSSING = Target(RIVER, (), (1560.0, 1119.5), 'Chaos Sanctum', 'next', True, (), 0, (1560.0, 1119.0), SANCTUARY)


def test_a_run_whose_way_out_is_an_open_passage_goes_on_into_the_level_it_leads_to_once() -> None:
    """The player, 2026-10-15: one KP_1 in the River of Flame "should carry into the Chaos Sanctuary run". The rule is
    the way out's, not the River's: a level run whose goal is its level's open passage notes the level behind it
    (`heading`), and the level change into that level carries the run on (`carried`), once. Any other change of level
    (a waypoint, the town) ends it, as does a door's way out (going through takes a press)."""
    goal = goals.way_out(CROSSING, 'Chaos Sanctum', PRESSED, 'Diablo', None)
    assert goal.crossed
    noted = heading(RUN, goal)
    assert noted is not None
    assert noted == replace(RUN, onward=SANCTUARY)
    assert heading(noted, goal) is None  # noted once
    assert heading(replace(RUN, leash=NONE), goal) is None  # no level run: the teleport key's own press
    assert heading(RUN, goals.way_out(replace(CROSSING, passage=None), 'Chaos Sanctum', PRESSED, '', None)) is None
    assert heading(RUN, DOOR) is None  # a door: going through is a press, and the run ends at it
    assert heading(RUN, None) is None
    # The crossing carries the run, working or paused as it was, into the level the passage leads into only
    assert carried(noted, RIVER, 50.0) is None  # still on the River
    on = carried(noted, SANCTUARY, 50.0)
    assert on is not None
    assert on == replace(RUN, area=SANCTUARY, entered=50.0)
    assert carried(replace(noted, paused=True), SANCTUARY, 50.0) == replace(on, paused=True)
    assert carried(noted, 103, 50.0) is None  # the town: the Pandemonium Fortress
    assert carried(noted, 106, 50.0) is None  # the City of the Damned by its waypoint: not the way out's level
    assert carried(noted, None, 50.0) is None
    assert carried(replace(noted, leash=NONE), SANCTUARY, 50.0) is None  # the run ended: nothing to carry
    assert carried(RUN, SANCTUARY, 50.0) is None  # a run that never went for the passage: the level was left
    assert decide(Facts(51.0, None, False, False, True, lambda: STEP, SANCTUARY), RUN) == Ended('the level was left')
    # Once: the carried run is the Sanctuary's own, with no way out noted; a change on from there ends it
    assert carried(on, RIVER, 60.0) is None
    assert decide(Facts(60.0, None, False, False, True, lambda: STEP, RIVER), on) == Ended('the level was left')


def test_a_run_carried_into_a_level_waits_for_its_card_and_then_ends_for_its_own_reasons() -> None:
    """Across the passage the level guide's card is still the River's for a poll or two (hunt.py `goal`: none): the
    carried run waits ENTERING seconds for the Sanctuary's, holding what is in reach meanwhile. A run that finds nothing
    to go to after that, or whose route ends at a door, a boss dead, ends as any run does: nothing carries it on."""
    on = replace(RUN, area=SANCTUARY, entered=50.0)
    nothing = Facts(51.0, None, False, False, True, lambda: STEP, SANCTUARY)
    assert decide(nothing, on) == NoWay(ENTERING_SAID)
    assert decide(replace(nothing, in_reach=True), on) == Hold()
    later = replace(nothing, now=50.0 + ENTERING + 0.1)
    assert decide(later, on) == Ended('nothing is left to go to on this level: no route stage, no boss known')
    assert decide(later, replace(RUN, area=SANCTUARY)) == decide(later, on)  # as a run pressed on the level ends
    sanctuary = replace(DOOR, place=(7800.0, 5300.0))
    assert decide(replace(nothing, goal=sanctuary), on) == Move(STEP, sanctuary)  # the card up: the run works it
    # The River's run ended at its door (a warp) or for want of a stage noted no crossing: nothing to carry on
    ended = decide(facts(DOOR, there=True), RUN)
    assert ended == Ended('at Chaos Sanctum: going through takes a press')
    assert heading(RUN, DOOR) is None


def at(play, area: int, place: tuple[float, float]) -> None:
    play.world = replace(play.world, player=replace(me(play.world), area=area, x=place[0], y=place[1]))


def test_one_press_in_the_river_walks_across_the_passage_and_runs_the_chaos_sanctuary(caplog) -> None:
    """One KP_1 in the River of Flame (the player, 2026-10-15): the run goes for the bridge's open passage, walks
    across, and the level change into the Chaos Sanctuary carries it on, said `Macro: run: on into ...`; the
    Sanctuary's run works its first seal once its card is up. The player's full-clear switch of the River goes with
    the run (and the HUD's word), and attack mode off still ends the carried run."""
    _, rooms = river_door()
    mark = bridge_end(rooms)
    assert mark is not None
    assert mark.spot is not None
    far = passage_of(RIVER, rooms, mark, mark.spot)
    river = Target(RIVER, rooms, mark.spot, mark.label, mark.kind, True, (), 0, far, SANCTUARY)
    seal = Target(SANCTUARY, (), (1531.0, 1063.0), 'Vizier seal 1', 'target', False, (), 396)
    shown: list[Target] = [river]
    progress = Progress(ROUTES, PERFORMED, wanted=lambda area: False)
    play = game(area=RIVER)
    at(play, RIVER, BRIDGE[1])  # the 22:08:45 stand by the bridge's end, within the passage's near
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    hunt.bearings = Bearings(progress, lambda: shown[0])
    run = play.run()
    hunt.post(Pursuit('pickup', 10.0, advance=False, leash=FULL))
    play.clock.now = 20.0
    with caplog.at_level(logging.INFO):
        found = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
        assert found.goal is not None
        assert found.goal.crossed
        assert found.posted is not None
        assert found.act == Move(Step(found.goal.place), found.goal, f'Chaos Sanctum: {PASSAGE}')  # walked across
        assert hunt.pursuit == replace(found.posted, onward=SANCTUARY)
        assert found.posted.area == RIVER
        hunt.switched = (RIVER, True)  # the player's double press on the River, made on the way (`run_mode`)
        at(play, SANCTUARY, found.goal.place)  # the walk's end: the Sanctuary's floor
        play.clock.now = 21.0
        across = hunt.judge(run, play.world, [], Ground(()), in_reach=False)  # the card is still the River's
        carried_on = hunt.pursuit
        assert carried_on is not None
        assert (carried_on.area, carried_on.onward, carried_on.entered, carried_on.leash) == (
            SANCTUARY,
            None,
            21.0,
            FULL,
        )
        assert across.act == NoWay(ENTERING_SAID)
        assert hunt.mode == Mode(True, SWITCHED)  # the full clear goes on, and the HUD's word with it
        assert badge(hunt.mode) == 'CLEAR'
        shown[0] = seal
        hunt.switched = (SANCTUARY, False)  # (to its goal: the full clear would go for the rooms first)
        play.clock.now = 22.0
        started = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
        assert started.goal is not None
        assert (started.goal.label, started.goal.route) == ('Vizier seal 1', 'Diablo')
        assert not isinstance(started.act, Ended)
        hunt.judge(run, play.world, [], Ground(()), in_reach=False)
        assert hunt.pursuit is not None
        assert hunt.pursuit.area == SANCTUARY  # once: no other carrying
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: run:')]
    assert lines[:3] == [
        'Macro: run: to Chaos Sanctum, clearing the way',
        'Macro: run: on into The Chaos Sanctuary: the run of River of Flame goes on across its way out',
        'Macro: run: full clear (switched by the player)',
    ]
    assert 'Run: on into The Chaos Sanctuary' in play.said
    assert not any('the level run ends' in r.getMessage() for r in caplog.records)
    hunt.end_run(run, 'attack mode off')  # KP_3, the macro request, the game left: the runner's ends still end it
    assert hunt.pursuit is None


def test_only_a_full_clear_switch_carries_across_the_passage_and_the_next_level_decides_otherwise() -> None:
    """The player, 2026-10-15: a double-pressed full clear of the River stays a full clear in the Sanctuary; a switch
    to the goal (made on a terror-zone River) does not carry, and the Sanctuary decides by its own rules: a terror zone
    there is a full clear, else its goal."""
    river_run = replace(RUN, onward=SANCTUARY)
    on = carried(river_run, SANCTUARY, 50.0)
    assert on is not None
    for river_tz, sanctuary_tz, switch, expected in (
        (False, False, True, Mode(True, SWITCHED)),  # a full clear carries
        (False, True, True, Mode(True, SWITCHED)),
        (True, True, False, Mode(True, TERROR)),  # a switch to the goal does not: the Sanctuary's terror zone
        (True, False, False, Mode(False)),  # ... nor its goal by default
        (True, False, None, Mode(False)),  # no switch: the Sanctuary's own rules, the River's terror zone not carried
    ):
        tz = {RIVER: river_tz, SANCTUARY: sanctuary_tz}
        play = game(area=SANCTUARY)
        hunt = hunter(play)
        hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area, tz=tz: tz.get(area, False)))
        run = play.run()
        hunt.switched = None if switch is None else (RIVER, switch)
        hunt.carry_on(run, river_run, on)
        assert hunt.run_mode(run, SANCTUARY, on) == expected, (river_tz, sanctuary_tz, switch)
        assert badge(hunt.mode) == ('CLEAR TZ' if expected.why == TERROR else 'CLEAR' if expected.clear else None)


def test_a_waypoint_or_the_town_from_a_run_bound_for_the_passage_ends_it(caplog) -> None:
    """The run went for the River's passage, and the level changed some other way (the waypoint to the City of the
    Damned, the town): nothing carries it on, it ends as before."""
    for elsewhere in (106, 103):
        play = game(area=RIVER)
        at(play, RIVER, BRIDGE[1])
        hunt = hunter(play)
        hunt.build = pursuing(hunt.build)
        hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: False), lambda: CROSSING)
        run = play.run()
        hunt.post(Pursuit('pickup', 10.0, advance=False, leash=FULL))
        play.clock.now = 20.0
        hunt.judge(run, play.world, [], Ground(()), in_reach=False)
        assert hunt.pursuit is not None
        assert hunt.pursuit.onward == SANCTUARY
        at(play, elsewhere, (5000.0, 5000.0))
        found = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
        assert found.act == Ended('the level was left'), elsewhere
        assert hunt.pursuit.area == RIVER


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
    hunt = hunter(play, remembered=[(41, 5000.0 + REMEMBERED_NEAR - 5.0, 5000.0, False)])
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    seen = foe(31, 5000.0 + CLEAR_WAY + 20.0, 5000.0)  # in sight, off the way
    found = hunt.cleared(run, play.world, [seen], ground, DOOR)
    assert found is not None
    assert (found.do, found.unit, found.route) == (FIGHT, 31, 'Diablo')
    remembered = hunt.cleared(run, play.world, [], ground, DOOR)
    assert remembered is not None
    assert (remembered.do, remembered.unit, remembered.place) == (FIGHT, 41, (5000.0 + REMEMBERED_NEAR - 5.0, 5000.0))
    assert getattr(hunt.cleared(run, play.world, [], ground, None), 'unit', None) == 41  # a level with no route too


def test_a_monster_remembered_far_off_waits_for_the_tour_of_the_rooms_and_is_gone_for_after_it(monkeypatch) -> None:
    # The player, 00:10 on 2026-10-18: "when we have lower mobs count, we starts to go from one side to another back
    # and forward": 126 of 179 legs to a remembered monster went over 60 units
    play = game(area=RIVER)
    hunt = hunter(play, remembered=[(41, 5200.0, 5000.0, False)])
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    room = ((4900.0, 5000.0), 'an unexplored room', None)
    monkeypatch.setattr(hunt, 'next_room', lambda run, player, area, now: room)
    here = (me(play.world).x, me(play.world).y)
    assert hunt.rest_of(run, play.world, [], here) == room  # the tour first
    monkeypatch.setattr(hunt, 'next_room', lambda run, player, area, now: None)
    assert hunt.rest_of(run, play.world, [], here) == ((5200.0, 5000.0), 'the remembered monster', 41)  # toured


def stand(play, x: float) -> None:
    play.world = replace(play.world, player=replace(me(play.world), x=x))


def test_a_room_passed_is_not_taken_back_under_another_of_its_tiles(monkeypatch) -> None:
    """22:54:19 on 2026-10-14 (rca/2026-10-14/run-1932-findings.md §1.2.1): the full clear's unexplored room was
    passed, and 5 units on the frontier named another tile of the same room, a key not passed: the room was the goal
    again, and the run went back and forth between it and the Icy Cellar's door 8 times in 9.6 s. A room is passed by
    the room."""
    play = game(area=RIVER)
    hunt = hunter(play)
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    room, tile = EAST[2], {'x': 1020}
    monkeypatch.setattr(hunt, 'frontier', lambda level, player, rect: (10.0, room, (tile['x'], 999)))
    play.clock.now = 50.0
    found = hunt.cleared(run, play.world, [], ground, DOOR)
    assert found is not None
    assert found.label == 'full clear: an unexplored room'
    hunt.pass_by(found, 'a test', play.clock.now, ROOMS)
    for x in (1024, 1021, 1027):  # the room's other tiles, nearest by the way from where the character goes
        tile['x'] = x
        play.clock.now += REST_SECONDS + 0.1  # the frontier is looked at again
        assert hunt.cleared(run, play.world, [], ground, DOOR) == DOOR


def test_a_room_the_run_gets_nearer_to_is_not_passed_for_want_of_a_strike(monkeypatch, caplog) -> None:
    """22:54:12.99 on 2026-10-14 (§1.2.1): "passing full clear: an unexplored room ...: no strike in 10 s on the way
    to it", 119 units off by the walked way after a run of 153 units toward it in those 10 s. A room has nothing to
    strike: it is passed when the way to it (`Travel.eta`, the means in hand) has not got shorter in CLEAR_SECONDS."""
    play = game(area=RIVER)
    hunt = hunter(play)
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    monkeypatch.setattr(hunt, 'frontier', lambda level, player, rect: (30.0, EAST[3], (1034, 999)))
    play.clock.now = 50.0
    for _ in range(30):  # 15 s going toward it, 4 units a look
        found = hunt.cleared(run, play.world, [], ground, DOOR)
        assert found is not None
        assert found.label == 'full clear: an unexplored room'
        stand(play, me(play.world).x + 4.0)
        play.clock.now += 0.5
    with caplog.at_level(logging.INFO):
        for _ in range(int(CLEAR_SECONDS / 0.5) + 2):  # standing: no progress and no strike
            found = hunt.cleared(run, play.world, [], ground, DOOR)
            play.clock.now += 0.5
    assert found == DOOR
    assert 'no strike and no progress by the way in 10 s on the way to it' in caplog.text


def test_the_judge_of_a_clearing_goal_goes_on_across_another_goal(monkeypatch) -> None:
    """§1.2.1: each change of goal started the 10-s judge again, so two goals taken in turn were never passed. A
    look at another goal between two of its own does not start it again."""
    play = game(area=RIVER)
    hunt = hunter(play)
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    monkeypatch.setattr(hunt, 'frontier', lambda level, player, rect: None)
    away = foe(51, 5040.0, 5000.0)  # off the way: a full clear's own goal, not struck from here
    play.clock.now = 50.0
    passed_at = None
    for look in range(40):
        seen = [] if look % 4 == 3 else [away]  # out of sight now and then: the route's goal meanwhile
        found = hunt.cleared(run, play.world, seen, ground, DOOR)
        if seen and found == DOOR:
            passed_at = play.clock.now - 50.0
            break
        play.clock.now += 0.5
    assert passed_at is not None
    assert CLEAR_SECONDS <= passed_at <= CLEAR_SECONDS + 3.0


def test_a_clearing_goal_left_for_another_is_not_taken_back_while_the_other_holds(monkeypatch) -> None:
    """Two hostiles off the way, as near as each other: the nearer by turns as the character moves. The run keeps
    the one it went to (TAKE_BACK) until that one is gone, not the other again at every look."""
    play = game(area=RIVER)
    hunt = hunter(play)
    run = play.run()
    hunt.mode = Mode(True, SWITCHED)
    ground = Ground(())
    monkeypatch.setattr(hunt, 'frontier', lambda level, player, rect: None)
    east, west = foe(51, 5040.0, 5000.0), foe(52, 4960.0, 5000.0)
    play.clock.now = 50.0

    def unit(x: float, foes) -> int | None:
        stand(play, x)
        play.clock.now += 0.5
        return getattr(hunt.cleared(run, play.world, foes, ground, DOOR), 'unit', None)

    assert unit(4999.0, [east, west]) == 52
    assert unit(5001.0, [east, west]) == 51  # left for the other: it is nearer now
    assert unit(4999.0, [east, west]) == 51  # not taken back
    assert unit(4998.0, [east, west]) == 51
    assert unit(4998.0, [west]) == 52  # the other is gone: taken back


def test_a_valuable_across_the_lava_is_not_on_the_way() -> None:
    """22:36:09-18 on 2026-10-14 (rca/2026-10-14/run-1932-findings.md §1.2.3): an Ith Rune 26 units off in a straight
    line from E and 226 by walking round the lava was "on the way" from E (PICK_NEAR 40, straight) and not from W, 22
    units on: 8 warps between the two. On the way is PICK_NEAR by walking, on the take's ground."""
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'river-rune-ground.json').read_text())
    grids = tuple(Walkable(**grid) for grid in fixture['ground'])
    east = (7795.5, 5607.5)
    play = game(area=RIVER)
    play.world = replace(play.world, player=replace(me(play.world), x=east[0], y=east[1]))
    hunt = hunter(play, ground=grids)
    run = play.run()
    rune = Drop(70, 7817.0, 5622.0, 'Ith Rune', VALUABLE)
    play.loot = replace(play.loot, drops=(rune,))
    assert math.dist(east, (rune.x, rune.y)) < goals.PICK_NEAR
    assert not hunt.on_the_way(run, east, rune, play.world)
    assert hunt.side_drop(run, east, [], play.world) is None
    beside = Drop(71, east[0] - 6.0, east[1], 'Ral Rune', VALUABLE)  # on the same bank, a clear line
    play.loot = replace(play.loot, drops=(rune, beside))
    assert hunt.side_drop(run, east, [], play.world) == beside


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
