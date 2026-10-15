"""One move of the hunt's own (macros/travel.py): the pure choice, who asks, and a step made.

The first half asks `Travel` in the fakes' game with the shared movement sets (Teleport and the
walk: no build's own jump). The second asks the pure choice (`stride_of`, `around_of`) with facts
and jumps alone: no `Run`, no game, no set. What a build's own jump adds is tested with the build
(tests/inventory_tracking/builds/warlock/test_movement.py).
"""

import logging
import math
from dataclasses import replace

import pytest

from inventory_tracking.combat.stance import Jump, no_footing
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort, Cancelled, Hand
from inventory_tracking.macros.build import JumpSource, NoWay
from inventory_tracking.macros.movement import SHARED, TELEPORT_JUMP, OwnTeleport, StaffTeleport, Walk
from inventory_tracking.macros.routines import SWAP_SETTLE
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import (
    FIELDS,
    GROWING,
    JUMP_DISTRUST,
    JUMP_LEAST,
    JUMP_REACH,
    LOW_CHARGES,
    NO_SHOT,
    NO_SPOT_ON_WAY,
    NO_WAY_ROUND,
    OPEN_GROUND,
    OWN_MOVE,
    PLAYER_STEP,
    SEEK,
    SHUNNED,
    STRIDE,
    THERE,
    UNSEEN,
    WALLED,
    WARP_CHARGES,
    WARP_RETRY,
    Step,
    Travel,
    Walked,
    around_of,
    facts_with,
    move_facts,
    navigator,
    planning,
    spare_jump,
    step_line,
    step_walk,
    stride_of,
    walked_over,
    walked_way,
    way_left,
    way_leg,
)
from inventory_tracking.macros.world import Teleport
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world
from tests.inventory_tracking.macros.moves import ASPECT, HERE, IN_HAND, NOW, facts, wall_with_a_gap, walled


DART = Jump(900, 0.3, 40.0, JUMP_REACH, JUMP_LEAST, line=True)  # a jump of no build: thrown, so it needs a clear line
HOP = TELEPORT_JUMP  # needs none


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def game(**changes):
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    play = Game(world(**changes))
    play.staff = Teleport(10, 20, True)
    return play


def staff(play: Game) -> Teleport:
    """The staff the character of `game` wears."""
    assert play.staff is not None
    return play.staff


def approx_step(spot: tuple[float, float], skill: int | None = None) -> Step:
    """A step to `spot` within float error."""
    return Step(pytest.approx(spot), skill)  # pyrefly: ignore[bad-argument-type]  # approx compares as the spot


def reason(leg) -> str:
    assert isinstance(leg, NoWay)
    return leg.reason


# --- Travel, in the fakes' game, with the shared sets ----------------------------------------------------


def test_the_jump_is_teleport_from_the_staff_in_hand_and_never_a_swap():
    play = game()
    travel, run = Travel(SHARED), play.run()
    assert [(jump.skill, jump.line) for jump in travel.jumps(run, play.world)] == [(TELEPORT, False)]
    assert travel.jump_by(run, play.world) == TELEPORT
    play.staff = replace(staff(play), in_hand=False)  # a swap away: not a jump
    assert travel.jump_by(run, play.world) is None


def test_low_on_charges_the_modes_own_jumps_leave_the_staff_alone():
    # user, 2026-10-11: "track number of tp charges when using staff, and leverage warp more when low"
    play = game()
    travel, run = Travel(SHARED), play.run()
    play.staff = replace(staff(play), charges=LOW_CHARGES)
    assert travel.jump_by(run, play.world) == TELEPORT
    play.staff = replace(staff(play), charges=LOW_CHARGES - 1)
    assert travel.jumps(run, play.world) == ()  # a walk, not a charge
    assert travel.jump_by(run, play.world, replace(OWN_MOVE, reserve=1)) == TELEPORT  # the intent's floor


def test_a_jump_that_moved_nothing_is_left_out_for_a_while():
    play = game()
    travel, run = Travel(SHARED), play.run()
    travel.jump_failed[TELEPORT] = play.clock.now
    assert travel.jump_by(run, play.world) is None
    play.clock.now += JUMP_DISTRUST + 1
    assert travel.jump_by(run, play.world) == TELEPORT


def test_a_straight_stride_ends_short_of_its_goal_and_avoids_what_is_shunned():
    play = game()
    travel, run = Travel(SHARED), play.run()
    short = replace(OWN_MOVE, short=14.0)
    found = travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), short)
    assert found is not None
    assert found.skill == TELEPORT
    assert found.spot == pytest.approx((5016.0, 5000.0))
    assert step_line(found, (5000.0, 5000.0)) == 'a stride of 16 toward the nearest, by Teleport'
    shunning = replace(short, shuns=lambda spot: True)
    assert travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), shunning) is None
    assert travel.stride(run, play.world, Ground(()), ASPECT, (5015.0, 5000.0), short) is None  # there already


def test_a_step_is_made_by_the_jump_it_names_and_walked_when_that_can_no_longer_be_made():
    play = game()
    travel, run = Travel(SHARED), play.run()
    travel.make(run, Step((5012.0, 5000.0), TELEPORT), play.world, ASPECT, keys, Ground(()))
    assert play.pressed() == [KEYS[TELEPORT]]
    assert travel.jumped_at == {}  # Teleport has no casting delay: nothing to remember
    play.staff = replace(staff(play), in_hand=False)
    after = run.world()
    assert after.player is not None
    travel.make(run, Step((after.player.x + 8.0, after.player.y), TELEPORT), after, ASPECT, keys, None)
    assert play.pressed() == [KEYS[TELEPORT]]  # no second key: the staff is a swap away, the step is walked
    assert any(event[0] == 'click' for event in play.keys.events)


def test_with_no_set_that_applies_there_is_no_jump_and_no_stride():
    play = game()
    travel, run = Travel(), play.run()
    assert travel.jumps(run, play.world) == ()
    assert travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0)) is None
    assert travel.around(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0)) is None
    assert travel.wait(run, play.world, Ground(()), ASPECT, (5000.0, 5000.0), (5030.0, 5000.0), SEEK, None) == 0.0


def test_the_last_jump_is_remembered_for_the_skills_that_have_a_casting_delay():
    slow = Walk().led_by(JumpSource(DART, delay=0.8))
    travel = Travel((slow,))
    assert travel.delayed == {DART.skill}
    assert travel.warped_at == -math.inf
    travel.warped_at = 7.0
    assert travel.jumped_at == {DART.skill: 7.0}
    assert travel.warped_at == 7.0
    assert Travel(SHARED).delayed == frozenset()


def test_the_facts_are_the_game_as_travel_reads_it_today():
    play = game()
    play.clock.now = NOW
    travel, run = Travel(SHARED), play.run()
    travel.jumped_at[DART.skill] = NOW - 5.0
    travel.jump_failed[TELEPORT] = NOW - 2.0
    read = move_facts(run, play.world, None, ASPECT, travel)
    assert (read.here, read.now, read.slots, read.staff) == ((5000.0, 5000.0), NOW, HUNT_SLOTS, play.staff)
    assert (read.ground, read.doors, read.aspect) == (None, play.world.doors, ASPECT)
    assert (read.since_used(DART.skill), read.since_failed(TELEPORT)) == (5.0, 2.0)
    travel.jump_failed.clear()  # the facts were read once: the memory moving on does not change them
    travel.jumped_at.clear()
    assert (read.since_used(DART.skill), read.since_failed(TELEPORT)) == (5.0, 2.0)
    play.staff = None  # no staff worn, and no reader of one, are the same fact
    assert move_facts(run, play.world, None, ASPECT, travel).staff is None
    play.staff = IN_HAND
    run.teleport = None
    assert move_facts(run, play.world, None, ASPECT, travel).staff is None


def test_the_facts_with_a_staff_the_caller_read_do_not_read_it_again():
    play = game()
    travel, run = Travel(SHARED), play.run()
    run.teleport = None  # a read would fail: there is no reader
    assert facts_with(run, play.world, None, ASPECT, travel, IN_HAND).staff == IN_HAND
    off_keys = replace(play.world, slots=(None,))
    # As `move_facts`: a staff counts only with Teleport on a key
    assert facts_with(run, off_keys, None, ASPECT, travel, IN_HAND).staff is None


# --- who asks: the intents, the navigator ----------------------------------------------------------------


def test_the_three_intents_hold_todays_numbers():
    assert (LOW_CHARGES, JUMP_DISTRUST, WARP_CHARGES, WARP_RETRY) == (10, 30.0, 15, 3.0)
    table = {
        intent.name: (
            intent.reserve, intent.distrust, intent.sparing, intent.walks_under,
            intent.may_swap, intent.may_wait, intent.waits_blind,
        )
        for intent in (PLAYER_STEP, SEEK, OWN_MOVE)
    }  # fmt: skip
    assert table == {
        'player step': (10, 3.0, 15, 1, True, True, True),
        'seek': (10, 30.0, math.inf, 10, True, True, False),
        'own move': (10, 30.0, math.inf, 0.0, False, False, False),
    }
    for intent in (PLAYER_STEP, SEEK, OWN_MOVE):
        assert (intent.short, intent.shot, intent.detour) == (0.0, False, False)


def test_the_navigator_takes_the_first_set_that_applies():
    worn, own, afoot = facts(staff=IN_HAND), facts(), facts(slots=())
    assert isinstance(navigator(SHARED, worn), StaffTeleport)
    assert isinstance(navigator(SHARED, replace(worn, staff=replace(IN_HAND, charges=0, in_hand=False))), StaffTeleport)
    assert isinstance(navigator(SHARED, own), OwnTeleport)
    assert isinstance(navigator(SHARED, afoot), Walk)
    assert navigator((), afoot) is None
    assert navigator((StaffTeleport(), OwnTeleport()), afoot) is None
    assert isinstance(navigator((Walk(), StaffTeleport()), worn), Walk)  # the order is the build's


def test_the_jump_that_spares_the_staff_is_the_first_of_the_sets_that_is_not_teleport_and_is_on_a_key():
    assert spare_jump(SHARED, (TELEPORT, DART.skill)) is None  # the shared sets have only Teleport
    with_dart = tuple(shared.led_by(JumpSource(DART, delay=0.8)) for shared in SHARED)
    assert spare_jump(with_dart, (TELEPORT, DART.skill)) == DART
    assert spare_jump(with_dart, (TELEPORT, None)) is None  # on no key
    assert spare_jump((), (DART.skill,)) is None


# --- the pure choice: facts and jumps in, a decision out -------------------------------------------------


def test_the_walked_way_goes_round_a_wall_and_no_way_is_an_empty_one():
    ground = walled(wall_with_a_gap)
    barred = no_footing(ground, ())
    assert barred is not None
    path = walked_way(barred, (5000.5, 5000.5), (5020.5, 5000.5))
    assert path[-1] == (5020.5, 5000.5)
    assert max(y for _x, y in path) >= 5012  # round the wall's southern end
    assert all(not barred(spot) for spot in path)
    shut = no_footing(walled(lambda x, y: not 5008 <= x < 5010), ())
    assert shut is not None
    # The wall has no end: the way goes as near the goal as the ground lets it, and from there nowhere.
    assert walked_way(shut, (5000.5, 5000.5), (5020.5, 5000.5))[-1] == (5007.5, 5000.5)
    assert walked_way(shut, (5007.5, 5000.5), (5020.5, 5000.5)) == []


def test_a_stride_is_the_longest_jump_that_lands_and_a_walk_where_none_is_made():
    goal = (HERE[0] + 30.0, HERE[1])
    both = (DART, HOP)
    assert stride_of(facts(), goal, 14.0, jumps=both) == approx_step((HERE[0] + 16.0, HERE[1]), DART.skill)
    # The candidates in their order: JUMP_REACH lands in view to the west; to the east it is off the
    # window and three quarters of it is taken; down the screen only half of it is in view.
    for dx, dy, share in ((-60.0, 0.0, 1.0), (60.0, 0.0, 0.75), (60.0, 60.0, 0.5)):
        far = stride_of(facts(), (HERE[0] + dx, HERE[1] + dy), jumps=both)
        assert isinstance(far, Step)
        assert (far.skill, math.dist(HERE, far.spot)) == (DART.skill, pytest.approx(JUMP_REACH * share))
    assert stride_of(facts(), goal, 14.0, jumps=(HOP,)) == approx_step((HERE[0] + 16.0, HERE[1]), TELEPORT)
    walked = stride_of(facts(), goal)
    assert walked == approx_step((HERE[0] + STRIDE, HERE[1]))
    near = stride_of(facts(), (HERE[0] + 6.0, HERE[1]), jumps=both)  # under JUMP_LEAST: walked, whatever the jumps
    assert near == approx_step((HERE[0] + 6.0, HERE[1]))


def test_a_stride_at_or_within_its_stand_off_has_arrived():
    goal = (HERE[0] + 14.0, HERE[1])
    for found in (stride_of(facts(), goal, 14.0), stride_of(facts(), goal, 20.0), stride_of(facts(), HERE)):
        assert found == NoWay(THERE, arrived=True)  # nearer than `short` too: never a step back
    assert stride_of(facts(), goal, 20.0, shuns=lambda spot: True, jumps=(DART,)) == NoWay(THERE, arrived=True)


def test_a_stride_to_a_shunned_place_is_blocked_and_says_so():
    asked = []

    def shuns(spot) -> bool:
        asked.append(spot)
        return True

    assert stride_of(facts(), (HERE[0] + 40.0, HERE[1]), 14.0, shuns=shuns, jumps=(DART, HOP)) == NoWay(SHUNNED)
    assert asked == [pytest.approx((HERE[0] + STRIDE, HERE[1]))]  # the walk's end, one stride on


def test_a_walk_that_ends_out_of_view_is_not_made():
    narrow = facts(aspect=0.5)  # a window half as wide as it is high: 16 units east is off it
    assert reason(stride_of(narrow, (HERE[0] + 30.0, HERE[1]))) == UNSEEN
    assert isinstance(stride_of(replace(narrow, aspect=ASPECT), (HERE[0] + 30.0, HERE[1])), Step)


def test_a_wall_in_the_line_leaves_no_straight_stride():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    blocked = stride_of(facts(ground=ground), goal, jumps=(DART,))
    assert blocked == NoWay(WALLED)
    assert isinstance(blocked, NoWay)
    assert not blocked.arrived
    assert reason(stride_of(facts(ground=ground), goal)) == WALLED
    # The stride asks for one jump: with a thrown one first and a wall in its line it is not handed to the next
    assert reason(stride_of(facts(ground=ground), goal, jumps=(DART, HOP))) == WALLED
    # A jump that needs no line, when it is the first, lands beyond the wall
    over = stride_of(facts(ground=ground), goal, jumps=(HOP, DART))
    assert isinstance(over, Step)
    assert (over.skill, over.spot) == (TELEPORT, pytest.approx(goal))


def test_a_few_units_up_to_a_wall_the_goal_stands_behind_is_no_stride_for_a_shot():
    ground = walled(wall_with_a_gap)
    goal = (5012.5, 5000.5)  # behind the wall at 5008 to 5010
    both = (DART, HOP)
    assert reason(stride_of(facts(ground=ground), goal, 6.0, shot=True, jumps=both)) == NO_SHOT
    assert stride_of(facts(ground=ground), goal, 6.0, jumps=both) == approx_step((5006.5, 5000.5))
    clear = stride_of(facts(), goal, 6.0, shot=True, jumps=both)  # no wall: the same walk is made
    assert clear == approx_step((5006.5, 5000.5))


def test_with_no_wall_known_there_is_no_way_round_to_look_for():
    goal = (5020.5, 5000.5)
    assert around_of(facts(), goal, jumps=(DART,)) == NoWay(OPEN_GROUND)
    assert around_of(facts(ground=None), goal) == NoWay(OPEN_GROUND)


def test_the_way_round_is_jumped_along_over_a_clear_line_and_walked_otherwise():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    jumped = around_of(facts(ground=ground), goal, jumps=(DART, HOP))
    assert isinstance(jumped, Step)
    assert jumped.skill == DART.skill
    assert JUMP_LEAST <= math.dist(HERE, jumped.spot) <= JUMP_REACH
    for jumps in ((), (HOP,), (HOP, DART)):
        walk = around_of(facts(ground=ground), goal, jumps=jumps)  # no jump, or the first needs no line: walked
        assert isinstance(walk, Step)
        assert walk.skill is None
        assert math.dist(HERE, walk.spot) <= STRIDE


def test_no_way_round_a_wall_without_an_end_and_the_goals_own_cell_is_an_arrival():
    shut = facts(ground=walled(lambda x, y: not 5008 <= x < 5010), here=(5007.5, 5000.5))
    assert around_of(shut, (5020.5, 5000.5), jumps=(DART,)) == NoWay(NO_WAY_ROUND)
    assert around_of(shut, (5007.9, 5000.1), jumps=(DART,)) == NoWay(THERE, arrived=True)


def test_a_way_round_too_short_for_a_jump_or_a_walk_has_no_move():
    ground = walled(wall_with_a_gap)
    assert around_of(facts(ground=ground), (5002.5, 5000.5), jumps=(DART, HOP)) == NoWay(NO_SPOT_ON_WAY)


def test_a_dodges_click_waits_for_the_cast_to_end_not_the_settle_and_one_swallowed_is_said_and_made_again(caplog):
    # rca/2026-10-14/diablo-handling.md R3, fix 3: a step across Diablo's stream chosen in a cast left 0.67 s after
    # the decision (the cast's rest, 0.41 s of settle, the click) and met the missiles. Hurried, the click comes at
    # the first look that reads the cast over; a click the game took no notice of is said and made again, settled.
    play = Game(world())
    run = play.run()
    play.world = replace(play.world, player=replace(play.character, mode=7))
    play.acting_until = play.clock.now + 0.15
    casting = play.world.player
    settled = step_walk(run, (5010.0, 5000.0), casting, ASPECT, [], hurry=True)
    assert 0.15 <= settled < 0.15 + SWAP_SETTLE
    assert len(play.walks) == 1
    play.swallowed_clicks = 1
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        settled = step_walk(run, (5020.0, 5000.0), play.world.player, ASPECT, [], hurry=True)
    assert len(play.walks) == 2
    assert settled >= SWAP_SETTLE  # the click again is settled
    assert 'showed no move' in caplog.text


def test_a_failed_jump_in_the_game_is_remembered_and_said():
    play = game()
    travel, run = Travel(SHARED), play.run()
    play.staff = replace(staff(play), charges=0)  # the key does nothing: the staff is empty
    with pytest.raises(Abort, match='Teleport: the character did not move'):
        travel.jump(run, Step((5012.0, 5000.0), TELEPORT), play.world.player, ASPECT, keys)
    assert travel.jump_failed == {TELEPORT: pytest.approx(play.clock.now)}


@pytest.mark.parametrize('stop', [Hand('the mouse was moved'), Cancelled()], ids=['the hand', 'cancelled'])
def test_a_jump_the_player_or_the_run_cut_is_not_remembered_as_failed(stop):
    # 22:54:40.78 on 2026-10-14 (rca/2026-10-14/run-1932-findings.md §1.2.4): the player's mouse cut a Blade Warp at
    # its aim, it was taken for a jump that moved nobody, and the next 15 s were walked (JUMP_DISTRUST 30 s)
    play = game()
    travel, run = Travel(SHARED), play.run()

    def cut(*args, **kwargs):
        raise stop

    run.actuator.aim = cut
    with pytest.raises(type(stop)):
        travel.jump(run, Step((5012.0, 5000.0), TELEPORT), play.world.player, ASPECT, keys)
    assert travel.jump_failed == {}


def test_a_walk_click_waits_for_the_character_to_stand_free_only_when_a_look_has_it_casting():
    # The fixed 0.2 s of every walk leg (rca/2026-10-13/latency-findings.md §2.2): a character free at the look
    # the walk was chosen by and at one now is clicked at once; one that was casting waits as before.
    play = Game(world())
    run = play.run()
    assert step_walk(run, (5010.0, 5000.0), play.world.player, ASPECT, []) == 0.0
    casting = replace(play.character, mode=7)
    assert step_walk(run, (5020.0, 5000.0), casting, ASPECT, []) >= SWAP_SETTLE
    assert len(play.walks) == 2


# --- the walked field kept across the ground's growth, grown within a look's time ------------------------------


def outdoors(x, y) -> bool:
    """A level of 4 x 2 rooms of 8 x 8 tiles (world 5000-5160, 5000-5080): a wall at x 5038 open at its south end, one
    at x 5118 open at its north end, and pillars, so the way to the north-west corner from the south-east winds."""
    if 5038 <= x < 5040 and y < 5070:
        return False
    if 5118 <= x < 5120 and y >= 5010:
        return False
    return not (x % 23 < 2 and y % 17 < 3)


def room(column: int, row: int, walkable=outdoors) -> Walkable:
    left, top = 1000 + 8 * column, 1000 + 8 * row
    cells = ''.join(
        '1' if walkable(5 * left + x, 5 * top + y) else '0' for y in range(40) for x in range(40)
    )  # fmt: skip
    return Walkable(left, top, 8, 8, pack_cells(cells))


ROOMS = {(column, row): room(column, row) for column in range(4) for row in range(2)}
CORNER = (5004.5, 5004.5)  # the goal, in the north-west room
FAR = (5150.5, 5070.5)  # the character, in the south-east room
SAMPLES = [(5000.5 + x, 5000.5 + y) for x in range(0, 160, 7) for y in range(0, 80, 6)]


def afresh(grids) -> Walked:
    barred = no_footing(Ground(grids), ())
    assert barred is not None
    return Walked(barred, (math.floor(CORNER[0]) + 0.5, math.floor(CORNER[1]) + 0.5))


def same_field(kept: Walked, grids) -> None:
    fresh = afresh(grids)
    assert kept.left(FAR) == pytest.approx(fresh.left(FAR), abs=1e-9)
    assert kept.descent(FAR, JUMP_REACH) == pytest.approx(fresh.descent(FAR, JUMP_REACH), abs=1e-9)
    for point in SAMPLES:
        assert kept.left(point) == pytest.approx(fresh.left(point), abs=1e-9), point


def test_a_kept_walked_field_takes_in_each_room_read_and_answers_as_one_grown_afresh():
    # The Plains of Despair, 23:48 on 2026-10-14 (rca/2026-10-14/run-2040-findings.md §1.2.2): the field was kept by
    # the whole ground, which grows with every outdoor room read, so each room grew it afresh from the goal
    FIELDS.clear()
    cell = (math.floor(CORNER[0]), math.floor(CORNER[1]))
    grids = tuple(ROOMS[key] for key in ((0, 0), (0, 1), (1, 1), (2, 1), (3, 1), (3, 0)))
    first = walked_over(grids, (), cell)
    assert first is not None
    assert first.left(FAR) == math.inf  # the way through the north rooms is not read yet
    for key in ((2, 0), (1, 0)):  # the way read, then a room that shortens it
        grids = (*grids, ROOMS[key])
        kept = walked_over(grids, (), cell)
        assert kept is first  # taken in, not grown again from the goal
        same_field(kept, grids)
    assert first.left(FAR) < math.inf


def test_a_room_read_again_with_more_footing_is_taken_in_and_one_with_less_grows_the_field_afresh():
    FIELDS.clear()
    cell = (math.floor(CORNER[0]), math.floor(CORNER[1]))
    walled_in = room(1, 0, lambda x, y: outdoors(x, y) and not (5050 <= x < 5052))
    grids = (*ROOMS.values(),)
    grids = tuple(walled_in if grid is ROOMS[1, 0] else grid for grid in grids)
    first = walked_over(grids, (), cell)
    assert first is not None
    assert first.left(FAR) < math.inf
    opened = tuple(ROOMS[1, 0] if grid is walled_in else grid for grid in grids)
    assert walked_over(opened, (), cell) is first
    same_field(first, opened)
    again = walked_over(grids, (), cell)  # the wall back: no way may grow longer in a kept field
    assert again is not None
    assert again is not first
    same_field(again, grids)


def test_a_walked_field_grows_within_the_looks_time_and_is_the_straight_line_until_it_reaches(caplog):
    FIELDS.clear()
    grids = tuple(ROOMS.values())
    here = facts(here=FAR, ground=Ground(grids), slots=(None,))
    reads = iter(range(10**6))
    clock = lambda: next(reads) * 0.001  # ruff: ignore[lambda-assignment] - a clock that moves a millisecond each time it is read
    with caplog.at_level(logging.INFO, logger=LOG.name):
        with planning(clock, 0.005):
            assert way_left(here, CORNER) == math.dist(FAR, CORNER)  # not reached in time: the straight line
            assert way_left(replace(here, here=(5010.5, 5010.5)), CORNER) == math.dist((5010.5, 5010.5), CORNER)
        said = [record.getMessage() for record in caplog.records if record.getMessage().startswith('Macro: way:')]
        assert len(said) == 1
        assert 'still being grown' in said[0]
        looks = 1
        while True:
            with planning(clock, clock() + 0.005):
                left = way_left(here, CORNER)
            if left != math.dist(FAR, CORNER):
                break
            looks += 1
            assert looks < 200
    assert looks > 1  # grown over several looks, each one bounded
    assert left == pytest.approx(afresh(grids).left(FAR), abs=1e-9)
    assert way_left(here, CORNER) == left  # with no clock (the arena), no bound


def test_a_room_that_shortens_the_kept_way_is_taken_in_within_the_looks_time_too():
    FIELDS.clear()
    cell = (math.floor(CORNER[0]), math.floor(CORNER[1]))
    grids = tuple(ROOMS[key] for key in ((0, 0), (0, 1), (1, 1), (2, 1), (3, 1), (3, 0), (2, 0)))
    first = walked_over(grids, (), cell)
    assert first is not None
    assert first.left(FAR) < math.inf  # grown with no clock
    grids = (*grids, ROOMS[1, 0])  # the room that shortens the way of most of the field
    here = facts(here=FAR, ground=Ground(grids), slots=(None,))
    reads = iter(range(10**6))
    clock = lambda: next(reads) * 0.001  # ruff: ignore[lambda-assignment]
    looks = 0
    while True:
        looks += 1
        with planning(clock, clock() + 0.003):
            left = way_left(here, CORNER)
        if left != math.dist(FAR, CORNER):
            break
        assert looks < 200
    assert looks > 1  # the lowering passed on over several looks, each one bounded
    assert walked_over(grids, (), cell) is first
    assert left == pytest.approx(afresh(grids).left(FAR), abs=1e-9)


def test_with_the_walked_way_still_growing_and_no_straight_stride_there_is_no_failed_way():
    FIELDS.clear()
    grids = tuple(ROOMS.values())
    behind = (5030.5, 5040.5)  # the wall at 5038 between it and the character: no straight stride from here
    here = facts(here=(5045.5, 5040.5), ground=Ground(grids), slots=(None,))
    with planning(lambda: 1.0, 0.0):  # no time at all
        leg = way_leg(here, behind, OWN_MOVE)
    assert reason(leg) == GROWING
    assert isinstance(way_leg(here, behind, OWN_MOVE), Step)  # with no clock the way is grown: round the wall
