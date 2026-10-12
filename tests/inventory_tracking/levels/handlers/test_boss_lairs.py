"""The marks of the levels whose boss or portal the game's files place (levels/routes.md, Phase 6).

No dump of these levels yet: the rooms are made up as chunks of the level's preset.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import ARCANE_PORTAL, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import PRESET_NAMES
from inventory_tracking.levels.registry import handler_for


ORIGIN = (1000, 2000)


def named(name: str) -> int:
    [found] = [preset for preset, known in PRESET_NAMES.items() if known == name]
    return found


def lair(area, preset, variant, size=80):
    block = (*ORIGIN, size, size)
    rooms = tuple(
        Room(named(preset), ORIGIN[0] + 8 * i, ORIGIN[1] + 8 * j, 8, 8, variant, block)
        for i in range(size // 8)
        for j in range(size // 8)
    )
    return LevelSnapshot(Location(area, 0, ORIGIN[0] * 5 + 10, ORIGIN[1] * 5 + 10), rooms)


@pytest.mark.parametrize(
    ('area', 'preset', 'variant', 'label', 'spot'),
    [
        (37, 'Act 1 - Andariel', 0, 'Andariel', (46, 46)),  # Andy3.ds1
        (61, 'Act 2 - Tomb Tainted Sun X', 0, 'Fangskin', (71, 71)),
        (94, 'Act 3 - Temple 1', 0, 'Battlemaid Sarina', (50, 55)),
        (94, 'Act 3 - Temple 1', 2, 'Battlemaid Sarina', (80, 90)),
        (132, 'Act 5 - WorldStone', 0, 'Baal', (135, 160)),  # wstone01.ds1
    ],
)
def test_a_boss_lair_marks_where_the_file_places_its_boss(area, preset, variant, label, spot):
    guidance = guide_level(handler_for(area), lair(area, preset, variant, 200 if area == 132 else 104))

    poi = guidance.pois[0]
    assert (poi.label, poi.kind) == (label, 'target')
    assert math.dist(poi.point, (ORIGIN[0] * 5 + spot[0], ORIGIN[1] * 5 + spot[1])) <= 3  # its tile
    assert guidance.problems == ()


def test_travincal_marks_the_council_after_the_durance():
    north = lair(83, 'Act 3 - Travincal N', 0, 160)
    outside = replace(north.location, x=ORIGIN[0] * 5 - 400)  # in the level's south-west block, not in this one
    guidance = guide_level(handler_for(83), replace(north, location=outside))

    assert [poi.label for poi in guidance.pois[:2]] == ['Durance of Hate', 'Council']
    council = guidance.pois[1]
    assert math.dist(council.point, (ORIGIN[0] * 5 + 58, ORIGIN[1] * 5 + 98)) <= 3


def test_palace_cellar_3_marks_the_portal_in_the_layout_that_holds_it():
    portal_room = Room(named('Act 2 - Basement SE'), 1000, 2000, 24, 24, 3)
    other = Room(named('Act 2 - Basement SE'), 1024, 2000, 24, 24, 0)
    guidance = guide_level(handler_for(54), LevelSnapshot(Location(54, 0, 5010, 10010), (portal_room, other)))

    [portal] = [poi for poi in guidance.pois if poi.label == 'Arcane Sanctuary']
    assert (portal.kind, portal.use) == ('stairs', ARCANE_PORTAL)
    assert (round(portal.point[0]), round(portal.point[1])) == (5000 + 73, 10000 + 73)
    assert guidance.problems == ()
