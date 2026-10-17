"""Deckard Cain's Identify Items, the KP_6 loop's mass identify (macros/cain.py; routes/lower-kurast-loop-plan.md §15).
The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to
loop"."""

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cain import CAIN, identify_all
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.shop import known
from inventory_tracking.macros.world import Carried, Monster, Pack
from tests.inventory_tracking.macros.fakes import CAIN_LINE, Game, player, world


FORTRESS = 103
START = (5048.0, 5044.0)  # where a game begins, by the waypoint
CAIN_AT = (5022.8, 5032.7)  # the take 20261017T085221Z-103
CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
KRISS = Carried(11, 41, 2, 0, (1, 3), quality=4, identified=False)
CODEX = Carried(12, 510, 0, 0, (2, 2), quality=4, identified=False)  # in the cube


def fortress() -> Game:
    cain = Monster(78, CAIN, 1, *CAIN_AT, 0xFFFFFFFF)
    play = Game(world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]), monsters=(cain,)))
    play.vendor = cain
    play.pack = Pack((CUBE, KRISS), ('...',) * 4, in_cube=(CODEX,), cube_items=frozenset({CODEX.unit_id}))
    return play


def test_cain_identifies_the_inventorys_and_the_cubes_items_at_once_and_his_line_is_learned():
    play = fortress()

    assert identify_all(play.run(), (KRISS, CODEX)) == 2

    assert play.pack is not None
    assert all(i.identified for i in (*play.pack.items, *play.pack.in_cube))
    assert known(CAIN) == pytest.approx(CAIN_LINE, abs=0.012)  # the first lift scanned that took
    assert play.world.open_panels == ()


def test_no_cain_where_he_stands_stops_the_visit():
    play = fortress()
    play.world = world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]))
    play.vendor = None
    with pytest.raises(Abort, match='not in sight'):  # walked toward his usual place first (shop.py USUAL)
        identify_all(play.run(), (KRISS,))


def test_his_lines_are_tried_nearest_the_learned_one_first(monkeypatch):
    # 17:05:56-17:06:03 on 2026-10-17: from 0.16 up it took four tries, 8.5 s, with the learned one two steps off
    from inventory_tracking.macros import cain

    monkeypatch.setattr(cain, 'known', lambda vendor: 0.2165)
    tried = cain.lifts()
    assert tried[0] == 0.2165
    assert {round(abs(lift - 0.2165), 4) for lift in tried[1:3]} == {round(cain.LINE / 2, 4)}  # a half line either side
