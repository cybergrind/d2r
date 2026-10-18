"""Recorded 2026-10-19: expired route Teleport poisoned later combat movement."""

import pytest

from inventory_tracking.builds import pursuing
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import OWN_MOVE, PRESSED, Step
from tests.inventory_tracking.macros.test_hunt import ASPECT, game, hunter, keys


@pytest.mark.parametrize('intent', [OWN_MOVE, PRESSED], ids=['firing-stand', 'route'])
def test_expired_move_does_not_disable_own_teleport(intent):
    play = game()
    play.staff = None
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    run = play.run()
    assert hunt.travel.jump_by(run, play.world) == TELEPORT
    with pytest.raises(Abort, match='priced act expired'), hunt.priced_for(run, 0.001):
        hunt.travel.make(run, Step((5012.0, 5000.0), TELEPORT), play.world, ASPECT, keys, Ground(()), intent=intent)
    assert hunt.travel.jump_failed == {}
    assert hunt.travel.jump_by(run, play.world) == TELEPORT


@pytest.mark.parametrize('intent', [OWN_MOVE, PRESSED], ids=['firing-stand', 'route'])
def test_successful_retry_restores_teleport_for_every_movement_caller(intent):
    play = game()
    play.staff = None
    hunt = hunter(play)
    run = play.run()
    # The route retries after 3 s; a firing stand distrusts a failure for 30 s.
    hunt.travel.jump_failed[TELEPORT] = play.clock.now - 4.0
    assert hunt.travel.jump_by(run, play.world) != TELEPORT
    if intent == OWN_MOVE:
        hunt.travel.jump(run, Step((5012.0, 5000.0), TELEPORT), play.character, ASPECT, keys)
    else:
        hunt.travel.make(run, Step((5012.0, 5000.0), TELEPORT), play.world, ASPECT, keys, Ground(()), intent=intent)
    assert play.character.x > 5010.0  # observed landing, not just a submitted key
    assert hunt.travel.jump_by(run, play.world) == TELEPORT


@pytest.mark.parametrize('ground', [Ground(()), pytest.param('walls', id='known-collision-without-rooms')])
def test_own_teleport_remains_the_route_strategy_before_room_map_arrives(ground):
    from tests.inventory_tracking.macros.moves import wall_with_a_gap, walled

    play = game()
    play.staff = None
    hunt, run = hunter(play), play.run()
    known_ground = walled(wall_with_a_gap) if ground == 'walls' else ground
    found = hunt.travel.toward(run, play.world, known_ground, ASPECT, (5070.0, 5000.0), PRESSED)
    assert isinstance(found, Step)
    assert found.skill == TELEPORT
    assert 5000.0 < found.spot[0] <= 5026.0


def test_roomless_teleport_respects_known_landing_collision():
    from tests.inventory_tracking.macros.moves import walled

    play = game()
    play.staff = None
    hunt, run = hunter(play), play.run()
    ground = walled(lambda x, y: x < 5008)
    found = hunt.travel.toward(run, play.world, ground, ASPECT, (5070.0, 5000.0), PRESSED)
    assert not isinstance(found, Step)  # every candidate landing is blocked


def test_roomless_charged_staff_keeps_its_free_jump_policy():
    from inventory_tracking.builds.warlock.skills import BLADE_WARP

    play = game()  # charged staff, not Enigma
    hunt, run = hunter(play), play.run()
    found = hunt.travel.toward(run, play.world, Ground(()), ASPECT, (5070.0, 5000.0), PRESSED)
    assert isinstance(found, Step)
    assert found.skill == BLADE_WARP
