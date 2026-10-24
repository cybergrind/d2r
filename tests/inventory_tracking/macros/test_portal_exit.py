"""A Town Portal is not cast under a level exit's click box (portal.py EXIT_CLEAR; 22:09 on 2026-10-23, Durance of
Hate Level 2: every aim at the portal had the warp tile under it and the loop stopped with Mephisto alive)."""

import math

from inventory_tracking.game.records import Warp
from inventory_tracking.macros import portal
from inventory_tracking.macros.portal import clear_spot, under_exit


HERE = (18014.5, 6872.5)  # where the level run ended, on the way down to Level 3
WARP = Warp(2510829173, 1, *HERE)  # lvlwarp 1: box (-15, -90, 75, 20)


def test_a_portal_on_the_warp_lies_under_it():
    assert under_exit(HERE, [WARP])


def test_a_portal_far_from_the_warp_is_cast_where_the_character_stands():
    far = Warp(1, 1, HERE[0] + 30, HERE[1] + 30)
    assert clear_spot(HERE, [far], None) == HERE


def test_on_the_warp_the_spot_is_off_it_within_the_rings():
    spot = clear_spot(HERE, [WARP], None)
    assert spot is not None
    assert spot != HERE
    assert not under_exit(spot, [WARP])
    assert math.dist(spot, HERE) <= max(portal.EXIT_RINGS) + 1e-6


class Walls:
    """Ground with only the cells west of x=18010 walkable."""

    def walkable(self, x, y):
        return x < 18010


def test_the_spot_is_on_footing(monkeypatch):
    from inventory_tracking.macros import travel

    monkeypatch.setattr(travel, 'clear_line', lambda *_: True)
    spot = clear_spot(HERE, [WARP], Walls())  # type: ignore[arg-type]
    assert spot is None or spot[0] < 18010


def test_a_warp_with_no_known_box_is_not_in_the_way():
    assert not under_exit(HERE, [Warp(1, 99999, *HERE)])
