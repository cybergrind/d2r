"""Stony Field (area 4): the Tristram portal at the Cairn Stones, the Underground Passage cave and
the border gap back to Cold Plains (d2data levels: its only warp is the Underground Passage; D2MOO
DrlgOutPlace links it by border only to Cold Plains). No evidence yet.
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_stony_field_marks_the_cairn_stones_the_cave_and_the_way_back():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(5, 0, 8, 8, 8, 3, (0, 8, 8, 8)),  # the open border gap; its far side not read yet
        Room(160, 24, 8, 16, 16, 0, (24, 8, 16, 16)),  # Cairn Stones
        Room(25, 40, 0, 8, 8, 0, (40, 0, 8, 8)),  # Wild Cliff Cave Left
    )
    guidance = handler_for(4).guide(LevelSnapshot(Location(4, 0, 60, 60), rooms))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Cold Plains', 'previous', 'Act 1 - Wild Border 2'),  # the only gap: named by elimination
        ('Tristram', 'target', 'Act 1 - Cairn Stones'),
        ('Underground Passage', 'stairs', 'Act 1 - Wild Cliff Cave Left'),
    ]
    assert guidance.problems == ()
    assert not handler_for(4).confirmed
