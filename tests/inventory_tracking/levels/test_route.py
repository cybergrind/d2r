"""Teleport route over a level's rooms: straight where the line stays over rooms, around wide void.

The user teleports (2026-10-09): doorways don't matter, only void wider than a teleport does. On the
maze fixtures the old doorway walk was 1.3-1.7 times the straight line; three of the seven straight
lines cross no void at all.
"""

import math
from itertools import pairwise

import pytest

from inventory_tracking.levels.handlers.tower_cellar import HANDLERS
from inventory_tracking.levels.level_map import centre
from inventory_tracking.levels.model import Room
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.route import REACH, gap, passable, room_at, route
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import replay


def player_tile(snapshot):
    return snapshot.location.x / TILE_UNITS, snapshot.location.y / TILE_UNITS


def first_poi_point(snapshot):
    handler = handler_for(snapshot.location.area_id)
    assert handler is not None
    [poi, *_] = handler.guide(snapshot).pois
    return poi.spot or centre(poi.room)


def length(points):
    return sum(math.dist(a, b) for a, b in pairwise(points))


@pytest.mark.parametrize('fixture', ['tower_cellar_2', 'tower_cellar_3', 'worldstone_keep_3', 'jail_1'])
def test_a_target_in_sight_over_rooms_is_one_straight_hop_whatever_the_doorways(fixture):
    snapshot = replay(fixture)
    tile, goal = player_tile(snapshot), first_poi_point(snapshot)

    assert route(snapshot.rooms, tile, goal) == [tile, goal]


@pytest.mark.parametrize('fixture', ['tower_cellar_4', 'worldstone_keep_2'])
def test_void_wider_than_a_teleport_is_rounded_with_every_hop_landing_on_a_room(fixture):
    snapshot = replay(fixture)
    tile, goal = player_tile(snapshot), first_poi_point(snapshot)
    assert not passable(snapshot.rooms, tile, goal)  # the straight line crosses void too wide

    hops = route(snapshot.rooms, tile, goal)

    assert hops is not None
    assert hops[0] == tile
    assert hops[-1] == goal
    assert len(hops) >= 3
    assert all(room_at(snapshot.rooms, point) is not None for point in hops)
    assert all(passable(snapshot.rooms, a, b) for a, b in pairwise(hops))
    assert length(hops) < 1.5 * math.dist(tile, goal)


def test_tower_cellar_1_crosses_a_void_narrower_than_a_teleport_straight():
    snapshot = replay('tower_cellar_1')
    tile, goal = player_tile(snapshot), first_poi_point(snapshot)
    [poi] = HANDLERS[0].guide(snapshot).pois
    assert poi.label == 'Next level'

    assert route(snapshot.rooms, tile, goal) == [tile, goal]
    assert not passable(snapshot.rooms, tile, goal, reach=3.0)


def test_no_route_from_or_to_a_tile_off_the_rooms():
    tower = replay('tower_cellar_1')
    room = tower.rooms[3]

    assert route(tower.rooms, (0.0, 0.0), centre(room)) is None
    assert route(tower.rooms, centre(room), (0.0, 0.0)) is None


def test_a_bridge_room_is_the_way_over_a_wide_gap_and_without_it_there_is_none():
    here, there = Room(1, 0, 0, 8, 8), Room(2, 20, 0, 8, 8)  # 12 tiles of void between them
    bridge = Room(3, 10, 10, 8, 8)  # 2 tiles from each, diagonally

    assert gap(here, there) == 12
    assert gap(here, bridge) == gap(bridge, there) == math.hypot(2, 2)
    assert route((here, there), (4.0, 4.0), (24.0, 4.0)) is None
    hops = route((here, there, bridge), (4.0, 4.0), (24.0, 4.0))
    assert hops is not None
    assert hops[0] == (4.0, 4.0)
    assert hops[-1] == (24.0, 4.0)
    assert room_at((bridge,), hops[1]) is not None


def test_chunks_of_one_preset_count_as_one_landing_area():
    chunks = tuple(Room(9, x, y, 8, 8, 0, (0, 0, 16, 16)) for x in (0, 8) for y in (0, 8))
    far = Room(1, 16 + math.ceil(REACH) + 1, 0, 8, 8)  # over a gap one teleport cannot cross

    assert route(chunks, (1.0, 1.0), (15.0, 15.0)) == [(1.0, 1.0), (15.0, 15.0)]
    assert route((*chunks, far), (1.0, 1.0), centre(far)) is None
