"""Tamoe Highland → Pit 1 → Pit 2 (D2MOO DrlgOutWild/DrlgMaze, d2data levels; no evidence yet).

Tamoe's cave mouth is either 'Cave Entrance' or a cliff cave ('Wild Cliff Cave Left/Right'); only
one is placed. Pit 1's stairs down are 'Cave Down' (not 'Next'). Pit 2 is one fixed preset
('Cave Treasure 5', DrlgType 2) covering the level, so it has no handler.
"""

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_tamoe_highland_points_at_the_pit_whichever_entrance_was_placed():
    for entrance in (51, 24, 25):
        rooms = (Room(0, 0, 0, 8, 8), Room(16, 8, 0, 8, 8), Room(entrance, 40, 16, 8, 8))
        guidance = handler_for(7).guide(LevelSnapshot(Location(7, 0, 20, 20), rooms))

        assert [(p.label, p.room.preset) for p in guidance.pois] == [('Pit', entrance)]
        assert guidance.problems == ()


def test_pit_1_tracks_the_stairs_down_and_the_way_back():
    rooms = (Room(85, 0, 0, 24, 24), Room(55, 24, 0, 24, 24), Room(92, 48, 0, 24, 24))
    guidance = handler_for(12).guide(LevelSnapshot(Location(12, 0, 60, 60), rooms))

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 1 - Cave Down E'),
        ('Tamoe Highland', 'Act 1 - Cave Prev S'),
    ]
    assert guidance.problems == ()


def test_pit_level_2_has_no_handler_and_the_route_is_confirmed():
    assert handler_for(16) is None
    assert all(handler_for(area).confirmed for area in (7, 12))  # user, in game, 2026-09-30


def test_tamoe_highland_names_its_gap_and_the_monastery_gate_by_the_rooms_touching_it():
    rooms = (
        Room(0, 0, 0, 8, 8, None, None, (26,)),  # plain terrain touching the Monastery Gate: no open gap there
        Room(5, 0, 80, 8, 8, 3),  # the only gap: Black Marsh by elimination
        Room(51, 40, 16, 8, 8),
    )
    snapshot = LevelSnapshot(Location(7, 0, 20, 20), rooms)
    guidance = guide_level(handler_for(7), snapshot)

    assert [(p.label, p.kind) for p in guidance.pois] == [
        ('Black Marsh', 'previous'),
        ('Pit', 'stairs'),
        ('Monastery Gate', 'stairs'),
    ]
    assert guidance.problems == ()
