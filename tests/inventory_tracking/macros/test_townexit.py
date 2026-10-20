"""The walk out of a town (macros/townexit.py): along the gate's walk on the town's walls, past its edge, until the
level changes (rca/2026-10-19/town-exit-findings.md)."""

import logging
from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.levels.model import Level, Room, Walkable, pack_cells
from inventory_tracking.levels.town_gate import Gate
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.townexit import aim, walk_out
from tests.inventory_tracking.macros.fakes import Game, player, world


SIZE = 40  # units: one 8x8 tile town, walled round, its east wall open at y 10-14 (layout 1:1, the east one)
ROOMS = (Room(1, 0, 0, 8, 8, 1, (0, 0, 8, 8)),)


def walls() -> Walkable:
    rows = []
    for y in range(SIZE):
        row = ''
        for x in range(SIZE):
            wall = y in (0, SIZE - 1) or x == 0 or (x == SIZE - 1 and not 10 <= y <= 14) or (x == 20 and y >= 6)
            row += '0' if wall else '1'
        rows.append(row)
    return Walkable(0, 0, 8, 8, pack_cells(''.join(rows)))


class Town(Game):
    """The fakes' game, whose character leaves the town into level `to` once past its east edge."""

    def __init__(self, start: tuple[float, float], to: int = 2, edge: float = SIZE):
        super().__init__(world(1, player=player(1, x=start[0], y=start[1])))
        self.to, self.edge = to, edge

    def act(self, event) -> None:
        super().act(event)
        here = self.world.player
        if here is not None and here.area == 1 and here.x >= self.edge:
            self.world = replace(self.world, player=replace(here, area=self.to))


LEVEL = Level(1, ROOMS, (walls(),))


def test_the_walk_goes_round_the_wall_through_the_gate_and_out_into_the_next_level(caplog):
    game = Town((10.5, 30.5))
    with caplog.at_level(logging.INFO):
        reached = walk_out(game.run(), lambda: LEVEL, 2)
    assert reached.player is not None
    assert reached.player.area == 2
    # Round the inner wall (x 20, y 6 on) by its north end, then east to the gap at y 10-14
    assert any(abs(x - 20) <= 3 and y < 6 for x, y in game.walks)
    steps = [(10.5, 30.5), *game.walks]
    for (x0, y0), (x1, y1) in pairwise(steps):
        if (x0 - 20) * (x1 - 20) < 0:  # a walk across the wall's line is across its open north end
            assert y0 + (y1 - y0) * (20 - x0) / (x1 - x0) < 6
    assert all(10 <= y <= 14 for x, y in game.walks if x > 38)
    text = caplog.text
    assert 'Macro: town exit: Rogue Encampment into Blood Moor: the east gate at (39.5, 12.5)' in text
    assert 'Macro: town exit: click 1 at (10.5, 30.5)' in text
    assert 'Macro: town exit: in Blood Moor after' in text


def test_a_panel_a_click_opened_on_the_way_is_closed_and_the_walk_goes_on(caplog):
    game = Town((30.5, 12.5))
    game.world = replace(game.world, open_panels=('npc_interact',))  # a townsman's menu, as a click on him opens
    with caplog.at_level(logging.INFO):
        reached = walk_out(game.run(), lambda: LEVEL, 2)
    assert reached.player is not None
    assert reached.player.area == 2
    assert reached.open_panels == ()
    assert 'Macro: walk: the way out to Blood Moor: npc_interact opened on the way: closed' in caplog.text


def test_no_map_or_no_town_or_no_crossing_is_a_stop():
    with pytest.raises(Abort, match='the level guide has no map of the town'):
        walk_out(Town((10.5, 30.5)).run(), lambda: None, 2)
    unread = Level(1, (Room(1, 0, 0, 8, 8),), ())
    with pytest.raises(Abort, match="the town's layout is not read"):
        walk_out(Town((10.5, 30.5)).run(), lambda: unread, 2)
    field = Game(world(3, player=player(3)))
    with pytest.raises(Abort, match='not in town'):
        walk_out(field.run(), lambda: LEVEL, 2)
    stuck = Town((10.5, 30.5), edge=10**6)  # the edge never crossed
    with pytest.raises(Abort, match='not reached by walking'):
        walk_out(stuck.run(), lambda: LEVEL, 2)


def test_a_click_aims_ahead_along_the_walk_and_past_the_edge_at_its_end():
    path = tuple((float(x), 5.0) for x in range(1, 31))
    gate = Gate(1, (1, 0), (30.0, 5.0), (35.5, 5.0), path)
    assert aim(gate, (1.0, 5.0), 24.0) == (25.0, 5.0)
    assert aim(gate, (10.0, 5.0), 24.0) == (35.5, 5.0)  # the walk's end within reach: past the edge
    bent = Gate(1, (1, 0), (30.0, 5.0), (35.5, 5.0), ((1.0, 1.0), (1.0, 20.0), (5.0, 20.0), (5.0, 1.0), (30.0, 5.0)))
    assert aim(bent, (1.0, 1.0), 24.0) == (5.0, 1.0)  # the furthest within reach, the walk's last point too far
    straight = lambda a, b: a[0] == b[0] or a[1] == b[1]  # ruff: ignore[lambda-assignment]  (only lines along an axis are clear)
    assert aim(bent, (1.0, 1.0), 24.0, straight) == (1.0, 20.0)  # not on past a point behind a wall
    assert aim(Gate(1, (1, 0), (30.0, 5.0), (35.5, 5.0)), (1.0, 5.0), 24.0) == (35.5, 5.0)  # no walk: straight
