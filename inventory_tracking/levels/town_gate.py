"""A town's way out to the wilderness on foot: the gate on its walls (rca/2026-10-19/town-exit-findings.md).

A town is one preset whose DS1 file (Room.variant) is chosen per game, and in act 1 its place in the world too
(Room.block). The side its way out leaves by is fixed per file (SIDES), and the gate on it is found on the town's
walls: the shortest walk from the character to the cells of that edge, at the middle of the reachable run of them.
The wall library holds every town layout, so the whole town's walls are known from the first look
(levels/guide.py `_enter_rooms`). Room.leads_to is not used: it is read only once the player was near the edge.
GATES (the gates found so, 2026-10-19) stand in when the walls are unread. Pure.
"""

import math
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from itertools import pairwise

from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Room
from inventory_tracking.native.layout import TILE_UNITS


N, E, S, W = (0, -1), (1, 0), (0, 1), (-1, 0)
# (town preset, DS1 file index) -> the side its way to the wilderness leaves by: lvlprest.txt Def 1 File1..4 TownN1,
# TownE1, TownS1, TownW1 (the Rogue Encampment); Def 301 File2 LutW, File3 LutN (Lut Gholein); Def 797 Fortress (the
# stairs down, east). Every Win+C dump's Room.leads_to agrees (43 town dumps, 2026-09-30 to 2026-10-14)
SIDES: dict[tuple[int, int], tuple[int, int]] = {
    (1, 0): N,
    (1, 1): E,
    (1, 2): S,
    (1, 3): W,
    (301, 1): W,
    (301, 2): N,
    (797, 0): E,
}
TOWN_OF = {1: 1, 301: 40, 797: 103}  # preset -> its level
# The gate's edge cell, world units from the town's corner, found on the learned walls from the waypoint (2026-10-19;
# tests hold `town_gate` to them): used when the walls are unread. Two walks by hand crossed inside them: (280.4, 84.8)
# on 1:1 (take 20261017T194010Z-1) and (159.5, 87.1) on the Fortress (20261014T204042Z-103)
GATES: dict[tuple[int, int], Point] = {
    (1, 0): (152.5, 0.5),
    (1, 1): (279.5, 85.5),
    (1, 2): (152.5, 199.5),
    (1, 3): (0.5, 112.5),
    (301, 1): (0.5, 67.5),
    (301, 2): (92.5, 0.5),
    (797, 0): (159.5, 86.5),
}
GATE_LEAST = 3  # cells: a narrower run of reachable edge cells is a seam beside a wall, not the gate
PAST = 5.0  # units past the edge the walk aims (exits.PASSAGE_PAST is one tile): the level changes at the edge
# Units around the character a walkable start cell is looked for (it stands on a wall's cell now and then)
START_SLACK = 4
NEIGHBOURS = tuple((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


@dataclass(frozen=True)
class Gate:
    """The way out: `path` the walk's cell centres from the start to `edge` (empty from GATES), `beyond` PAST outside
    the edge, in the next level; world units. `walls`: found on the walls, else GATES."""

    town: int
    side: tuple[int, int]
    edge: Point
    beyond: Point
    path: tuple[Point, ...] = ()
    walls: bool = True

    @property
    def length(self) -> float:
        return sum(math.dist(a, b) for a, b in pairwise(self.path))


def town_room(rooms: Iterable[Room]) -> Room | None:
    """A room of a town's preset whose file and bounds are read; None while none is."""
    read = (room for room in rooms if room.variant is not None and room.block)
    return next((room for room in read if (room.preset, room.variant) in SIDES), None)


def town_gate(
    rooms: Iterable[Room], walkable: Callable[[float, float], bool | None] | None, start: Point
) -> Gate | None:
    """The town's way out from `start` (world units): the shortest walk over its walls (`walkable`: Ground.walkable)
    inside its preset to its side's edge, aimed at the middle of the reachable edge run of GATE_LEAST cells or more
    with the shortest walk. GATES' gate when the walls give none; None with no town room read."""
    room = town_room(rooms)
    if room is None:
        return None
    assert room.variant is not None
    assert room.block is not None
    layout = (room.preset, room.variant)
    side = SIDES[layout]
    left, top = room.block[0] * TILE_UNITS, room.block[1] * TILE_UNITS
    width, height = room.block[2] * TILE_UNITS, room.block[3] * TILE_UNITS
    town = TOWN_OF[room.preset]
    found = _walked(walkable, (left, top, width, height), side, start) if walkable is not None else None
    if found is not None:
        edge, path = found
        return Gate(town, side, edge, _past(edge, side), path)
    dx, dy = GATES[layout]
    edge = (left + dx, top + dy)
    return Gate(town, side, edge, _past(edge, side), walls=False)


def _past(edge: Point, side: tuple[int, int]) -> Point:
    return edge[0] + side[0] * (PAST + 0.5), edge[1] + side[1] * (PAST + 0.5)


def _walked(
    walkable: Callable[[float, float], bool | None],
    box: tuple[int, int, int, int],
    side: tuple[int, int],
    start: Point,
) -> tuple[Point, tuple[Point, ...]] | None:
    """(edge cell centre, the walk's cell centres to it) over the cells `walkable` calls walkable inside `box`; None:
    no walkable start, or no edge run reached."""
    left, top, width, height = box
    known: dict[tuple[int, int], bool] = {}

    def free(cell: tuple[int, int]) -> bool:
        found = known.get(cell)
        if found is None:
            x, y = cell
            inside = left <= x < left + width and top <= y < top + height
            found = known[cell] = inside and walkable(x + 0.5, y + 0.5) is True
        return found

    here = (math.floor(start[0]), math.floor(start[1]))
    near = [
        (here[0] + dx, here[1] + dy)
        for dx in range(-START_SLACK, START_SLACK + 1)
        for dy in range(-START_SLACK, START_SLACK + 1)
    ]
    starts = [cell for cell in near if free(cell)]
    if not starts:
        return None
    first = min(starts, key=lambda cell: math.dist(cell, here))
    before: dict[tuple[int, int], tuple[int, int] | None] = {first: None}
    steps = {first: 0}
    queue = deque([first])
    while queue:
        cell = queue.popleft()
        for dx, dy in NEIGHBOURS:
            near_cell = (cell[0] + dx, cell[1] + dy)
            if near_cell in before or not free(near_cell):
                continue
            if dx and dy and not (free((cell[0] + dx, cell[1])) and free((cell[0], cell[1] + dy))):
                continue  # no cutting a corner
            before[near_cell] = cell
            steps[near_cell] = steps[cell] + 1
            queue.append(near_cell)
    edge_line = {E: left + width - 1, W: left, S: top + height - 1, N: top}[side]
    along = 1 if side in (E, W) else 0  # the coordinate that runs along the edge
    on_edge = sorted(cell[along] for cell in before if cell[1 - along] == edge_line)
    runs: list[list[int]] = []
    for value in on_edge:
        if runs and value - runs[-1][-1] <= 1:
            runs[-1].append(value)
        else:
            runs.append([value])
    runs = [run for run in runs if len(run) >= GATE_LEAST]
    if not runs:
        return None

    def cell_of(value: int) -> tuple[int, int]:
        return (edge_line, value) if along == 1 else (value, edge_line)

    nearest = min(runs, key=lambda run: min(steps[cell_of(value)] for value in run))
    middle = (nearest[0] + nearest[-1]) / 2
    target = cell_of(min(nearest, key=lambda value: abs(value - middle)))
    path: list[Point] = []
    cell: tuple[int, int] | None = target
    while cell is not None and cell != first:
        path.append((cell[0] + 0.5, cell[1] + 0.5))
        cell = before[cell]
    return (target[0] + 0.5, target[1] + 0.5), tuple(reversed(path))
