"""Worldstone Keep 1-3 (Baal). Fixtures: Win+C dumps 20260930T112800Z-757ba08b (WSK 2, standing
in the waypoint) and 20260930T112937Z-9cbcd0c0 (WSK 3, standing in the stairs up). Exits are
16x16 presets split into four 8x8 Room2 chunks each.
"""

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.level_map import build_map
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def found(fixture):
    snapshot = replay(fixture)
    guidance = handler_for(snapshot.location.area_id).guide(snapshot)
    here = [pointer(p, snapshot.location).here for p in guidance.pois]
    return snapshot, guidance, here


def test_wsk_2_tracks_stairs_down_waypoint_and_the_way_back():
    snapshot, guidance, here = found('worldstone_keep_2')

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 5 - Baal Next S'),
        ('Waypoint', 'Act 5 - Baal Waypoint W'),
        ('Worldstone Keep 1', 'Act 5 - Baal Prev NSW'),
    ]
    assert here == [False, True, False]
    assert guidance.problems == ()
    assert len(build_map(snapshot, guidance.pois).route) >= 2


def test_wsk_3_standing_in_the_stairs_up_is_here_not_a_problem():
    snapshot, guidance, here = found('worldstone_keep_3')

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 5 - Baal Next N'),
        ('Worldstone Keep 2', 'Act 5 - Baal Prev NEW'),
    ]
    assert here == [False, True]
    assert guidance.problems == ()
    assert len(build_map(snapshot, guidance.pois).route) >= 2


def test_labels_along_the_chain():
    assert [s.label for s in handler_for(128).pois] == ['Next level', 'Arreat Summit']
    assert [s.label for s in handler_for(129).pois] == ['Next level', 'Waypoint', 'Worldstone Keep 1']
    assert [s.label for s in handler_for(130).pois] == ['Next level', 'Worldstone Keep 2']
    assert [s.label for s in handler_for(131).pois] == ['Throne']
    assert not handler_for(131).confirmed
    assert all(handler_for(area).confirmed for area in (128, 129, 130))  # user checked 2026-09-30


def test_the_throne_of_destruction_marks_the_hall_before_the_throne():
    # user, 2026-10-10 night: teleport steps rush to Baal's hall. levels.txt puts the level at tile
    # (3000, 1000), 40 x 52 tiles; the layout file seats Baal at (90, 11) units, the hall below him.
    import math

    from inventory_tracking.levels.model import LevelSnapshot, Location, Room

    block = (3000, 1000, 40, 52)
    rooms = tuple(Room(1086, 3000 + 8 * i, 1000 + 8 * j, 8, 8, 0, block) for i in range(5) for j in range(6))
    guidance = handler_for(131).guide(LevelSnapshot(Location(131, 0, 15102, 5242), rooms))
    [poi] = guidance.pois
    assert (poi.label, poi.kind) == ('Throne', 'target')
    assert math.dist(poi.point, (15094, 5040)) <= 5
    assert guidance.problems == ()
