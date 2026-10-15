"""Stony Field (area 4): the Tristram portal at the Cairn Stones, the Underground Passage cave and
the border gap back to Cold Plains (d2data levels: its only warp is the Underground Passage; D2MOO
DrlgOutPlace links it by border only to Cold Plains). No evidence yet.
Tristram (area 38): Wirt's body where the level's one DS1 file places it.
"""

from inventory_tracking.levels.model import PORTAL, WIRTS_BODY, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from tests.inventory_tracking.levels.fixtures import handler_of


def test_stony_field_marks_the_cairn_stones_the_cave_and_the_way_back():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(5, 0, 8, 8, 8, 3, (0, 8, 8, 8)),  # the open border gap; its far side not read yet
        Room(160, 24, 8, 16, 16, 0, (24, 8, 16, 16)),  # Cairn Stones
        Room(25, 40, 0, 8, 8, 0, (40, 0, 8, 8)),  # Wild Cliff Cave Left
    )
    guidance = handler_of(4).guide(LevelSnapshot(Location(4, 0, 60, 60), rooms))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Tristram', 'target', 'Act 1 - Cairn Stones'),  # the first mark: the one the teleport step follows
        ('Underground Passage', 'stairs', 'Act 1 - Wild Cliff Cave Left'),
        ('Cold Plains', 'previous', 'Act 1 - Wild Border 2'),  # the only gap: named by elimination
    ]
    assert [p.use for p in guidance.pois] == [PORTAL, 0, 0]  # the stones hold a portal object, not a door
    assert guidance.problems == ()
    assert not handler_of(4).confirmed


def test_tristram_marks_wirts_body_from_inside_the_one_preset():
    block = (5000, 5000, 44, 44)
    rooms = tuple(Room(300, 5000 + x, 5000 + y, 8, 8, 0, block) for x in range(0, 40, 8) for y in range(0, 40, 8))
    guidance = handler_of(38).guide(LevelSnapshot(Location(38, 0, 25100, 25100), rooms))

    [poi] = guidance.pois
    assert (poi.label, poi.kind, poi.use) == ("Wirt's body", 'target', WIRTS_BODY)
    assert poi.point == (25050, 25180)  # the file's (48, 179) units from the origin, to the nearest tile
    assert guidance.problems == ()
    assert not handler_of(38).confirmed
