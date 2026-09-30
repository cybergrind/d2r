"""Outer Steppes: the gap to the Plains of Despair and the way back to the Pandemonium Fortress.

From D2MOO DrlgOutdoors/DrlgOutPlace and d2data lvlprest (2026-10-01; no evidence yet): the
Fortress side is one 'Act 4 - Fortress Transition' preset (8x24); the level links are
'Mesa Border 1-4' rooms in their open DS1 file (Border*o.ds1 = file 3), as in Act 1.
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def rows(guidance):
    return [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois]


def test_the_one_open_gap_is_the_plains_by_elimination_and_the_fortress_is_the_way_back():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(799, 0, 8, 8, 8, variant=0),  # closed border
        Room(800, 40, 0, 8, 8, variant=3),  # open gap
        Room(798, 0, 16, 8, 24),
    )
    guidance = handler_for(104).guide(LevelSnapshot(Location(104, 0, 60, 60), rooms))

    assert rows(guidance) == [
        ('Plains of Despair', 'stairs', 'Act 4 - Mesa Border 2'),
        ('Pandemonium Fortress', 'previous', 'Act 4 - Fortress Transition'),
    ]
    assert guidance.problems == ()


def test_a_gap_known_to_lead_to_the_plains_is_named_and_extra_gaps_are_plain_exits():
    rooms = (
        Room(801, 16, 0, 8, 8, variant=3),
        Room(802, 40, 0, 8, 8, variant=3, leads_to=(105,)),
        Room(798, 0, 16, 8, 24),
    )
    guidance = handler_for(104).guide(LevelSnapshot(Location(104, 0, 60, 60), rooms))

    assert rows(guidance) == [
        ('Plains of Despair', 'stairs', 'Act 4 - Mesa Border 4'),
        ('Exit', 'exit', 'Act 4 - Mesa Border 3'),
        ('Pandemonium Fortress', 'previous', 'Act 4 - Fortress Transition'),
    ]
    assert not handler_for(104).confirmed
