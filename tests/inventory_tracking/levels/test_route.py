"""Room route from doorway letters: checked against real maze fixtures (N = -y, E = +x).

On 2026-09-30 every doorway in the Tower Cellar 1-4, Durance 2 and Arcane fixtures (412 checks)
faced a neighbour with the opposite doorway under N = -y, E = +x; no other axis choice did.
"""

from itertools import pairwise

import pytest

from inventory_tracking.levels.handlers.tower_cellar import HANDLERS
from inventory_tracking.levels.model import Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.route import doorways, route
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import replay


STEP = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}


@pytest.mark.parametrize(
    ('room', 'expected'),
    [
        (Room(122, 0, 0, 8, 8), {'N', 'S', 'E'}),  # Act 1 - Crypt NSE
        (Room(143, 0, 0, 8, 8), {'W'}),  # Act 1 - Crypt Next W
        (Room(527, 0, 0, 12, 12), {'S'}),  # Act 2 - Arcane Summoner S
        (Room(159, 0, 0, 8, 8), None),  # Act 1 - Crypt Countess X: no doorway token
        (Room(1047, 0, 0, 8, 8, 0, (0, 0, 40, 40)), None),  # Temple NW Down chunk
        (Room(1042, 0, 0, 8, 8, 1, (0, 0, 40, 40)), None),  # 'Temple NE' names a quadrant, not doors
    ],
)
def test_doorways_come_from_the_trailing_letters_of_single_room_presets(room, expected):
    assert doorways(room) == expected


@pytest.mark.parametrize('fixture', ['tower_cellar_1', 'tower_cellar_2', 'tower_cellar_3', 'tower_cellar_4'])
def test_route_walks_matching_doorways_from_the_player_to_the_stairs(fixture):
    snapshot = replay(fixture)
    [poi] = HANDLERS[0].guide(snapshot).pois
    tile = (snapshot.location.x / TILE_UNITS, snapshot.location.y / TILE_UNITS)

    path = route(snapshot.rooms, tile, poi.room)

    assert path[0].x <= tile[0] < path[0].x + path[0].width
    assert path[0].y <= tile[1] < path[0].y + path[0].height
    assert path[-1] == poi.room
    for here, there in pairwise(path):
        [letter] = [
            d
            for d, (dx, dy) in STEP.items()
            if (here.x + dx * here.width, here.y + dy * here.height) == (there.x, there.y)
        ]
        assert letter in doorways(here)
        assert OPPOSITE[letter] in doorways(there)
    assert preset_name(path[-1].preset).startswith('Act 1 - Crypt Next')


def test_no_route_without_doorways_or_outside_the_rooms():
    snapshot = replay('halls_of_pain_live')
    room = snapshot.rooms[0]

    assert route(snapshot.rooms, (snapshot.location.x / 5, snapshot.location.y / 5), room) is None
    tower = replay('tower_cellar_1')
    assert route(tower.rooms, (0.0, 0.0), tower.rooms[0]) is None


def test_player_already_in_the_target_room_is_a_one_room_route():
    tower = replay('tower_cellar_1')
    room = tower.rooms[3]

    assert route(tower.rooms, (room.x + 1, room.y + 1), room) == [room]


@pytest.mark.parametrize('fixture', ['worldstone_keep_2', 'worldstone_keep_3'])
def test_route_runs_over_whole_presets_when_rooms_are_chunked(fixture):
    from inventory_tracking.levels.registry import handler_for

    snapshot = replay(fixture)
    [stairs, *_] = handler_for(snapshot.location.area_id).guide(snapshot).pois
    tile = (snapshot.location.x / TILE_UNITS, snapshot.location.y / TILE_UNITS)

    path = route(snapshot.rooms, tile, stairs.room)

    assert path[0].x <= tile[0] < path[0].x + path[0].width
    assert path[-1] == stairs.room
    assert all(room.block == (room.x, room.y, room.width, room.height) for room in path)  # whole presets
