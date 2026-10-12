"""One move of the hunt's own (macros/travel.py): which jumps the character has, and a step made by one."""

from dataclasses import replace

import pytest

from inventory_tracking.combat.stance import no_footing
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import BLADE_WARP, TELEPORT
from inventory_tracking.macros.travel import (
    JUMP_DISTRUST,
    LOW_CHARGES,
    WARP_DELAY,
    Step,
    Travel,
    step_line,
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
