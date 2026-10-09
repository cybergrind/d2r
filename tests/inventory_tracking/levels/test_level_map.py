"""Map card built from real Arcane fixtures: every room, the player dot, the POI dot."""

import math

import pytest

from inventory_tracking.levels.geometry import ARROWS, pointer
from inventory_tracking.levels.level_map import build_map
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.osd.level_map import project
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize('fixture', ['arcane_summoner_s', 'arcane_summoner_w'])
def test_map_has_every_room_the_player_and_the_poi(fixture):
    snapshot = replay(fixture)
    guidance = handler_for(74).guide(snapshot)

    card = build_map(snapshot, guidance.pois)

    assert len(card.rooms) == 61
    px, py = card.player
    centre = next(r for r in snapshot.rooms if r.preset == 524)  # the NSEW junction
    assert centre.x <= px <= centre.x + centre.width
    assert centre.y <= py <= centre.y + centre.height
    [poi] = card.pois
    room = guidance.pois[0].room
    assert (poi.label, poi.kind) == ('Summoner', 'target')
    assert (poi.x, poi.y) == (room.x + room.width / 2, room.y + room.height / 2)


@pytest.mark.parametrize('fixture', ['arcane_summoner_s', 'arcane_summoner_w'])
def test_map_dot_and_arrow_agree_on_direction(fixture):
    snapshot = replay(fixture)
    [found] = handler_for(74).guide(snapshot).pois
    card = build_map(snapshot, (found,))

    (sx0, sy0), (sx1, sy1) = project(*card.player), project(card.pois[0].x, card.pois[0].y)
    octant = round(math.degrees(math.atan2(-(sy1 - sy0), sx1 - sx0)) / 45) % 8

    assert ARROWS[octant] == pointer(found, snapshot.location).arrow


def test_maze_map_carries_the_route_from_player_to_stairs():
    snapshot = replay('tower_cellar_1')
    guidance = handler_for(21).guide(snapshot)

    card = build_map(snapshot, guidance.pois)

    assert len(card.route) >= 2
    assert card.route[0] == card.player
    assert card.route[-1] == (card.pois[0].x, card.pois[0].y)


def test_temple_map_routes_too_now_that_teleport_ignores_doorways():
    snapshot = replay('halls_of_pain_live')

    card = build_map(snapshot, handler_for(123).guide(snapshot).pois)

    assert len(card.route) >= 2
    assert card.route[0] == card.player
    assert card.route[-1] == (card.pois[0].x, card.pois[0].y)


def test_outdoor_edge_presets_are_marked_as_edges():
    from collections import Counter

    from inventory_tracking.levels.presets import preset_name

    snapshot = replay('black_marsh')

    card = build_map(snapshot, handler_for(6).guide(snapshot).pois)

    borders = sum('Border' in preset_name(r.preset) for r in snapshot.rooms)
    assert Counter(card.room_kinds) == {'edge': borders, 'room': len(snapshot.rooms) - borders}
    assert borders == 48


def test_maze_levels_have_no_edges():
    snapshot = replay('tower_cellar_1')

    card = build_map(snapshot, handler_for(21).guide(snapshot).pois)

    assert set(card.room_kinds) == {'room'}


def test_the_map_carries_the_walkable_tiles_it_is_given():
    from inventory_tracking.levels.level_map import build_map
    from inventory_tracking.levels.model import LevelSnapshot, Location, Room, Walkable

    snapshot = LevelSnapshot(Location(9, 0, 20, 20), (Room(0, 0, 0, 8, 8),))

    card = build_map(snapshot, (), walkable=[Walkable(0, 0, 2, 1, '10')])

    assert card.walkable == ((0, 0, 2, 1, '10'),)


def test_visited_rooms_follow_the_room_order():
    from inventory_tracking.levels.level_map import build_map
    from inventory_tracking.levels.model import LevelSnapshot, Location, Room

    snapshot = LevelSnapshot(Location(6, 0, 20, 20), (Room(0, 0, 0, 8, 8), Room(0, 8, 0, 8, 8)))

    card = build_map(snapshot, (), visited={(8, 0, 8, 8)})

    assert card.visited == (0, 1)
    assert build_map(snapshot, ()).visited == ()


def test_extra_dots_are_added_after_the_handler_pois():
    from inventory_tracking.levels.level_map import build_map
    from inventory_tracking.levels.model import LevelSnapshot, Location, Room
    from inventory_tracking.osd.level_map import MapPoi

    snapshot = LevelSnapshot(Location(6, 0, 20, 20), (Room(0, 0, 0, 8, 8),))
    dot = MapPoi('Herald T1', 'herald', 3.0, 4.0)

    assert build_map(snapshot, (), dots=[dot]).pois == (dot,)
