"""Chaos Sanctuary: the mark is Diablo's star, where the Heart's layout file places `DiabloStart`
(user, 2026-10-10 night). No dump of the level yet: the rooms here are made up around the
level's place in levels.txt (tile 1500, 1000; 120 x 120 tiles, five presets of 24 x 24)."""

import math

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.registry import handler_for


def chunks(preset, x, y):
    return tuple(Room(preset, x + 8 * i, y + 8 * j, 8, 8, 0, (x, y, 24, 24)) for i in range(3) for j in range(3))


def test_the_first_mark_is_diablos_star_in_the_heart():
    heart, entry, arm = 862, 857, 858  # level_presets.json: Diablo Heart, Entry, Arm W
    rooms = (*chunks(entry, 1548, 1096), *chunks(heart, 1548, 1048), *chunks(arm, 1524, 1048))
    handler = handler_for(108)
    guidance = handler.guide(LevelSnapshot(Location(108, 0, 7800, 5600), rooms))
    [poi] = guidance.pois
    assert (poi.label, poi.kind) == ('Diablo', 'target')
    assert math.dist(poi.point, (1548 * 5 + 53, 1048 * 5 + 53)) <= 5
    assert guidance.problems == ()
    assert not handler.confirmed
