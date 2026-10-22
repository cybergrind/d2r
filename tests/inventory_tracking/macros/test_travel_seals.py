"""Walk clicks kept off a closed Chaos Sanctuary seal (travel.py WALK_OFF_SEALS, 2026-10-21): the arena's CS run (seed
3) walked "7 toward Infector seal 2" at 169.31 s as a safety retreat and firing spot while the Infector was fought; the
walk's click on the seal's picture opened it at 170.36 s, before the Infector died (173.0 s), out of the route's order
(tests/inventory_tracking/scenarios/arena/situations/test_cs_run.py, the seal's pack before the last seal)."""

import logging
import math

import pytest

from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import SEALS
from inventory_tracking.macros import travel
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.travel import step_walk
from tests.inventory_tracking.macros.fakes import Game, world
from tests.inventory_tracking.macros.moves import ASPECT


GOAL = (5010.0, 5000.0)
INFECTOR_SEAL_2 = SEALS[1]  # 393, DiabloSeal2


def seal_under(play: Game, goal: tuple[float, float], mode: int = 0, txt: int = INFECTOR_SEAL_2) -> Thing:
    """A seal standing where a click at `goal` has its picture under the pointer (the fakes' `thing_above`)."""
    lift = play.thing_above / 16
    play.thing = Thing(1211830634, txt, mode, goal[0] + lift, goal[1] + lift)
    return play.thing


def test_a_walk_click_on_a_closed_seal_is_moved_off_it_and_the_seal_stays_closed(monkeypatch, caplog):
    monkeypatch.setattr(travel, 'WALK_OFF_SEALS', True)
    play = Game(world())
    run = play.run()
    seal_under(play, GOAL)
    assert travel.closed_seal(run, (2, 1211830634))

    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        step_walk(run, GOAL, play.world.player, ASPECT, [], name='Infector seal 2')

    assert play.thing is not None
    assert play.thing.mode == 0  # not opened by the walk
    assert len(play.walks) == 1
    assert math.dist(play.walks[0], GOAL) < 3.5
    assert 'Macro: walk toward Infector seal 2: a closed seal (2, 1211830634) under the click at' in caplog.text


def test_with_the_switch_off_the_walk_click_opens_the_seal_as_before(monkeypatch):
    monkeypatch.setattr(travel, 'WALK_OFF_SEALS', False)
    play = Game(world())
    run = play.run()
    seal_under(play, GOAL)

    with pytest.raises(Abort, match='did not move'):
        step_walk(run, GOAL, play.world.player, ASPECT, [], name='Infector seal 2')  # the click operated it

    assert play.thing is not None
    assert play.thing.mode != 0


@pytest.mark.parametrize(('mode', 'txt'), [(1, INFECTOR_SEAL_2), (0, 0)], ids=['a seal already open', 'another object'])
def test_an_open_seal_or_another_object_is_not_walked_round(monkeypatch, mode, txt):
    monkeypatch.setattr(travel, 'WALK_OFF_SEALS', True)
    play = Game(world())
    run = play.run()
    seal_under(play, GOAL, mode=mode, txt=txt)
    over = (2, 1211830634)
    assert not travel.closed_seal(run, over)
    assert not travel.closed_seal(run, None)
    assert not travel.closed_seal(run, (4, 1211830634))  # an item of the same id is no seal
