"""The towns' ways out on foot (levels/town_gate.py), on the learned walls of every town layout
(fixtures/towns/town_walls.json: runs/levels/walls.json and one Win+C room list per layout, 2026-10-19)."""

import json
import math
from itertools import pairwise
from pathlib import Path

import pytest

from inventory_tracking.levels.model import Ground, Room, Walkable, pack_cells
from inventory_tracking.levels.town_gate import GATES, SIDES, E, N, S, W, town_gate, town_room
from inventory_tracking.levels.walls import WallLibrary


FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'towns' / 'town_walls.json'  # not levels/: no level dump
TOWNS = json.loads(FIXTURE.read_text())['towns']


def town(key: str) -> tuple[tuple[Room, ...], Ground, tuple[float, float], tuple[float, float]]:
    """(rooms, the library's ground, the waypoint, the town's corner) of layout `key` ('preset:variant')."""
    found = TOWNS[key]
    rooms = tuple(Room.from_row(row) for row in found['rooms'])
    block = rooms[0].block
    assert block is not None
    return rooms, Ground(WallLibrary(FIXTURE).known(rooms)), tuple(found['waypoint']), (block[0] * 5, block[1] * 5)


@pytest.mark.parametrize('key', sorted(TOWNS))
def test_every_town_layout_has_its_gate_on_its_side_where_gates_says(key):
    rooms, ground, waypoint, corner = town(key)
    gate = town_gate(rooms, ground.walkable, waypoint)
    assert gate is not None
    assert gate.walls
    preset, variant = map(int, key.split(':'))
    layout = (preset, variant)
    assert gate.side == SIDES[layout]
    assert (gate.edge[0] - corner[0], gate.edge[1] - corner[1]) == GATES[layout]
    # The walk is on the walls, step by step, and ends on the edge; past it lies outside the town
    steps = (waypoint, *gate.path)
    assert all(math.dist(a, b) <= math.sqrt(2) + 1 for a, b in pairwise(steps[1:]))
    assert all(ground.walkable(*point) for point in gate.path)
    assert gate.path[-1] == gate.edge
    assert ground.walkable(*gate.beyond) is None


def test_the_two_walks_out_by_hand_crossed_at_the_gates_found():
    # The last town frames of 20261017T194010Z-1 (layout 1:1, corner (1064, 928) tiles) and 20261014T204042Z-103 (the
    # Fortress, corner (1000, 1000)), each the frame before the next level's take
    crossed = {'1:1': (5600.44 - 1064 * 5, 4724.82 - 928 * 5), '797:0': (5159.45 - 5000, 5087.07 - 5000)}
    for key, at in crossed.items():
        rooms, ground, waypoint, corner = town(key)
        gate = town_gate(rooms, ground.walkable, waypoint)
        assert gate is not None
        assert math.dist((gate.edge[0] - corner[0], gate.edge[1] - corner[1]), at) <= 3.0


def test_a_new_game_start_in_the_rogue_encampment_finds_the_same_gate():
    rooms, ground, waypoint, corner = town('1:1')
    middle = (corner[0] + 140, corner[1] + 100)  # the camp's middle, where a game begins
    start = next(
        (middle[0] + dx, middle[1] + dy) for dx in range(-20, 21) for dy in range(-20, 21)
        if ground.walkable(middle[0] + dx, middle[1] + dy)
    )  # fmt: skip
    gate = town_gate(rooms, ground.walkable, start)
    assert gate is not None
    assert gate.edge == town_gate(rooms, ground.walkable, waypoint).edge  # type: ignore[union-attr]


def test_unread_walls_take_gates_gate_and_an_unread_layout_none():
    rooms, _, waypoint, corner = town('797:0')
    gate = town_gate(rooms, None, waypoint)
    assert gate is not None
    assert not gate.walls
    assert gate.path == ()
    assert gate.edge == (corner[0] + 159.5, corner[1] + 86.5)
    assert gate.beyond == (gate.edge[0] + 5.5, gate.edge[1])  # east, past the edge
    unread = tuple(Room(room.preset, room.x, room.y, room.width, room.height) for room in rooms)
    assert town_room(unread) is None
    assert town_gate(unread, None, waypoint) is None


def test_a_walled_square_is_left_by_its_one_gap_not_by_a_seam():
    # One 8x8 town tile (40 units) walled round; the north wall has a gap of 5 cells at x 10-14 and a seam of 2 at 30-31
    size = 40
    rows = []
    for y in range(size):
        row = ''
        for x in range(size):
            wall = x in (0, size - 1) or y == size - 1 or (y == 0 and not (10 <= x <= 14 or 30 <= x <= 31))
            row += '0' if wall else '1'
        rows.append(row)
    ground = Ground((Walkable(0, 0, 8, 8, pack_cells(''.join(rows))),))
    rooms = (Room(1, 0, 0, 8, 8, 0, (0, 0, 8, 8)),)  # 1:0, the north layout
    gate = town_gate(rooms, ground.walkable, (30.5, 30.5))
    assert gate is not None
    assert gate.side == N
    assert gate.edge == (12.5, 0.5)
    assert gate.beyond == (12.5, -5.0)
    assert {N, E, S, W} == set(SIDES.values())
