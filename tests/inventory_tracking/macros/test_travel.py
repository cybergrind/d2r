"""One move of the hunt's own (macros/travel.py): which jumps the character has, and a step made by one.

The first half asks `Travel` in the fakes' game. The second asks the pure choice (`jumps_of`,
`stride_of`, `around_of`) with facts alone: no `Run`, no game.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.combat.stance import no_footing
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import MoveFacts, NoWay
from inventory_tracking.macros.skills import BLADE_WARP, TELEPORT
from inventory_tracking.macros.travel import (
    JUMP_DISTRUST,
    JUMP_LEAST,
    JUMP_REACH,
    LOW_CHARGES,
    NO_SHOT,
    NO_SPOT_ON_WAY,
    NO_WAY_ROUND,
    OPEN_GROUND,
    SHUNNED,
    STRIDE,
    THERE,
    UNSEEN,
    WALLED,
    WARP_DELAY,
    Step,
    Travel,
    around_of,
    jump_of,
    jumps_of,
    move_facts,
    step_line,
    stride_of,
    walked_way,
)
from inventory_tracking.macros.world import Teleport
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


ASPECT = 2560 / 1418


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def game(**changes):
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    play = Game(world(**changes))
    play.staff = Teleport(10, 20, True)
    return play


def test_the_jumps_are_blade_warp_first_then_teleport_without_a_swap():
    play = game()
    travel, run = Travel(), play.run()
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    assert [jump.line for jump in travel.jumps(run, play.world)] == [True, False]
    travel.warped_at = play.clock.now  # its casting delay runs
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += WARP_DELAY
    assert travel.jump_by(run, play.world) == BLADE_WARP
    play.staff = replace(play.staff, in_hand=False)  # a swap away: not a jump
    assert travel.jump_by(run, play.world, warp=False) is None


def test_low_on_charges_the_modes_own_jumps_leave_the_staff_alone():
    # user, 2026-10-11: "track number of tp charges when using staff, and leverage warp more when low"
    play = game()
    travel, run = Travel(), play.run()
    play.staff = replace(play.staff, charges=LOW_CHARGES)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    play.staff = replace(play.staff, charges=LOW_CHARGES - 1)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP]
    travel.warped_at = play.clock.now
    assert travel.jump_by(run, play.world) is None  # its delay runs: a walk, not a charge


def test_a_jump_that_moved_nothing_is_left_out_for_a_while():
    play = game()
    travel, run = Travel(), play.run()
    play.warp_lands = False
    with pytest.raises(Abort, match='Blade Warp: the character did not move'):
        travel.make(run, Step((5012.0, 5000.0), BLADE_WARP), play.world, ASPECT, keys, Ground(()))
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += JUMP_DISTRUST + 1
    assert travel.jump_by(run, play.world) == BLADE_WARP


def test_a_straight_stride_ends_short_of_its_goal_and_avoids_what_is_shunned():
    play = game()
    travel, run = Travel(), play.run()
    found = travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), short=14.0)
    assert found is not None
    assert found.skill == BLADE_WARP
    assert found.spot == pytest.approx((5016.0, 5000.0))
    assert step_line(found, (5000.0, 5000.0)) == 'a stride of 16 toward the nearest, by Blade Warp'
    assert travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), 14.0, shuns=lambda spot: True) is None
    assert travel.stride(run, play.world, Ground(()), ASPECT, (5015.0, 5000.0), short=14.0) is None  # there already


def walled(walkable):
    """One room of 32 x 32 tiles round the character (world 5000, 5000), walkable where `walkable(x, y)` says so."""
    cells = ''.join('1' if walkable(4920 + x, 4920 + y) else '0' for y in range(160) for x in range(160))
    return Ground((Walkable(984, 984, 32, 32, pack_cells(cells)),))


def wall_with_a_gap(x, y):
    """A wall two units thick east of the character, from far north to 12 units south of it."""
    return not (5008 <= x < 5010 and y < 5012)


def test_the_walked_way_goes_round_a_wall_and_no_way_is_an_empty_one():
    ground = walled(wall_with_a_gap)
    barred = no_footing(ground, ())
    path = walked_way(barred, (5000.5, 5000.5), (5020.5, 5000.5))
    assert path[-1] == (5020.5, 5000.5)
    assert max(y for _x, y in path) >= 5012  # round the wall's southern end
    assert all(not barred(spot) for spot in path)
    shut = no_footing(walled(lambda x, y: not 5008 <= x < 5010), ())
    # The wall has no end: the way goes as near the goal as the ground lets it, and from there nowhere.
    assert walked_way(shut, (5000.5, 5000.5), (5020.5, 5000.5))[-1] == (5007.5, 5000.5)
    assert walked_way(shut, (5007.5, 5000.5), (5020.5, 5000.5)) == []


def test_with_no_straight_stride_a_move_is_made_along_the_way_round_the_wall():
    # Drifter Cavern, 09:43 on 2026-10-12: the staff empty and the firing spot behind a wall.
    play = game()
    play.staff = replace(play.staff, charges=0)
    ground = walled(wall_with_a_gap)
    travel, run = Travel(), play.run()
    goal = (5020.5, 5000.5)
    assert travel.stride(run, play.world, ground, ASPECT, goal) is None
    found = travel.around(run, play.world, ground, ASPECT, goal)
    assert found is not None
    assert found.skill == BLADE_WARP  # a clear line to a spot further along the way
    assert found.spot[1] > 5005
    travel.warped_at = play.clock.now  # under its casting delay: walked
    walk = travel.around(run, play.world, ground, ASPECT, goal)
    assert walk is not None
    assert walk.skill is None
    assert walk.spot[1] > 5002


# --- the pure choice: facts in, a decision out -----------------------------------------------------------

NOW = 100.0
HERE = (5000.5, 5000.5)
IN_HAND = Teleport(69, 69, True)


def facts(**changes) -> MoveFacts:
    """The character at HERE on a level with no wall read, Blade Warp and Teleport on keys, no staff worn."""
    known = {
        'here': HERE,
        'now': NOW,
        'slots': (BLADE_WARP, None, TELEPORT),
        'staff': None,
        'ground': Ground(()),
        'doors': (),
        'aspect': ASPECT,
    }
    return MoveFacts(**{**known, **changes})


def skills(found) -> list[int]:
    return [jump.skill for jump in found]


def reason(leg) -> str:
    assert isinstance(leg, NoWay)
    return leg.reason


def test_blade_warp_ready_comes_before_teleport():
    found = jumps_of(facts())
    assert skills(found) == [BLADE_WARP, TELEPORT]
    assert [(jump.line, jump.reach, jump.least) for jump in found] == [
        (True, JUMP_REACH, JUMP_LEAST),
        (False, JUMP_REACH, JUMP_LEAST),
    ]
    assert jump_of(facts()) == BLADE_WARP
    assert jump_of(facts(), warp=False) == TELEPORT


def test_blade_warp_in_its_casting_delay_is_no_jump_until_the_delay_is_over():
    assert skills(jumps_of(facts(last_used={BLADE_WARP: NOW - 0.1}))) == [TELEPORT]
    made = facts(now=0.5, last_used={BLADE_WARP: 0.0})
    assert skills(jumps_of(made)) == [TELEPORT]
    assert skills(jumps_of(replace(made, now=WARP_DELAY))) == [BLADE_WARP, TELEPORT]  # over at the delay itself
    assert skills(jumps_of(facts(last_used={BLADE_WARP: -math.inf}))) == [BLADE_WARP, TELEPORT]  # never made
    assert skills(jumps_of(facts(last_used={BLADE_WARP: NOW - 0.1}), delay=0.05)) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(last_used={TELEPORT: NOW}))) == [BLADE_WARP, TELEPORT]  # Teleport has no delay


def test_a_jump_that_moved_nothing_is_distrusted_for_as_long_as_the_caller_says():
    failed = facts(failed={BLADE_WARP: NOW - JUMP_DISTRUST})
    assert skills(jumps_of(failed)) == [TELEPORT]  # to the second: left out
    assert skills(jumps_of(replace(failed, now=NOW + 0.5))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(failed, distrust=3.0)) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(failed={TELEPORT: NOW - 1.0}))) == [BLADE_WARP]
    assert jumps_of(facts(failed={BLADE_WARP: NOW - 1.0, TELEPORT: NOW - 1.0})) == ()


def test_the_staff_in_hand_is_jumped_by_down_to_the_floor_of_charges():
    def worn(charges: int) -> MoveFacts:
        return facts(staff=replace(IN_HAND, charges=charges))

    assert skills(jumps_of(worn(69))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(worn(LOW_CHARGES))) == [BLADE_WARP, TELEPORT]  # the floor itself is still spent
    assert skills(jumps_of(worn(LOW_CHARGES - 1))) == [BLADE_WARP]
    assert skills(jumps_of(worn(0))) == [BLADE_WARP]
    assert skills(jumps_of(worn(14), floor=15)) == [BLADE_WARP]
    assert skills(jumps_of(worn(1), floor=1)) == [BLADE_WARP, TELEPORT]


def test_the_staff_in_the_other_weapon_set_is_a_swap_away_and_no_jump():
    assert skills(jumps_of(facts(staff=replace(IN_HAND, in_hand=False)))) == [BLADE_WARP]
    assert skills(jumps_of(facts(staff=replace(IN_HAND, in_hand=False)), floor=0)) == [BLADE_WARP]


def test_with_no_staff_teleport_is_the_characters_own_skill_whatever_the_floor():
    assert skills(jumps_of(facts(staff=None), floor=1000)) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(staff=None, slots=(TELEPORT,)))) == [TELEPORT]


def test_a_skill_that_is_on_no_key_is_no_jump():
    assert jumps_of(facts(slots=())) == ()
    assert jumps_of(facts(slots=(None, 7))) == ()
    assert skills(jumps_of(facts(slots=(BLADE_WARP,), staff=IN_HAND))) == [BLADE_WARP]
    assert jump_of(facts(slots=(BLADE_WARP,)), warp=False) is None
    assert jump_of(facts(slots=())) is None


def test_the_facts_are_the_game_as_travel_reads_it_today():
    play = game()
    play.clock.now = NOW
    travel, run = Travel(), play.run()
    travel.warped_at = NOW - 5.0
    travel.jump_failed[TELEPORT] = NOW - 2.0
    read = move_facts(run, play.world, None, ASPECT, travel)
    assert (read.here, read.now, read.slots, read.staff) == ((5000.0, 5000.0), NOW, HUNT_SLOTS, play.staff)
    assert (read.ground, read.doors, read.aspect) == (None, play.world.doors, ASPECT)
    assert (read.since_used(BLADE_WARP), read.since_failed(TELEPORT)) == (5.0, 2.0)
    travel.jump_failed.clear()  # the facts were read once: the memory moving on does not change them
    assert read.since_failed(TELEPORT) == 2.0
    play.staff = None  # no staff worn, and no reader of one, are the same fact
    assert move_facts(run, play.world, None, ASPECT, travel).staff is None
    play.staff = IN_HAND
    run.teleport = None
    assert move_facts(run, play.world, None, ASPECT, travel).staff is None


def test_a_stride_is_the_longest_jump_that_lands_and_a_walk_where_none_is_made():
    goal = (HERE[0] + 30.0, HERE[1])
    assert stride_of(facts(), goal, 14.0) == Step(pytest.approx((HERE[0] + 16.0, HERE[1])), BLADE_WARP)
    # The candidates in their order: JUMP_REACH lands in view to the west; to the east it is off the
    # window and three quarters of it is taken; down the screen only half of it is in view.
    for dx, dy, share in ((-60.0, 0.0, 1.0), (60.0, 0.0, 0.75), (60.0, 60.0, 0.5)):
        far = stride_of(facts(), (HERE[0] + dx, HERE[1] + dy))
        assert isinstance(far, Step)
        assert (far.skill, math.dist(HERE, far.spot)) == (BLADE_WARP, pytest.approx(JUMP_REACH * share))
    delayed = facts(last_used={BLADE_WARP: NOW})
    assert stride_of(delayed, goal, 14.0) == Step(pytest.approx((HERE[0] + 16.0, HERE[1])), TELEPORT)
    walked = stride_of(facts(slots=()), goal)
    assert walked == Step(pytest.approx((HERE[0] + STRIDE, HERE[1])))
    near = stride_of(facts(), (HERE[0] + 6.0, HERE[1]))  # under JUMP_LEAST: walked, whatever jumps there are
    assert near == Step(pytest.approx((HERE[0] + 6.0, HERE[1])))


def test_a_stride_at_or_within_its_stand_off_has_arrived():
    goal = (HERE[0] + 14.0, HERE[1])
    for found in (stride_of(facts(), goal, 14.0), stride_of(facts(), goal, 20.0), stride_of(facts(), HERE)):
        assert found == NoWay(THERE, arrived=True)  # nearer than `short` too: never a step back
    assert stride_of(facts(), goal, 20.0, shuns=lambda spot: True) == NoWay(THERE, arrived=True)


def test_a_stride_to_a_shunned_place_is_blocked_and_says_so():
    asked = []

    def shuns(spot) -> bool:
        asked.append(spot)
        return True

    assert stride_of(facts(), (HERE[0] + 40.0, HERE[1]), 14.0, shuns=shuns) == NoWay(SHUNNED)
    assert asked == [pytest.approx((HERE[0] + STRIDE, HERE[1]))]  # the walk's end, one stride on


def test_a_walk_that_ends_out_of_view_is_not_made():
    narrow = facts(slots=(), aspect=0.5)  # a window half as wide as it is high: 16 units east is off it
    assert reason(stride_of(narrow, (HERE[0] + 30.0, HERE[1]))) == UNSEEN
    assert isinstance(stride_of(replace(narrow, aspect=ASPECT), (HERE[0] + 30.0, HERE[1])), Step)


def test_a_wall_in_the_line_leaves_no_straight_stride():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    blocked = stride_of(facts(ground=ground, slots=(BLADE_WARP,)), goal)
    assert blocked == NoWay(WALLED)
    assert not blocked.arrived
    assert reason(stride_of(facts(ground=ground, slots=()), goal)) == WALLED
    # The stride asks for one jump: with the blade ready and a wall in its line it is not handed to Teleport
    assert reason(stride_of(facts(ground=ground), goal)) == WALLED
    # Teleport, when it is the jump, needs no line: it lands beyond the wall
    over = stride_of(facts(ground=ground, last_used={BLADE_WARP: NOW}), goal)
    assert isinstance(over, Step)
    assert (over.skill, over.spot) == (TELEPORT, pytest.approx(goal))


def test_a_few_units_up_to_a_wall_the_goal_stands_behind_is_no_stride_for_a_shot():
    ground = walled(wall_with_a_gap)
    goal = (5012.5, 5000.5)  # behind the wall at 5008 to 5010
    assert reason(stride_of(facts(ground=ground), goal, 6.0, shot=True)) == NO_SHOT
    assert stride_of(facts(ground=ground), goal, 6.0) == Step(pytest.approx((5006.5, 5000.5)))
    clear = stride_of(facts(), goal, 6.0, shot=True)  # no wall: the same walk is made
    assert clear == Step(pytest.approx((5006.5, 5000.5)))


def test_with_no_wall_known_there_is_no_way_round_to_look_for():
    goal = (5020.5, 5000.5)
    assert around_of(facts(), goal) == NoWay(OPEN_GROUND)
    assert around_of(facts(ground=None), goal) == NoWay(OPEN_GROUND)


def test_the_way_round_is_jumped_along_over_a_clear_line_and_walked_otherwise():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    empty = facts(ground=ground, staff=replace(IN_HAND, charges=0))
    jumped = around_of(empty, goal)
    assert isinstance(jumped, Step)
    assert jumped.skill == BLADE_WARP
    assert JUMP_LEAST <= math.dist(HERE, jumped.spot) <= JUMP_REACH
    for other in (replace(empty, last_used={BLADE_WARP: NOW}), replace(empty, staff=IN_HAND, slots=(TELEPORT,))):
        walk = around_of(other, goal)  # the blade in its delay, or Teleport alone: the way is walked
        assert isinstance(walk, Step)
        assert walk.skill is None
        assert math.dist(HERE, walk.spot) <= STRIDE


def test_no_way_round_a_wall_without_an_end_and_the_goals_own_cell_is_an_arrival():
    shut = facts(ground=walled(lambda x, y: not 5008 <= x < 5010), here=(5007.5, 5000.5))
    assert around_of(shut, (5020.5, 5000.5)) == NoWay(NO_WAY_ROUND)
    assert around_of(shut, (5007.9, 5000.1)) == NoWay(THERE, arrived=True)


def test_a_way_round_too_short_for_a_jump_or_a_walk_has_no_move():
    ground = walled(wall_with_a_gap)
    assert around_of(facts(ground=ground), (5002.5, 5000.5)) == NoWay(NO_SPOT_ON_WAY)
