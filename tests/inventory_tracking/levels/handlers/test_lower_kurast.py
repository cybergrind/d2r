"""Lower Kurast super chests: the bonfire camp (user, 2026-09-30: LK super chests don't sparkle;
two shacks by a fire, chests inside).

Win+C dump 20260930T124726Z-e166c530 (fixture lower_kurast_camp), taken inside one shack: the camp
is 'Act 3 - Slums 16x16' DS1 variant 1 (fire at 5416,2211, jungle torches around it, a jungle chest
in each shack at 5420,2172 and 5428,2221). It was the only variant-1 instance among 80 rooms;
the other 16x16 blocks (variants 0 and 2) have no fire.

The chests (2026-10-15): the camp's file places three `PlaceUniqueChest` spots, at (27, 52), (12, 57) and (60, 12)
units from its origin; a mark is on each (levels/model.py UNIQUE_CHEST).
"""

import json
import math
from dataclasses import replace

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.model import UNIQUE_CHEST, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import FIXTURES, handler_of, replay


SLUMS_16X16 = 618
EXITS = (Room(613, 64, 0, 8, 8), Room(631, 72, 0, 8, 8), Room(614, 64, 56, 8, 8))  # Gate N, Waypoint, Gate S


CHESTS = ((27, 52), (12, 57), (60, 12))  # units from the camp's origin, as its file places them


def camps(guidance):
    return [poi for poi in guidance.pois if poi.label == 'Super chests']


def units(poi):
    assert poi.spot is not None
    return (round(poi.spot[0] * TILE_UNITS), round(poi.spot[1] * TILE_UNITS))


def chests_of(x, y):
    """The marks' places (world units) of a camp whose origin is at tile (x, y)."""
    return [(x * TILE_UNITS + dx, y * TILE_UNITS + dy) for dx, dy in CHESTS]


def camp(x, y, variant):
    """A 16x16 preset split into four 8x8 chunks, as the client holds it."""
    return tuple(Room(SLUMS_16X16, x + dx, y + dy, 8, 8, variant, (x, y, 16, 16)) for dx in (0, 8) for dy in (0, 8))


def test_the_real_camp_is_found_and_the_player_stands_in_it():
    snapshot = replay('lower_kurast_camp')
    handler = handler_of(79)

    guidance = handler.guide(snapshot)

    found = camps(guidance)
    assert [(poi.label, preset_name(poi.room.preset), poi.kind, poi.use) for poi in found] == [
        ('Super chests', 'Act 3 - Slums 16x16', 'target', UNIQUE_CHEST)
    ] * 3
    # On the jungle chests the dump shows there: 183 at (5387, 2212), 181 at (5372, 2217) and (5420, 2172).
    assert [units(poi) for poi in found] == chests_of(1072, 432) == [(5387, 2212), (5372, 2217), (5420, 2172)]
    assert any(pointer(poi, snapshot.location).here for poi in found)
    assert guidance.problems == ()
    assert handler.confirmed


def test_every_camp_is_marked_and_other_variants_are_not():
    rooms = camp(0, 0, 1) + camp(16, 0, 0) + camp(32, 0, 2) + camp(48, 0, 1) + EXITS
    guidance = handler_of(79).guide(LevelSnapshot(Location(79, 0, 5, 5), rooms))

    assert [units(p) for p in camps(guidance)] == chests_of(0, 0) + chests_of(48, 0)
    assert guidance.problems == ()


def test_a_level_without_a_camp_is_quiet():
    guidance = handler_of(79).guide(LevelSnapshot(Location(79, 0, 5, 5), camp(0, 0, 0) + EXITS))

    assert camps(guidance) == []
    assert guidance.problems == ()


def test_a_level_whose_layouts_are_all_read_and_hold_no_camp_has_no_chests_to_wait_for():
    # lower-kurast-plan.md task 5: the client holds every room of the level and each 16x16's file from entry (all
    # three fixtures: no layout unread). None a camp: the chests are absent, and the route's stage done with.
    def guide(*rooms):
        return handler_of(79).guide(LevelSnapshot(Location(79, 0, 5, 5), (*rooms, *EXITS)))

    assert guide(*camp(0, 0, 0), *camp(16, 0, 2)).absent == frozenset({'Super chests'})
    assert guide(*camp(0, 0, 0), *camp(16, 0, 1)).absent == frozenset()  # a camp
    assert guide(*camp(0, 0, 0), *camp(16, 0, None)).absent == frozenset()  # a layout not read: maybe a camp
    unread_chunk = (*camp(0, 0, 0)[:3], replace(camp(0, 0, 0)[3], variant=None))
    assert guide(*unread_chunk).absent == frozenset({'Super chests'})  # any chunk's reading is the preset's
    for name in ('lower_kurast_camp', 'lower_kurast_game2', 'lower_kurast_two_camps'):
        snapshot = replay(name)
        assert all(room.variant is not None for room in snapshot.rooms if room.preset == SLUMS_16X16)
        assert handler_of(79).guide(snapshot).absent == frozenset()


def test_a_second_game_finds_its_camp_elsewhere():
    # Evidence 20260930T125427 from another game; the user confirmed the mark in game.
    snapshot = replay('lower_kurast_game2')

    guidance = handler_of(79).guide(snapshot)

    assert [units(p) for p in camps(guidance)] == chests_of(1016, 560)
    assert guidance.problems == ()


def test_two_camps_give_six_marks_each_on_a_chest_the_dump_shows():
    # Level dump 20261006T184600Z-26ba144d (2026-10-06 21:46): camps at tiles (1064, 504) and (1112, 528); the
    # character stood in the second, whose three placed chests were loaded (two of them opened, mode 2), and a
    # fourth jungle chest stood there that the file does not place (scenery: no mark).
    snapshot = replay('lower_kurast_two_camps')
    seen = json.loads((FIXTURES / 'lower_kurast_two_camps.json').read_text())['jungle_chests']

    marks = [units(p) for p in camps(handler_of(79).guide(snapshot))]

    assert sorted(marks) == sorted(chests_of(1064, 504) + chests_of(1112, 528))  # the order: task 4's
    near = [(x, y) for _, x, y, _ in seen if any(math.dist((x, y), mark) <= 1 for mark in marks)]
    assert sorted(near) == sorted(chests_of(1112, 528))
