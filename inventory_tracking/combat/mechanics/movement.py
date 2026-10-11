"""Where a walking monster will be: its own route, read from its path record (combat/plan.md, the
movement research of 2026-10-11).

The client holds, for every monster, the waypoints it is walking and which one it is going to
(macros/world.py PATH_RECORD; the recorder writes the records to a take's paths.jsonl). A monster
walks straight from waypoint to waypoint at its monstats Velocity (Run when it runs), in world units
a second. On the Far Oasis take of 2026-10-10 22:42 UTC, 15 frames ahead, this put a moving hostile
1.46 units off on average and more than 2 units off 24% of the time; its last three frames'
velocity carried on gave 1.82 and 33%, standing still 2.50 and 49%. What it does not know: a monster
that stops to attack or to think again inside the window, and a speed the monstats row does not give.
"""

import math
import struct
from dataclasses import dataclass

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.timeline import GAME_RATE


Point = tuple[float, float]
WALK, RUN = 2, 15  # monster modes that follow a route
CURRENT, COUNT = 0x30, 0x34  # the waypoint the monster is going to, and how many there are
WAYPOINTS = 0xC8  # x, y cells (u16 pairs)
MOST_WAYPOINTS = 78  # what the record has room for by the classic layout
CELL_CENTRE = 0.5  # a waypoint is a cell; a monster standing on it is read at its middle


@dataclass(frozen=True)
class Route:
    points: tuple[Point, ...]  # the waypoints still ahead, the next one first
    speed: float  # world units a frame

    def after(self, at: Point, frames: float) -> Point:
        """Where a monster now at `at` is `frames` later: along the waypoints, standing at the last."""
        x, y = at
        left = self.speed * frames
        for px, py in self.points:
            gap = math.hypot(px - x, py - y)
            if gap >= left:
                return (x + (px - x) * left / gap, y + (py - y) * left / gap) if gap else (x, y)
            left -= gap
            x, y = px, py
        return (x, y)


def speed_of(txt: int, mode: int) -> float:
    """World units a frame for the monster type walking or running (monstats Velocity, Run); 0 unknown."""
    row = tables()['monsters'].get(str(txt), {})
    return float(row.get('Run' if mode == RUN else 'Velocity') or 0) / GAME_RATE


def route_of(record: bytes, txt: int, mode: int) -> Route | None:
    """The route a walking or running monster's path record holds; None when it is doing something
    else, has no waypoint left, or its type's speed is not known."""
    if mode not in (WALK, RUN) or len(record) < WAYPOINTS:
        return None
    current, count = struct.unpack_from('<II', record, CURRENT)
    count = min(count, MOST_WAYPOINTS, (len(record) - WAYPOINTS) // 4)
    speed = speed_of(txt, mode)
    if current >= count or not speed:
        return None
    cells = struct.iter_unpack('<HH', record[WAYPOINTS + 4 * current : WAYPOINTS + 4 * count])
    return Route(tuple((x + CELL_CENTRE, y + CELL_CENTRE) for x, y in cells), speed)
