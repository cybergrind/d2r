"""Lower Kurast super chests: the bonfire camp (user, 2026-09-30: LK super chests don't sparkle;
two shacks by a fire, chests inside).

Win+C dump 20260930T124726Z-e166c530 (fixture lower_kurast_camp), taken inside one shack: the camp
is 'Act 3 - Slums 16x16' DS1 variant 1 (fire at 5416,2211, jungle torches around it, a jungle chest
in each shack at 5420,2172 and 5428,2221). It was the only variant-1 instance among 80 rooms;
the other 16x16 blocks (variants 0 and 2) have no fire.
"""

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


SLUMS_16X16 = 618
EXITS = (Room(613, 64, 0, 8, 8), Room(631, 72, 0, 8, 8), Room(614, 64, 56, 8, 8))  # Gate N, Waypoint, Gate S


def camps(guidance):
    return [poi for poi in guidance.pois if poi.label == 'Super chests']


def camp(x, y, variant):
    """A 16x16 preset split into four 8x8 chunks, as the client holds it."""
    return tuple(Room(SLUMS_16X16, x + dx, y + dy, 8, 8, variant, (x, y, 16, 16)) for dx in (0, 8) for dy in (0, 8))


def test_the_real_camp_is_found_and_the_player_stands_in_it():
    snapshot = replay('lower_kurast_camp')
    handler = handler_for(79)

    guidance = handler.guide(snapshot)

    [poi] = camps(guidance)
    assert (poi.label, preset_name(poi.room.preset), poi.kind) == ('Super chests', 'Act 3 - Slums 16x16', 'target')
    assert (poi.room.x, poi.room.y, poi.room.width, poi.room.height) == (1072, 432, 16, 16)
    assert pointer(poi, snapshot.location).here
    assert guidance.problems == ()
    assert handler.confirmed


def test_every_camp_is_marked_and_other_variants_are_not():
    rooms = camp(0, 0, 1) + camp(16, 0, 0) + camp(32, 0, 2) + camp(48, 0, 1) + EXITS
    guidance = handler_for(79).guide(LevelSnapshot(Location(79, 0, 5, 5), rooms))

    assert [(p.label, p.room.x) for p in camps(guidance)] == [('Super chests', 0), ('Super chests', 48)]
    assert guidance.problems == ()


def test_a_level_without_a_camp_is_quiet():
    guidance = handler_for(79).guide(LevelSnapshot(Location(79, 0, 5, 5), camp(0, 0, 0) + EXITS))

    assert camps(guidance) == []
    assert guidance.problems == ()


def test_a_second_game_finds_its_camp_elsewhere():
    # Evidence 20260930T125427 from another game; the user confirmed the mark in game.
    snapshot = replay('lower_kurast_game2')

    guidance = handler_for(79).guide(snapshot)

    assert [(p.room.x, p.room.y, p.room.variant) for p in camps(guidance)] == [(1016, 560, 1)]
    assert guidance.problems == ()
