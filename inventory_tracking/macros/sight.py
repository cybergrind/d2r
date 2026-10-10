"""Where a monster can be struck from: lines of sight over the loaded rooms' walkable sub-tiles.

Echoing Strike's blades fly over the ground (missiles.txt `echoingstrike`, collide type 3: walls stop
them), so a shot is clear when every sub-tile along the line from the character to the monster is
walkable by the grids the level guide read (levels/model.Ground), and no closed door stands on it
(levels/doors.py: the door units' modes, since the Catacombs runs of 2026-10-10 shot through closed
doors). Sub-tiles no grid covers count as blocked once the level has any walls read: the rooms
around the character are the loaded ones and have grids, so an unknown cell on the way is a room
not read (unverified footing is no place to shoot into: those runs teleported to spots with no
shot); with no grid at all every cell counts as clear. Both ends of the line are skipped by a
margin, as a monster or the character often stands on a doorway's or a lava bank's edge. The user
asked for this on 2026-10-09: the hunt must not try to hit through walls.
"""

import math
from collections.abc import Sequence

from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.teleport import footing
from inventory_tracking.native.layout import TILE_UNITS


Point = tuple[float, float]

SAMPLE = 0.5  # world units between the sub-tiles looked at along a shot
# World units at both ends of a shot not looked at: a monster often stands on a wall's very edge, and so
# does the character (River of Flame's lava-edge tiles are unwalkable by the grids while the character
# stands on them, host 2026-10-09: a shot that failed at its own first sample found nothing in reach).
MARGIN = 1.5
BEARINGS = 16  # spots around a monster tried per ring
NEAREST_RING = 4.0  # world units: the innermost ring of firing spots
RING_STEP = 3.0


def clear_shot(ground: Ground, start: Point, end: Point, doors: Sequence[Door] = ()) -> bool:
    """Whether nothing known blocks a line from `start` to `end` (world units): a cell a missile does
    not fly through (the grid's flight layer; the walk bit where a grid has none), a cell no grid
    covers when the level has walls, or a closed door."""
    length = math.dist(start, end)
    if length <= 2 * MARGIN:
        return True
    walled = len(ground) > 0
    closed = [door for door in doors if door.closed]
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


def firing_spots(ground: Ground, mob: Point, reach: float, player: Point, doors: Sequence[Door] = ()) -> list[Point]:
    """Points around `mob` (world units) with footing and a clear shot at it, within `reach`, the
    nearest to `player` first: rings `RING_STEP` apart from just inside the reach down to
    `NEAREST_RING`, `BEARINGS` points on each. Where no grid is known a spot counts as footing."""
    found = []
    radius = reach - RING_STEP
    while radius >= NEAREST_RING:
        for bearing in range(BEARINGS):
            angle = 2 * math.pi * bearing / BEARINGS
            spot = (mob[0] + radius * math.cos(angle), mob[1] + radius * math.sin(angle))
            known = footing(ground, (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS))
            if known is not False and clear_shot(ground, spot, mob, doors):
                found.append(spot)
        radius -= RING_STEP
    return sorted(found, key=lambda spot: math.dist(spot, player))
