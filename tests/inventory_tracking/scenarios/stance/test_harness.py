"""The stance harness: the timing of a walk and a hop, a barred walk, production's step round a wall, and the fixture
round trip. The monsters are the revivers' own table rows (Catacombs Level 1, a fallen), never invented ids."""

import json
from collections.abc import Callable
from dataclasses import asdict

from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.native.layout import TILE_UNITS

from ..revivers.scenarios import CATACOMBS, FALLEN
from .harness import Move, Point, Strategy, View, body, load, play, production, scene, stay


ORIGIN = (5000.0, 5000.0)
TILES = (990, 990, 20, 20)  # the grid's tiles: world 4950 to 5050 on each axis


def at(dx: float, dy: float) -> Point:
    return (ORIGIN[0] + dx, ORIGIN[1] + dy)


def grid(wall: Callable[[Point], bool] | None = None) -> Ground:
    """One walkable grid over TILES; a sub-tile whose centre `wall` names is unwalkable and flies no blade."""
    x0, y0, width, height = TILES
    columns, rows = width * TILE_UNITS, height * TILE_UNITS
    bits = ''.join(
        '0' if wall is not None and wall((x0 * TILE_UNITS + c + 0.5, y0 * TILE_UNITS + r + 0.5)) else '1'
        for r in range(rows)
        for c in range(columns)
    )
    cells = pack_cells(bits)
    return Ground([Walkable(x0, y0, width, height, cells, cells)])


def south_wall(point: Point) -> bool:
    """A two-unit wall at x 5004 to 5006 from y 4997 south: a gap to the north walks round it."""
    return 5004 <= point[0] <= 5006 and point[1] >= 4997


def first_then_stay(move: Move) -> tuple[Strategy, list[int]]:
    """A strategy that moves once, then stays; the frames it was asked at."""
    asked: list[int] = []

    def strategy(view: View) -> Move | None:
        asked.append(view.frame)
        return move if len(asked) == 1 else None

    return strategy, asked


def test_a_monster_ten_units_away_in_the_open_is_cleared_by_staying():
    open_scene = scene('open', CATACOMBS, ORIGIN, (body(1, FALLEN, at(10, 0), CATACOMBS),))
    result = play(open_scene, stay, seconds=5)
    assert result.cleared
    assert result.casts >= 1
    assert result.moves == 0
    assert result.kills_at == [result.cleared_at]


def test_a_monster_out_of_reach_is_never_cast_at_by_staying():
    far = scene('far', CATACOMBS, ORIGIN, (body(1, FALLEN, at(28, 0), CATACOMBS),))
    result = play(far, stay, seconds=5)
    assert not result.cleared
    assert result.casts == 0
    assert result.alive == 1


def test_a_walk_of_ten_units_costs_nine_plus_thirteen_frames():
    open_scene = scene('walk', CATACOMBS, ORIGIN, (body(1, FALLEN, at(10, 0), CATACOMBS),))
    strategy, asked = first_then_stay(Move(at(0, 10)))
    result = play(open_scene, strategy, seconds=3)
    assert asked[:2] == [0, 22]  # 9 frames of latency, then ceil(10 / 20 * 25) = 13 frames of running
    assert result.walked == 10.0
    assert result.casts >= 1
    assert result.moves == 1


def test_a_hop_costs_thirty_eight_frames_whatever_the_distance():
    open_scene = scene('hop', CATACOMBS, ORIGIN, (body(1, FALLEN, at(10, 0), CATACOMBS),))
    strategy, asked = first_then_stay(Move(at(0, 10), hop=True))
    result = play(open_scene, strategy, seconds=3)
    assert asked[:2] == [0, 38]
    assert result.walked == 0.0
    assert result.moves == 1


def test_a_walk_through_a_barred_line_is_refused_and_the_turn_casts_instead():
    wall = scene('refused', CATACOMBS, ORIGIN, (body(1, FALLEN, at(0, 10), CATACOMBS),), grid(south_wall))
    strategy, asked = first_then_stay(Move(at(14, 0)))  # a walk east, across the wall
    result = play(wall, strategy, seconds=2)
    assert result.refused == 1
    assert result.moves == 0
    assert result.walked == 0.0
    assert result.casts >= 1  # the monster to the north is in the open: the refused turn casts
    assert asked[0] == 0


def test_production_walks_round_a_wall_where_staying_does_not():
    behind = scene('round', CATACOMBS, ORIGIN, (body(1, FALLEN, at(10, 0), CATACOMBS),), grid(south_wall))
    walked = play(behind, production(), seconds=6)
    assert walked.moves >= 1
    assert walked.cleared
    assert not play(behind, stay, seconds=6).cleared


def test_a_fixture_loads_as_the_scene_it_records(tmp_path):
    fixture = {
        'name': 'moment',
        'area': CATACOMBS,
        'in_fight': True,
        'player': [5000.0, 5000.0],
        'hostiles': [{'unit': 123, 'txt': FALLEN, 'at': [5010.0, 5000.0], 'life': 0.5, 'elite': False}],
        'companions': [{'unit': 5, 'txt': 744, 'at': [5001.0, 5000.0]}],
        'doors': [[77, 13, 0, 5000.0, 4990.0]],
        'ground': [asdict(grid(south_wall).grids[0])],
        'after': {'cleared_seconds': 7.4, 'casts': 9, 'alive_at': {'1.0': 14}, 'player_at': {'1.0': [5000.0, 5000.0]}},
    }
    path = tmp_path / 'moment.json'
    path.write_text(json.dumps(fixture))
    loaded = load(path)
    assert loaded.name == 'moment'
    assert loaded.area == CATACOMBS
    assert loaded.origin == (5000.0, 5000.0)
    assert [(b.unit, b.txt, b.at, b.life) for b in loaded.bodies] == [(123, FALLEN, (5010.0, 5000.0), 0.5)]
    assert loaded.ground is not None
    assert len(loaded.ground) == 1
    assert [door.unit_id for door in loaded.doors] == [77]
    assert loaded.blocked is not None  # a closed door, and the grid's flight layer
    assert loaded.barred is not None
    assert loaded.barred(at(0, 5)) is False
    assert loaded.barred((5000.0, 4990.0)) is True  # the closed door stands there
    assert loaded.recorded == fixture['after']
