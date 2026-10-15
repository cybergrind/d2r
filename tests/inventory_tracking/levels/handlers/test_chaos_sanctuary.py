"""Chaos Sanctuary: the mark is Diablo's star, where the Heart's layout file places `DiabloStart`
(user, 2026-10-10 night). No dump of the level yet: the rooms here are made up around the
level's place in levels.txt (tile 1500, 1000; 120 x 120 tiles, five presets of 24 x 24)."""

import math
from dataclasses import replace

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from tests.inventory_tracking.levels.fixtures import handler_of


def chunks(preset, x, y):
    return tuple(Room(preset, x + 8 * i, y + 8 * j, 8, 8, 0, (x, y, 24, 24)) for i in range(3) for j in range(3))


def sanctuary(east=0):
    heart, entry, west, east_arm, north = (
        862,
        857,
        858,
        859,
        861,
    )  # level_presets.json: Diablo Heart, Entry, Arm W, E, N
    return (
        *chunks(entry, 1548, 1096),
        *chunks(heart, 1548, 1048),
        *chunks(west, 1524, 1048),
        *(replace(room, variant=east) for room in chunks(east_arm, 1572, 1048)),
        *chunks(north, 1548, 1024),
    )


def test_the_seals_are_marked_after_the_star_where_each_arms_layout_places_them():
    guidance = handler_of(108).guide(LevelSnapshot(Location(108, 0, 7800, 5600), sanctuary(east=1)))

    assert [(p.label, round(p.point[0]), round(p.point[1])) for p in guidance.pois[1:]] == [
        ('Vizier seal 1', 1524 * 5 + 35, 1048 * 5 + 35),
        ('Vizier seal 2', 1524 * 5 + 35, 1048 * 5 + 75),
        ('De Seis seal', 1548 * 5 + 33, 1024 * 5 + 35),
        ('Infector seal 1', 1572 * 5 + 33, 1048 * 5 + 73),  # the arm's second layout
        ('Infector seal 2', 1572 * 5 + 55, 1048 * 5 + 35),
    ]
    assert [p.use for p in guidance.pois] == [0, 396, 395, 394, 392, 393]  # each seal is its own object to click
    assert guidance.problems == ()


def test_the_first_mark_is_diablos_star_in_the_heart():
    handler = handler_of(108)
    guidance = handler.guide(LevelSnapshot(Location(108, 0, 7800, 5600), sanctuary()))
    poi = guidance.pois[0]
    assert (poi.label, poi.kind) == ('Diablo', 'target')
    assert math.dist(poi.point, (1548 * 5 + 53, 1048 * 5 + 53)) <= 5
    assert guidance.problems == ()
    assert not handler.confirmed
