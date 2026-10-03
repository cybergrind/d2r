"""City of the Damned: the stairs down to the River of Flame and the gap back to the Plains.

From D2MOO DrlgOutdoors (2026-10-01; no evidence yet): 'Act 4 - Mesa Warp' is spawned only in
this level (levels.json Vis1 = 107, River of Flame); the Plains link is an open 'Mesa Border 1-4'.
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_city_marks_the_river_of_flame_stairs_and_the_plains_gap():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(802, 0, 8, 8, 8, variant=3),  # the only gap: the Plains by elimination
        Room(803, 16, 0, 8, 8, variant=1),
        Room(811, 40, 40, 8, 8),
    )
    guidance = handler_for(106).guide(LevelSnapshot(Location(106, 0, 60, 60), rooms))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Plains of Despair', 'previous', 'Act 4 - Mesa Border 4'),
        ('River of Flame', 'stairs', 'Act 4 - Mesa Warp'),
    ]
    assert guidance.problems == ()
    assert not handler_for(106).confirmed
