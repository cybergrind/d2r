"""Where a Teleport may land from where the character stands: the game's own rule per level.

The rule (D2MOO SkillSor.cpp `SKILLS_SrvDo027_Teleport`, levels.txt `Teleport`): 0, no Teleport; 1, a Teleport lands
on the free cells nearest the aim whatever lies between (`sub_6FCBDFE0`: `COLLISION_GetFreeCoordinates`); 2, only
when the line from the character to the aim meets no cell a flying player is barred by (`UNITS_TestCollision` with
COLLIDE_MASK_PLAYER_FLYING, COLLIDE_DOOR | COLLIDE_MISSILE_BARRIER, `COLLISION_RayTrace`). Duriel's Lair (73) is the
one level with 2 (d2data levels.json, bundled in data/level_presets.json `teleport`).

Measured 2026-10-23 over the takes of 2026-10-19..23 (rca/2026-10-23/gap-findings.md): off Duriel's Lair, hops landed
across up to 33 sub-tiles of wall and 23,461 landings had that line barred; in Duriel's Lair all 5 landings had it
clear and all 46 refusals barred, gaps of 1 to 17 sub-tiles: the game counts no gap width, only that line. The cast
is made and its mana spent, and the character stays ("nothing 0.6s after the key").

Pure: no game reads. Cells no grid covers count as clear (the planner's own optimism over rooms not read yet).
"""

import math
from collections.abc import Iterator, Sequence
from functools import lru_cache

from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground, Walkable, unpack_cells, unpack_masks
from inventory_tracking.levels.presets import teleport_rule
from inventory_tracking.native.layout import TILE_UNITS


# 2026-10-23 (the player, on Duriel's Lair: "we try to teleport through the bigger gap that we can"; "your goal is to
# maximize exp/hour"): 10-36 s a visit went on Teleports across the lair's walls the game refused, the room behind
# them the agenda's target (rca/2026-10-23/gap-findings.md). True: on a level whose rule is LINE, a hop lands only
# over a clear line (`hop_lands`), for the hop planner's way (macros/teleport.py `Way`), its landing (`landing`),
# the stride (macros/travel.py) and so the explore target (macros/hunt.py `frontier`: a room no such way reaches is
# no stop). False: a Teleport crosses anything, as before.
TELEPORT_LINE = True
LINE = 2  # levels.txt Teleport: only over a clear line
ANY = 1
FLY_BARS = 0x0804  # COLLIDE_DOOR | COLLIDE_MISSILE_BARRIER (D2MOO D2Collision.h COLLIDE_MASK_PLAYER_FLYING)
UNIT_SIZE = 2  # the player's and the aim's size in `UNITS_TestCollision` (each capped at 2)


def lined(area: int | None) -> bool:
    """Whether a Teleport on level `area` needs a clear line (TELEPORT_LINE and the level's rule is LINE)."""
    return TELEPORT_LINE and area is not None and teleport_rule(area) == LINE


def ray(start: tuple[int, int], end: tuple[int, int], size: int = UNIT_SIZE) -> Iterator[tuple[int, int]]:
    """The sub-tiles the game's line test looks at from `start` to `end`: both ends moved `size` toward each other
    along the longer axis (both axes on a diagonal), then every cell of the stepped line, both ends included
    (D2MOO Units.cpp `UNITS_TestCollision`, D2Collision.cpp `COLLISION_RayTrace`). None when they touch."""
    (x1, y1), (x2, y2) = start, end
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    if dx + dy < 2 * size:
        return
    if dx >= dy:
        x1, x2 = (x1 - size, x2 + size) if x2 <= x1 else (x1 + size, x2 - size)
    if dy >= dx:
        y1, y2 = (y1 - size, y2 + size) if y2 <= y1 else (y1 + size, y2 - size)
    sx, sy = (1 if x2 >= x1 else -1), (1 if y2 >= y1 else -1)
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    x, y, deviation = x1, y1, 0
    yield x, y
    if dx < dy:
        while y != y2:
            y += sy
            deviation += dx
            if deviation >= dy:
                deviation -= dy
                x += sx
            yield x, y
    else:
        while x != x2:
            x += sx
            deviation += dy
            if deviation >= dx:
                deviation -= dx
                y += sy
            yield x, y


def cell(point: Point) -> tuple[int, int]:
    return math.floor(point[0]), math.floor(point[1])


@lru_cache(maxsize=16)
def bars(grids: tuple[Walkable, ...]) -> frozenset[tuple[int, int]]:
    """The sub-tiles a flying player is barred by: a raw mask with FLY_BARS, else (no masks read) one missiles do
    not fly through, else (no flight layer) one not walkable. Built once per set of grids."""
    found: set[tuple[int, int]] = set()
    for grid in grids:
        columns, rows = grid.width * TILE_UNITS, grid.height * TILE_UNITS
        left, top = grid.x * TILE_UNITS, grid.y * TILE_UNITS
        masks = unpack_masks(grid.masks, columns * rows) if grid.masks else None
        if masks is not None:
            barred = [index for index, mask in enumerate(masks) if mask & FLY_BARS]
        else:
            bits = unpack_cells(grid.flight, columns * rows) if grid.flight else None
            bits = bits if bits is not None else unpack_cells(grid.cells, columns * rows)
            barred = [index for index, bit in enumerate(bits or '') if bit != '1']
        found.update((left + index % columns, top + index // columns) for index in barred)
    return frozenset(found)


def crossed(barred: frozenset[tuple[int, int]], start: Point, end: Point) -> bool:
    """Whether the game's line from `start` to `end` (world units) meets none of `barred`."""
    return not any(step in barred for step in ray(cell(start), cell(end)))


def line_clear(ground: Ground, start: Point, end: Point, doors: Sequence[Door] = ()) -> bool:
    """Whether the game's Teleport line from `start` to `end` meets no barred cell of `ground` and no closed door."""
    if not crossed(bars(ground.grids), start, end):
        return False
    closed = [door for door in doors if door.closed]
    return not closed or not any(
        door.blocks((x + 0.5, y + 0.5)) for x, y in ray(cell(start), cell(end)) for door in closed
    )


def hop_lands(area: int | None, ground: Ground | None, start: Point, end: Point, doors: Sequence[Door] = ()) -> bool:
    """The one reachability fact for a Teleport from `start` to `end` (world units) on level `area`: True unless the
    level's rule needs a clear line (`lined`) and the line is barred. Footing at `end` is the caller's own test."""
    if ground is None or not lined(area):
        return True
    return line_clear(ground, start, end, doors)
