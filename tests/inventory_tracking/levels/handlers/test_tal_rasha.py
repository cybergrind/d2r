"""Tal Rasha's Tombs (areas 66-72): the Orifice in the true tomb, the way back in every tomb.

Win+C dump 20260930T154636Z-55eebd5c (fixture tal_rasha_true_tomb, area 70): the true tomb holds
'Act 2 - Tomb Talrasha S' (16x16); the orifice object (objects.json 152, "Where you place the
Horadric staff") stood at (22618, 11123), in that room. D2MOO DrlgMaze places the Talrasha room
only in the staff tomb, and a 'Tomb Prev' room (the way back) in every tomb.
"""

import pytest

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import replay


def test_the_true_tomb_points_at_the_orifice():
    snapshot = replay('tal_rasha_true_tomb')

    guidance = handler_for(70).guide(snapshot)

    orifice, back = guidance.pois
    assert (orifice.label, orifice.kind, preset_name(orifice.room.preset)) == (
        'Orifice',
        'target',
        'Act 2 - Tomb Talrasha S',
    )
    assert orifice.room.x <= 22618 / TILE_UNITS < orifice.room.x + orifice.room.width
    assert orifice.room.y <= 11123 / TILE_UNITS < orifice.room.y + orifice.room.height
    assert pointer(orifice, snapshot.location).here  # the dump was taken at the orifice
    assert (back.label, back.kind) == ('Canyon of the Magi', 'previous')
    assert guidance.problems == ()
    assert handler_for(70).confirmed


@pytest.mark.parametrize('area', [66, 67, 68, 69, 71, 72])
def test_a_false_tomb_shows_only_the_way_back_and_is_quiet(area):
    rooms = (Room(444, 0, 0, 16, 16), Room(416, 16, 0, 16, 16))  # Tomb Prev SEW, Tomb EW
    guidance = handler_for(area).guide(LevelSnapshot(Location(area, 0, 40, 40), rooms))

    assert [p.label for p in guidance.pois] == ['Canyon of the Magi']
    assert guidance.problems == ()
