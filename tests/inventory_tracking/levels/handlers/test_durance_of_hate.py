"""Durance of Hate 2: stairs down (evidence 2026-09-30, user: direction correct).

Durance of Hate 3: the mark is where the level's layout file places Mephisto (user, 2026-10-11).
No dump of the level yet: the rooms here are made up around the level's place in levels.txt
(tile 3500, 1600; 41 x 29 tiles, one preset)."""

import math

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def test_stairs_down_and_the_waypoint_the_player_stands_in():
    handler = handler_for(101)

    guidance = handler.guide(replay('durance_of_hate_2'))  # arrived by waypoint

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 3 - Mephisto Next E'),
        ('Waypoint', 'Act 3 - Mephisto Waypoint N'),
    ]
    assert guidance.problems == ()
    assert handler.confirmed


def test_the_first_mark_on_level_3_is_mephisto():
    complex_ = 796  # level_presets.json: Mephisto Complex
    bounds = (3500, 1600, 41, 29)
    rooms = tuple(Room(complex_, 3500 + 8 * i, 1600 + 8 * j, 8, 8, 0, bounds) for i in range(5) for j in range(3))
    handler = handler_for(102)
    guidance = guide_level(handler, LevelSnapshot(Location(102, 0, 17690, 8070), rooms))  # by the stairs
    poi = guidance.pois[0]
    assert (poi.label, poi.kind) == ('Mephisto', 'target')
    assert math.dist(poi.point, (3500 * 5 + 40, 1600 * 5 + 65)) <= 5
    assert guidance.problems == ()
    assert not handler.confirmed
