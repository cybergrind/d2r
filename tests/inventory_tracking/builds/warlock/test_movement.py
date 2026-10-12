"""How a Warlock moves (builds/warlock/movement.py): Blade Warp as a jump source, before Teleport in every set.

The first half asks the sets with facts alone; the second makes moves with `Travel` in the fakes' game.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.movement import (
    BLADE_WARP_JUMP,
    BLADE_WARP_SOURCE,
    MOVEMENT,
    WARP_DELAY,
    WARP_SECONDS,
    WARP_SPEED,
)
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import MoveFacts, NoWay
from inventory_tracking.macros.movement import SHARED, OwnTeleport, StaffTeleport, Walk
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import (
    JUMP_DISTRUST,
    JUMP_LEAST,
    JUMP_REACH,
    LOW_CHARGES,
    OWN_MOVE,
    PLAYER_STEP,
    SEEK,
    STRIDE,
    WALLED,
    Step,
    Travel,
    move_facts,
    navigator,
    spare_jump,
    step_line,
)
from inventory_tracking.macros.world import Teleport
from tests.inventory_tracking.macros import moves
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world
from tests.inventory_tracking.macros.moves import ASPECT, HERE, IN_HAND, NOW, skills, wall_with_a_gap, walled


def facts(**changes) -> MoveFacts:
    """The character at HERE on a level with no wall read, Blade Warp and Teleport on keys, no staff worn."""
    changes.setdefault('slots', (BLADE_WARP, None, TELEPORT))
    return moves.facts(**changes)


def jumps_of(here: MoveFacts, intent=OWN_MOVE):
    """The jumps of the set that applies, as `Travel.jumps` asks them."""
    movement = navigator(MOVEMENT, here)
    assert movement is not None
    return movement.jumps(here, intent)


def leg_of(here: MoveFacts, goal, intent=OWN_MOVE):
    movement = navigator(MOVEMENT, here)
    assert movement is not None
    return movement.leg(here, goal, intent)


def test_the_blade_is_a_thrown_jump_with_a_casting_delay():
    assert (BLADE_WARP_JUMP.skill, BLADE_WARP_JUMP.line) == (BLADE_WARP, True)
    assert (BLADE_WARP_JUMP.seconds, BLADE_WARP_JUMP.speed) == (WARP_SECONDS, WARP_SPEED) == (0.35, 45.0)
    assert (BLADE_WARP_JUMP.reach, BLADE_WARP_JUMP.least) == (JUMP_REACH, JUMP_LEAST)
    assert (BLADE_WARP_SOURCE.jump, BLADE_WARP_SOURCE.delay) == (BLADE_WARP_JUMP, WARP_DELAY)
    assert WARP_DELAY == 0.8


def test_the_warlocks_sets_are_the_shared_ones_with_the_blade_first():
    assert [type(movement) for movement in MOVEMENT] == [StaffTeleport, OwnTeleport, Walk]
    for movement, shared in zip(MOVEMENT, SHARED, strict=True):
        assert movement.sources == (BLADE_WARP_SOURCE, *shared.sources)
    assert spare_jump(MOVEMENT, HUNT_SLOTS) == BLADE_WARP_JUMP
    assert spare_jump(MOVEMENT, (TELEPORT,)) is None


def test_blade_warp_ready_comes_before_teleport():
    found = jumps_of(facts())
    assert skills(found) == [BLADE_WARP, TELEPORT]
    assert [(jump.line, jump.reach, jump.least) for jump in found] == [
        (True, JUMP_REACH, JUMP_LEAST),
        (False, JUMP_REACH, JUMP_LEAST),
    ]


def test_blade_warp_in_its_casting_delay_is_no_jump_until_the_delay_is_over():
    assert skills(jumps_of(facts(last_used={BLADE_WARP: NOW - 0.1}))) == [TELEPORT]
    made = facts(now=0.5, last_used={BLADE_WARP: 0.0})
    assert skills(jumps_of(made)) == [TELEPORT]
    assert skills(jumps_of(replace(made, now=WARP_DELAY))) == [BLADE_WARP, TELEPORT]  # over at the delay itself
    assert skills(jumps_of(facts(last_used={BLADE_WARP: -math.inf}))) == [BLADE_WARP, TELEPORT]  # never made
    assert skills(jumps_of(facts(last_used={TELEPORT: NOW}))) == [BLADE_WARP, TELEPORT]  # Teleport has no delay


def test_a_jump_that_moved_nothing_is_distrusted_for_as_long_as_the_caller_says():
    failed = facts(failed={BLADE_WARP: NOW - JUMP_DISTRUST})
    assert skills(jumps_of(failed)) == [TELEPORT]  # to the second: left out
    assert skills(jumps_of(replace(failed, now=NOW + 0.5))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(failed, PLAYER_STEP)) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(failed={TELEPORT: NOW - 1.0}))) == [BLADE_WARP]
    assert jumps_of(facts(failed={BLADE_WARP: NOW - 1.0, TELEPORT: NOW - 1.0})) == ()


def test_the_staff_in_hand_is_jumped_by_down_to_the_floor_of_charges():
    def worn(charges: int) -> MoveFacts:
        return facts(staff=replace(IN_HAND, charges=charges))

    assert skills(jumps_of(worn(69))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(worn(LOW_CHARGES))) == [BLADE_WARP, TELEPORT]  # the floor itself is still spent
    assert skills(jumps_of(worn(LOW_CHARGES - 1))) == [BLADE_WARP]
    assert skills(jumps_of(worn(0))) == [BLADE_WARP]
    for intent in (SEEK, PLAYER_STEP):  # the same floor whoever asks a set: the player's hop is not a set's
        assert skills(jumps_of(worn(LOW_CHARGES - 1), intent)) == [BLADE_WARP]


def test_the_staff_in_the_other_weapon_set_is_a_swap_away_and_no_jump():
    assert skills(jumps_of(facts(staff=replace(IN_HAND, in_hand=False)))) == [BLADE_WARP]


def test_with_no_staff_teleport_is_the_characters_own_skill():
    assert skills(jumps_of(facts(staff=None))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(staff=None, slots=(TELEPORT,)))) == [TELEPORT]


def test_a_skill_that_is_on_no_key_is_no_jump():
    assert jumps_of(facts(slots=())) == ()
    assert jumps_of(facts(slots=(None, 7))) == ()
    assert skills(jumps_of(facts(slots=(BLADE_WARP,), staff=IN_HAND))) == [BLADE_WARP]


def test_a_stride_is_by_the_blade_and_by_teleport_while_its_delay_runs():
    goal = (HERE[0] + 30.0, HERE[1])
    short = replace(OWN_MOVE, short=14.0)
    assert leg_of(facts(), goal, short) == Step(pytest.approx((HERE[0] + 16.0, HERE[1])), BLADE_WARP)
    delayed = facts(last_used={BLADE_WARP: NOW})
    assert leg_of(delayed, goal, short) == Step(pytest.approx((HERE[0] + 16.0, HERE[1])), TELEPORT)
    assert leg_of(facts(slots=()), goal) == Step(pytest.approx((HERE[0] + STRIDE, HERE[1])))


def test_a_wall_in_the_blades_line_is_not_handed_to_teleport():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    assert leg_of(facts(ground=ground, slots=(BLADE_WARP,)), goal) == NoWay(WALLED)
    # The stride asks for one jump: with the blade ready and a wall in its line it is not handed to Teleport
    assert leg_of(facts(ground=ground), goal) == NoWay(WALLED)
    # Teleport, when it is the jump, needs no line: it lands beyond the wall
    over = leg_of(facts(ground=ground, last_used={BLADE_WARP: NOW}), goal)
    assert isinstance(over, Step)
    assert (over.skill, over.spot) == (TELEPORT, pytest.approx(goal))


def test_the_way_round_is_jumped_along_by_the_blade_and_walked_otherwise():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    round_it = replace(SEEK, detour=True)
    empty = facts(ground=ground, staff=replace(IN_HAND, charges=0))
    jumped = leg_of(empty, goal, round_it)
    assert isinstance(jumped, Step)
    assert jumped.skill == BLADE_WARP
    assert JUMP_LEAST <= math.dist(HERE, jumped.spot) <= JUMP_REACH
    for other in (replace(empty, last_used={BLADE_WARP: NOW}), replace(empty, staff=IN_HAND, slots=(TELEPORT,))):
        walk = leg_of(other, goal, round_it)  # the blade in its delay, or Teleport alone: the way is walked
        assert isinstance(walk, Step)
        assert walk.skill is None
        assert math.dist(HERE, walk.spot) <= STRIDE


def test_the_blades_delay_is_waited_out_for_the_seek_step_where_its_line_is_clear():
    goal = (HERE[0] + 30.0, HERE[1])
    just = facts(last_used={BLADE_WARP: NOW - 0.3})
    for movement in MOVEMENT:
        assert movement.wait(just, goal, SEEK) == pytest.approx(WARP_DELAY - 0.3)
        assert movement.wait(just, goal, OWN_MOVE) == 0.0
        assert movement.wait(replace(just, ground=walled(wall_with_a_gap)), (5020.5, 5000.5), SEEK) == 0.0
        assert movement.wait(replace(just, slots=(TELEPORT,)), goal, SEEK) == 0.0


# --- Travel, in the fakes' game, with the Warlock's sets -------------------------------------------------


def keys(_world, wanted):
    return {skill: KEYS[skill] for skill in wanted}


def game(**changes):
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    play = Game(world(**changes))
    play.staff = Teleport(10, 20, True)
    return play


def test_the_jumps_are_blade_warp_first_then_teleport_without_a_swap():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    assert [jump.line for jump in travel.jumps(run, play.world)] == [True, False]
    travel.warped_at = play.clock.now  # its casting delay runs
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += WARP_DELAY
    assert travel.jump_by(run, play.world) == BLADE_WARP
    travel.warped_at = play.clock.now
    play.staff = replace(play.staff, in_hand=False)  # a swap away: not a jump
    assert travel.jump_by(run, play.world) is None


def test_low_on_charges_the_modes_own_jumps_leave_the_staff_alone():
    # user, 2026-10-11: "track number of tp charges when using staff, and leverage warp more when low"
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    play.staff = replace(play.staff, charges=LOW_CHARGES)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    play.staff = replace(play.staff, charges=LOW_CHARGES - 1)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP]
    travel.warped_at = play.clock.now
    assert travel.jump_by(run, play.world) is None  # its delay runs: a walk, not a charge


def test_a_blade_warp_that_moved_nothing_is_left_out_for_a_while():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    play.warp_lands = False
    with pytest.raises(Abort, match='Blade Warp: the character did not move'):
        travel.make(run, Step((5012.0, 5000.0), BLADE_WARP), play.world, ASPECT, keys, Ground(()))
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += JUMP_DISTRUST + 1
    assert travel.jump_by(run, play.world) == BLADE_WARP


def test_a_blade_warp_made_is_remembered_for_its_casting_delay():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    assert travel.delayed == {BLADE_WARP}
    travel.make(run, Step((5012.0, 5000.0), BLADE_WARP), play.world, ASPECT, keys, Ground(()))
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert travel.warped_at == pytest.approx(play.clock.now, abs=2.0)
    assert set(travel.jumped_at) == {BLADE_WARP}
    read = move_facts(run, run.world(), None, ASPECT, travel)
    assert read.since_used(BLADE_WARP) == pytest.approx(play.clock.now - travel.warped_at)


def test_a_straight_stride_is_by_blade_warp_and_ends_short_of_its_goal():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    found = travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), replace(OWN_MOVE, short=14.0))
    assert found is not None
    assert found.skill == BLADE_WARP
    assert found.spot == pytest.approx((5016.0, 5000.0))
    assert step_line(found, (5000.0, 5000.0)) == 'a stride of 16 toward the nearest, by Blade Warp'


def test_with_no_straight_stride_a_move_is_made_along_the_way_round_the_wall():
    # Drifter Cavern, 09:43 on 2026-10-12: the staff empty and the firing spot behind a wall.
    play = game()
    play.staff = replace(play.staff, charges=0)
    ground = walled(wall_with_a_gap)
    travel, run = Travel(MOVEMENT), play.run()
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
