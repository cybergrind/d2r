"""pickup.py PICK_AT_ONCE (2026-10-25, rca/2026-10-25/smoothness-findings.md §3.2): a near pickup's click returns at
once, the drop out of every choice for AT_ONCE_SECONDS, its "picked up" read at the next looks (`pending`); one still on
the ground is a target again and its next click waits. Off: the click waits for the item to leave the ground."""

import logging
import re
from dataclasses import replace

import pytest

from inventory_tracking.game.records import VALUABLE, Drop, Loot
from inventory_tracking.macros import pickup
from inventory_tracking.macros.pickup import pick_up
from tests.inventory_tracking.macros.test_pickup import LEVEL, game, keys, nothing


GAME = ('cybergg1', 1)
NEAR = Drop(70, 5001.5, 5001.0, 'Ist Rune', VALUABLE)
LAG = 0.12  # seconds the game takes to lift the item after the click (the session's click -> off the ground p50 0.15)
PICKED = re.compile(r'Macro: picked up (.+?) [\d.]+s after')  # the watch's (d2-loop-watch logwords.py PICKED)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(pickup, 'PENDING', {})
    monkeypatch.setattr(pickup, 'AT_ONCE_MISSED', set())
    monkeypatch.setattr(pickup, 'CLICKED', {})
    monkeypatch.setattr(pickup, 'SEEN', {})


def lagged(play, *drops):
    """The game with `drops` read on the ground for LAG s after the fake's click took them; its run."""
    play.loot = replace(play.loot, game=GAME)
    run = play.run()
    taken: dict[int, float] = {}
    read = run.loot

    def loot() -> Loot:
        now = play.clock.now
        found = read()
        for drop in drops:
            if drop.label in play.picked and drop.unit_id not in taken:
                taken[drop.unit_id] = now
        still = tuple(d for d in drops if d.unit_id in taken and now - taken[d.unit_id] < LAG)
        return replace(found, drops=(*found.drops, *still))

    run.loot = loot
    return run


def test_a_near_pickup_waits_for_the_lift_only_with_the_switch_off(monkeypatch):
    spent = {}
    for on in (False, True):
        monkeypatch.setattr(pickup, 'PICK_AT_ONCE', on)
        pickup.PENDING.clear()
        play = game(NEAR)
        run = lagged(play, NEAR)
        began = play.clock.now
        assert pick_up(run, LEVEL, keys, nothing)
        spent[on] = play.clock.now - began
        assert play.picked == ['Ist Rune']
        assert (NEAR.unit_id in pickup.PENDING) == on
    assert spent[False] - spent[True] >= LAG - 0.05  # the lift, less the wait's last poll


def test_on_the_drop_is_out_of_every_choice_until_read_and_its_pickup_said_once(monkeypatch, caplog):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', True)
    play = game(NEAR)
    run = lagged(play, NEAR)
    pick_up(run, LEVEL, keys, nothing)
    assert NEAR in run.loot().drops  # the game has not lifted it yet
    assert NEAR not in pickup.unshunned(run.loot(), play.clock.now).drops  # but no choice goes for it again
    play.clock.now += LAG
    with caplog.at_level(logging.INFO):
        pickup.unshunned(run.loot(), play.clock.now)
        pickup.unshunned(run.loot(), play.clock.now + 0.1)
    said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: picked up')]
    assert len(said) == 1
    assert 'read picked up at a later look' in caplog.text
    found = PICKED.search(said[0])
    assert found is not None
    assert found.group(1) == 'Ist Rune'
    assert pickup.PENDING == {}


def test_on_a_click_that_took_nothing_makes_the_drop_a_target_again_and_its_next_click_waits(monkeypatch, caplog):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', True)
    play = game(NEAR)
    play.deaf_picks = 1  # the game took no notice of the first click
    run = lagged(play, NEAR)
    assert pick_up(run, LEVEL, keys, nothing)
    assert play.picked == []
    with caplog.at_level(logging.INFO):
        loot = pickup.unshunned(run.loot(), play.clock.now + pickup.AT_ONCE_SECONDS)
    assert NEAR in loot.drops  # a target again
    assert 'still on the ground' in caplog.text
    assert NEAR.unit_id in pickup.AT_ONCE_MISSED
    assert NEAR.unit_id in pickup.CLICKED  # a valuable watched as a click's (`late`)
    play.clock.now += pickup.AT_ONCE_SECONDS
    assert pick_up(run, LEVEL, keys, nothing)  # the next press: its click waits, as before
    assert play.picked == ['Ist Rune']
    assert NEAR.unit_id not in pickup.PENDING


def test_on_a_far_drop_and_an_unread_look_change_nothing(monkeypatch):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', True)
    far = Drop(71, 5008.0, 5003.0, 'Ist Rune', VALUABLE)
    play = game(far)
    run = lagged(play, far)
    assert pick_up(run, LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    pickup.PENDING[NEAR.unit_id] = (NEAR, play.clock.now, (0, -24), 1.0, None)
    pickup.unshunned(Loot(), play.clock.now + 1.0)  # unread: nothing is known off the ground
    assert NEAR.unit_id in pickup.PENDING
