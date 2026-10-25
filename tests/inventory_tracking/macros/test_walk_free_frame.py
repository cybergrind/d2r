"""travel.py WALK_FREE_FRAME (2026-10-25, rca/2026-10-25/smoothness-findings.md §3.3): a walk chosen in a cast clicks
at the first look that reads the cast over, not after SWAP_SETTLE free; one the game swallowed is clicked again,
settled. Off: as before. A walk that set off and is held short of MOVED by a body is watched the whole STEP_WALK_SECONDS
with it on: the Tower Cellar 5 replay pins it (tests/inventory_tracking/scenarios/battle, the arm on 18 passed)."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.macros import travel as travel_module
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.routines import SWAP_SETTLE
from inventory_tracking.macros.travel import step_walk
from tests.inventory_tracking.macros.fakes import Game, world
from tests.inventory_tracking.macros.moves import ASPECT


CAST_LEFT = 0.15  # seconds of the strike's cast left when the walk is chosen


def casting() -> Game:
    play = Game(world())
    play.world = replace(play.world, player=replace(play.character, mode=7))
    play.acting_until = play.clock.now + CAST_LEFT
    return play


@pytest.mark.parametrize('on', [False, True], ids=['off', 'on'])
def test_a_walk_chosen_in_a_cast_clicks_at_its_end_only_with_the_switch(monkeypatch, on):
    monkeypatch.setattr(travel_module, 'WALK_FREE_FRAME', on)
    play = casting()
    run = play.run()
    began = play.clock.now
    settled = step_walk(run, (5010.0, 5000.0), play.world.player, ASPECT, [])
    assert len(play.walks) == 1
    if on:
        assert CAST_LEFT <= settled < CAST_LEFT + SWAP_SETTLE / 2  # the cast's rest, one look more
    else:
        assert settled >= CAST_LEFT + SWAP_SETTLE - 0.02  # free for SWAP_SETTLE on end after the cast (a 0.02 s look)
    assert play.clock.now - began < 1.0


def test_on_the_saving_is_the_settle_and_a_free_character_walks_as_before(monkeypatch):
    took = {}
    for on in (False, True):
        monkeypatch.setattr(travel_module, 'WALK_FREE_FRAME', on)
        play = casting()
        took[on] = step_walk(play.run(), (5010.0, 5000.0), play.world.player, ASPECT, [])
    assert took[False] - took[True] >= SWAP_SETTLE * 0.75
    # A free character: no settle either way, one click
    for on in (False, True):
        monkeypatch.setattr(travel_module, 'WALK_FREE_FRAME', on)
        play = Game(world())
        assert step_walk(play.run(), (5010.0, 5000.0), play.world.player, ASPECT, []) == 0.0
        assert len(play.walks) == 1


def test_on_a_click_the_game_swallowed_is_made_again_settled_and_said(monkeypatch, caplog):
    monkeypatch.setattr(travel_module, 'WALK_FREE_FRAME', True)
    play = casting()
    play.swallowed_clicks = 1  # the cast's last frame took the first click
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        settled = step_walk(play.run(), (5010.0, 5000.0), play.world.player, ASPECT, [])
    assert len(play.walks) == 1  # the second click walked
    assert settled >= SWAP_SETTLE  # and it was settled
    assert 'showed no move' in caplog.text


def test_off_a_swallowed_click_ends_the_walk_as_before(monkeypatch):
    monkeypatch.setattr(travel_module, 'WALK_FREE_FRAME', False)
    play = casting()
    play.swallowed_clicks = 1
    with pytest.raises(Abort, match='did not move'):
        step_walk(play.run(), (5010.0, 5000.0), play.world.player, ASPECT, [])
