"""Where a monster can be struck from: lines of sight over the loaded rooms' walkable sub-tiles.

Echoing Strike's blades are stopped by walls (missiles.txt `echoingstrike`, collide type 3), so a shot is clear when
every sub-tile on the line is walkable by levels/model.Ground and no closed door (levels/doors.py) stands on it. Once a
level has walls read, a cell no grid covers counts as blocked (a room not read); with no grid every cell is clear.
"The hunt must not try to hit through walls" (the player, 2026-10-09).
"""

import math
from collections.abc import Sequence

from inventory_tracking.levels import doors as door_model
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.teleport import footing
from inventory_tracking.native.layout import TILE_UNITS


SAMPLE = 0.5  # world units between the sub-tiles looked at along a shot
# World units skipped at both ends of a shot: monster and character often stand on an unwalkable edge (River of
# Flame's lava bank, 2026-10-09).
MARGIN = 1.5
BEARINGS = 16  # spots around a monster tried per ring
NEAREST_RING = 4.0  # world units: the innermost ring of firing spots
RING_STEP = 3.0


def clear_shot(ground: Ground, start: Point, end: Point, doors: Sequence[Door] = ()) -> bool:
    """Whether nothing known blocks the line: a cell missiles do not fly through (flight layer, else walk bit), an
    uncovered cell on a walled level, or a closed door: its box between the margins, and its leaf over the whole line
    (levels/doors.py SHOT_LEAF: a monster pressed into a closed doorway from the far side)."""
    closed = [door for door in doors if door.closed]
    if door_model.SHOT_LEAF and any(door.crosses(start, end) for door in closed):
        return False
    length = math.dist(start, end)
    if length <= 2 * MARGIN:
        return True
    walled = len(ground) > 0
    steps = max(int((length - 2 * MARGIN) / SAMPLE), 1)
    for index in range(steps + 1):
        t = min((MARGIN + index * SAMPLE) / length, (length - MARGIN) / length)
        point = (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
        known = ground.flyable(*point)
        if known is None:
            known = ground.walkable(*point)
        if known is False or (known is None and walled):
            return False
        if any(door.blocks(point) for door in closed):
            return False
    return True


def in_reach(ground: Ground, player: Point, mob: Point, reach: float, doors: Sequence[Door] = ()) -> bool:
    """Whether a strike from `player` at `mob` is within `reach` world units with a clear shot."""
    return math.dist(player, mob) <= reach and clear_shot(ground, player, mob, doors)


def firing_spots(
    ground: Ground, mob: Point, reach: float, player: Point, doors: Sequence[Door] = (), engage: float | None = None
) -> list[Point]:
    """Spots around `mob` with footing and a clear shot, on rings from just inside `reach` down to `NEAREST_RING`.
    Ordered nearest to `player`; with `engage`, the ring nearest it first (the outer ring missed a third of casts:
    rca/2026-10-14/run-1932-findings.md §4.2)."""
    found = []
    radius = reach - RING_STEP
    while radius >= NEAREST_RING:
        for bearing in range(BEARINGS):
            angle = 2 * math.pi * bearing / BEARINGS
            spot = (mob[0] + radius * math.cos(angle), mob[1] + radius * math.sin(angle))
            known = footing(ground, (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS))
            if known is not False and clear_shot(ground, spot, mob, doors):
                found.append((abs(radius - engage) if engage is not None else 0.0, spot))
        radius -= RING_STEP
    return [spot for _, spot in sorted(found, key=lambda row: (row[0], math.dist(row[1], player)))]
