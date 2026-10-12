"""Levels that are one fixed preset, and chest rooms: the mark sits on the object the layout places.

No dump of these levels yet: the rooms are made up as chunks of the level's one preset. The spots
are the installed game's (levels/routes.md, 2026-10-12)."""

import pytest

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import PRESET_NAMES
from inventory_tracking.levels.registry import handler_for


def named(name: str) -> int:
    [found] = [preset for preset, known in PRESET_NAMES.items() if known == name]
    return found


def near(point):
    return round(point[0]), round(point[1])


def whole_level(area, preset, variant, size, origin=(1000, 2000)):
    """The level as 8x8 chunks of one preset, the player just inside its corner."""
    block = (*origin, size, size)
    rooms = tuple(
        Room(named(preset), origin[0] + 8 * i, origin[1] + 8 * j, 8, 8, variant, block)
        for i in range(size // 8)
        for j in range(size // 8)
    )
    return LevelSnapshot(Location(area, 0, origin[0] * 5 + 10, origin[1] * 5 + 10), rooms)


@pytest.mark.parametrize(
    ('area', 'preset', 'variant', 'size', 'label', 'spot'),
    [
        (13, 'Act 1 - Cave Treasure 2', 0, 24, 'Super chest', (112, 22)),  # Cave 2
        (14, 'Act 1 - Cave Treasure 3', 0, 24, 'Super chest', (23, 38)),  # Underground Passage 2
        (15, 'Act 1 - Cave Treasure 4', 0, 24, 'Super chest', (32, 103)),  # Hole 2
        (16, 'Act 1 - Cave Treasure 5', 0, 24, 'Super chest', (110, 59)),  # Pit 2
        (90, 'Act 3 - Dungeon Treasure 1', 5, 40, 'Super chest', (50, 106)),  # Swampy Pit 3
        (91, 'Act 3 - Dungeon Treasure 2', 3, 40, "Khalim's Brain", (184, 179)),  # Flayer Dungeon 3
        (93, 'Act 3 - Sewer Treasure X', 0, 24, "Khalim's Heart", (42, 12)),  # Kurast Sewers 2
        (114, 'Act 5 - Ice River A', 2, 64, 'Anya', (46, 66)),  # Frozen River
        (114, 'Act 5 - Ice River B', 0, 64, 'Anya', (51, 266)),
        (116, 'Act 5 - Ice Pool A', 0, 32, 'Super chest', (143, 119)),  # Drifter Cavern
        (116, 'Act 5 - Ice Pool B', 1, 32, 'Super chest', (133, 7)),
        (119, 'Act 5 - Ice Pool B', 4, 32, 'Super chest', (21, 21)),  # Icy Cellar
    ],
)
def test_a_one_preset_level_marks_its_object_first(area, preset, variant, size, label, spot):
    handler = handler_for(area)

    guidance = guide_level(handler, whole_level(area, preset, variant, size))

    poi = guidance.pois[0]
    assert (poi.label, poi.kind) == (label, 'target')
    assert poi.use == (397 if label == 'Super chest' else 0)  # the super chest is clicked by the step
    assert near(poi.point) == (1000 * 5 + spot[0], 2000 * 5 + spot[1])
    assert guidance.problems == ()
    assert not handler.confirmed


@pytest.mark.parametrize('area', [125, 126, 127])  # Abaddon, Pit of Acheron, Infernal Pit
def test_a_hell_pit_marks_every_dead_end_that_holds_a_chest(area):
    rooms = (
        Room(named('Act 5 - Lava NS'), 0, 0, 24, 24, 0),
        Room(named('Act 5 - Lava S'), 0, 24, 24, 24, 1),  # (54, 54)
        Room(named('Act 5 - Lava N'), 24, 0, 24, 24, 0),  # the plain layout: no chest
        Room(named('Act 5 - Lava E'), 48, 0, 24, 24, 1),  # (65, 100)
    )

    guidance = guide_level(handler_for(area), LevelSnapshot(Location(area, 0, 60, 60), rooms))

    assert [(p.label, near(p.point)) for p in guidance.pois] == [
        ('Super chest', (54, 24 * 5 + 54)),
        ('Super chest', (48 * 5 + 65, 100)),
    ]
    assert guidance.problems == ()


@pytest.mark.parametrize(
    ('area', 'label', 'preset', 'variant', 'spot'),
    [
        (19, 'Chest', 'Act 1 - Crypt Chest W', 0, (21, 11)),  # Mausoleum
        (65, 'Chest', 'Act 2 - Sewer Chest E', 0, (21, 35)),  # Ancient Tunnels
        (84, 'Chest', 'Act 3 - Spider Chest NE', 1, (5, 64)),  # Arachnid Lair
        (85, "Khalim's Eye", 'Act 3 - Spider Chest NW', 2, (45, 63)),  # Spider Cavern
        (92, 'Chest', 'Act 3 - Sewer Chest S', 0, (33, 18)),  # Kurast Sewers 1
    ],
)
def test_a_chest_room_mark_sits_on_the_chest(area, label, preset, variant, spot):
    size = 16 if 'Spider' in preset else 12 if 'Sewer' in preset else 8
    rooms = (Room(named(preset), 300, 400, size, size, variant), Room(0, 0, 0, 8, 8))

    guidance = handler_for(area).guide(LevelSnapshot(Location(area, 0, 20, 20), rooms))

    [poi] = [p for p in guidance.pois if p.label == label]
    assert near(poi.point) == (300 * 5 + spot[0], 400 * 5 + spot[1])
