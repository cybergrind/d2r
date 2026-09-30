"""Cathedral → Catacombs 1-3 → Andariel (Catacombs 4). Confirmed in game 2026-09-30; fixtures
catacombs_2 / catacombs_3 come from automatic evidence (the player stood in the waypoint / stairs up).

Catacombs 4 is one fixed preset ('Act 1 - Andariel') covering the level, so it has no handler.
"""

import pytest

from inventory_tracking.levels.handler import instances
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.registry import handler_for


def test_each_level_tracks_next_level_and_the_way_back():
    assert [s.label for s in handler_for(34).pois] == ['Next level', 'Cathedral']
    assert [s.label for s in handler_for(35).pois] == ['Next level', 'Waypoint', 'Catacombs 1']
    assert [s.label for s in handler_for(36).pois] == ['Next level', 'Catacombs 2']
    assert handler_for(37) is None


def test_catacombs_2_finds_all_three_in_a_level():
    # Next S, Waypoint E, Prev EW (stairs up) placed in a small synthetic maze.
    rooms = (Room(293, 0, 0, 8, 8), Room(297, 8, 0, 8, 8), Room(288, 16, 0, 8, 8), Room(282, 24, 0, 8, 8))
    snapshot = LevelSnapshot(Location(35, 0, 30 * 5, 4 * 5), rooms)

    guidance = handler_for(35).guide(snapshot)

    assert [(p.label, p.room.preset) for p in guidance.pois] == [
        ('Next level', 293),
        ('Waypoint', 297),
        ('Catacombs 1', 288),
    ]
    assert guidance.problems == ()
    assert len(instances(rooms)) == 4


@pytest.mark.parametrize(
    ('fixture', 'expected'),
    [
        (
            'catacombs_2',
            [
                ('Next level', 'Act 1 - Catacombs Next E', False),
                ('Waypoint', 'Act 1 - Catacombs Waypoint S', True),
                ('Catacombs 1', 'Act 1 - Catacombs Prev NS', False),
            ],
        ),
        (
            'catacombs_3',
            [('Next level', 'Act 1 - Catacombs Next S', False), ('Catacombs 2', 'Act 1 - Catacombs Prev EW', True)],
        ),
    ],
)
def test_real_catacombs_levels_replay_and_are_confirmed(fixture, expected):
    from inventory_tracking.levels.geometry import pointer
    from inventory_tracking.levels.presets import preset_name
    from tests.inventory_tracking.levels.fixtures import replay

    snapshot = replay(fixture)
    handler = handler_for(snapshot.location.area_id)
    guidance = handler.guide(snapshot)

    found = [(p.label, preset_name(p.room.preset), pointer(p, snapshot.location).here) for p in guidance.pois]
    assert found == expected
    assert guidance.problems == ()
    assert all(handler_for(area).confirmed for area in (34, 35, 36))
