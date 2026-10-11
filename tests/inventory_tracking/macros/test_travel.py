"""One move of the hunt's own (macros/travel.py): which jumps the character has, and a step made by one."""

from dataclasses import replace

import pytest

from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import BLADE_WARP, TELEPORT
from inventory_tracking.macros.travel import JUMP_DISTRUST, LOW_CHARGES, WARP_DELAY, Step, Travel, step_line
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
