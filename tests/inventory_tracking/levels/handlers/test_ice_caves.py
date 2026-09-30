"""Arreat Plateau → Crystalline Passage → Glacial Trail → Frozen Tundra (d2data levels; no evidence yet).

Both levels are 'Act 5 - Ice' mazes. The levels table has Vis0 as the way back, Vis1 (Warp 74)
as the level ahead ('Ice Next') and Vis2 (Warp 75) as the side cave ('Ice Down'). The side
caves are Frozen River (114, Anya) and Drifter Cavern (116). Both levels have a waypoint.
"""

import pytest

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


ROOMS = (
    Room(1017, 0, 0, 16, 16),  # Ice NSEW
    Room(1025, 16, 0, 16, 16),  # Ice Next N
    Room(1028, 32, 0, 16, 16),  # Ice Down S
    Room(1036, 48, 0, 16, 16),  # Ice waypoint E
    Room(1018, 64, 0, 16, 16),  # Ice Prev W
)


@pytest.mark.parametrize(
    ('area', 'expected'),
    [
        (
            113,
            [
                ('Glacial Trail', 'stairs', 'Act 5 - Ice Next N'),
                ('Frozen River', 'target', 'Act 5 - Ice Down S'),
                ('Waypoint', 'waypoint', 'Act 5 - Ice waypoint E'),
                ('Arreat Plateau', 'previous', 'Act 5 - Ice Prev W'),
            ],
        ),
        (
            115,
            [
                ('Frozen Tundra', 'stairs', 'Act 5 - Ice Next N'),
                ('Drifter Cavern', 'stairs', 'Act 5 - Ice Down S'),
                ('Waypoint', 'waypoint', 'Act 5 - Ice waypoint E'),
                ('Crystalline Passage', 'previous', 'Act 5 - Ice Prev W'),
            ],
        ),
    ],
)
def test_ice_cave_tracks_next_level_side_cave_waypoint_and_way_back(area, expected):
    guidance = handler_for(area).guide(LevelSnapshot(Location(area, 0, 20, 20), ROOMS))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == expected
    assert guidance.problems == ()


@pytest.mark.parametrize('area', [113, 115])
def test_missing_exits_are_problems_but_a_missing_waypoint_is_not(area):
    guidance = handler_for(area).guide(LevelSnapshot(Location(area, 0, 20, 20), (Room(1017, 0, 0, 16, 16),)))

    assert len(guidance.problems) == 3
    assert not handler_for(area).confirmed  # no in-game evidence yet
