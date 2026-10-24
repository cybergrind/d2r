"""LEG_SPIN (macros/loop.py, 2026-10-24; rca/2026-10-24/game5-findings.md): 23:30:44-23:31:05 on 2026-10-23, Halls of
the Dead Level 2, 21 'TZ next level' legs in 21 s under a tier 5 Herald pack, no strike, no move, the death. Legs that
end at once in a fight make the next leg the fight back."""

from dataclasses import replace

import pytest

from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import loop as module
from inventory_tracking.macros.loop import FIGHT_BACK, Loop
from tests.inventory_tracking.macros.fakes import player, world


HALLS_2 = 57  # Halls of the Dead Level 2 (levels.txt)
HERE = (15201.9, 8083.9)  # where the character stood from 23:30:57 (the log)


MAX = 2943  # CybergrindAA's life on 2026-10-23


def beset(*, near: float = 6.0, area: int = HALLS_2):
    """The character in `area` with a hostile `near` units off (monstats 101, the take's reviver)."""
    hostile = Monster(3504444985, 101, 1, HERE[0] + near, HERE[1], NO_OWNER, life=128, max_life=128)
    return world(area, player=player(area, x=HERE[0], y=HERE[1]), monsters=(hostile,))


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(module, 'LEG_SPIN', True)


def test_three_legs_within_a_second_and_a_half_in_a_fight_make_the_fight_back(on) -> None:
    loop, seen = Loop(on=True), beset()
    assert not loop.spinning(beset(), 100.0, (2943, MAX))
    assert not loop.spinning(beset(), 100.5, (2527, MAX))  # the take's lives at 23:30:57.3, 57.8 and 58.4
    assert loop.spinning(seen, 101.0, (2508, MAX))  # the take: one every 0.5 s
    loop.fight_back_due(seen.game_name)
    assert loop.after_beset(seen) == FIGHT_BACK
    assert not loop.spinning(seen, 101.4, (2500, MAX))  # counted afresh after it


def test_legs_spaced_out_or_with_nobody_near_or_across_levels_are_legs(on) -> None:
    loop = Loop(on=True)
    for t, life in ((100.0, 2943), (102.0, 2500), (104.0, 2000)):  # 2 s apart: a level each, or a walk
        assert not loop.spinning(beset(), t, (life, MAX))
    steady = Loop(on=True)
    for t in (100.0, 100.5, 101.0):
        assert not steady.spinning(beset(), t, (1752, MAX))  # not hurt: a Town Portal held, a pickup, a sweep
    quiet = Loop(on=True)
    for t, life in ((100.0, 2943), (100.5, 2527), (101.0, 2508)):
        assert not quiet.spinning(beset(near=40.0), t, (life, MAX))  # past SIGHT
    moving = Loop(on=True)
    for t, area, life in ((100.0, 56, 2943), (100.5, 57, 2527), (101.0, 60, 2508)):
        assert not moving.spinning(beset(area=area), t, (life, MAX))  # one level each: the way on


def test_in_town_or_switched_off_nothing_is_counted(monkeypatch) -> None:
    monkeypatch.setattr(module, 'LEG_SPIN', True)
    loop = Loop(on=True)
    falling = ((100.0, 2943), (100.5, 2527), (101.0, 2508))
    for t, life in falling:
        town = beset()
        assert town.player is not None
        assert not loop.spinning(replace(town, player=replace(town.player, area=103)), t, (life, MAX))
    monkeypatch.setattr(module, 'LEG_SPIN', False)
    off = Loop(on=True)
    assert not any(off.spinning(beset(), t, (life, MAX)) for t, life in falling)
