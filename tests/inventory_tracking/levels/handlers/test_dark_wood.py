"""Dark Wood (area 5): the Underground Passage cave and the border gap to Black Marsh (d2data levels:
its only warp is the Underground Passage; D2MOO DrlgOutPlace links it by border only to Black Marsh).
Evidence 20260930T120851 (fixture dark_wood): the cave is 'Wild Cliff Cave Left' at 2904,1114.
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_dark_wood_marks_the_underground_passage_and_black_marsh():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(6, 0, 8, 8, 8, 3, (0, 8, 8, 8)),  # the open border gap; its far side not read yet
        Room(51, 40, 0, 8, 8, 1, (40, 0, 8, 8)),  # Cave Entrance
    )
    guidance = handler_for(5).guide(LevelSnapshot(Location(5, 0, 60, 60), rooms))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Black Marsh', 'stairs', 'Act 1 - Wild Border 3'),  # the only gap: named by elimination
        ('Underground Passage', 'stairs', 'Act 1 - Cave Entrance'),
    ]
    assert guidance.problems == ()


def test_real_dark_wood_replays():
    from tests.inventory_tracking.levels.fixtures import replay

    guidance = handler_for(5).guide(replay('dark_wood'))

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Black Marsh', 'Act 1 - Wild Border 3'),
        ('Underground Passage', 'Act 1 - Wild Cliff Cave Left'),
    ]
    assert guidance.problems == ()
