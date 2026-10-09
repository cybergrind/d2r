"""Route through a level for a player who teleports (the Warlock casts Teleport from a staff).

Teleport ignores walls and doorways: any point on a loaded room is a landing spot, so the route is
the straight line to the target wherever that line stays over rooms. Only void (no Room2 at all)
is an obstacle, and a teleport crosses void up to REACH tiles wide: half a screen (geometry.py,
~40 world units wide). The route is the shortest chain of room instances (levels.handler.instances:
chunks of a large preset collapse into one) whose gaps a teleport crosses, pulled tight so a
straight hop replaces every detour that stays passable. The user asked for this on 2026-10-09: the
doorway walk (the old BFS, in git history) sent them around a maze whose stairs were one teleport away.
"""

import heapq
import math
from collections.abc import Iterable, Sequence

from inventory_tracking.levels.handler import instances
from inventory_tracking.levels.model import Room


REACH = 4.0  # tiles of void one teleport crosses: half a screen's width
STEP = 0.25  # tiles between samples along a hop (walls between rooms are thinner than a tile)

Point = tuple[float, float]


def room_at(rooms: Iterable[Room], tile: Point) -> Room | None:
    x, y = tile
    return next((r for r in rooms if r.x <= x < r.x + r.width and r.y <= y < r.y + r.height), None)


def centre(room: Room) -> Point:
    return room.x + room.width / 2, room.y + room.height / 2


def gap(here: Room, there: Room) -> float:
    """Distance between two rooms' rectangles: 0 when they touch or overlap."""
    dx = max(there.x - (here.x + here.width), here.x - (there.x + there.width), 0)
    dy = max(there.y - (here.y + here.height), here.y - (there.y + there.height), 0)
    return math.hypot(dx, dy)


def passable(rooms: Sequence[Room], start: Point, end: Point, reach: float = REACH) -> bool:
    """A teleport chain follows the straight line: no void run along it is wider than `reach`."""
    length = math.dist(start, end)
    samples = max(int(length / STEP), 1)
    void = 0.0
    for index in range(samples + 1):
        t = index / samples
        point = (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
        if room_at(rooms, point) is not None:
            void = 0.0
        else:
            void += length / samples
            if void > reach:
                return False
    return True


def pull_tight(rooms: Sequence[Room], points: list[Point], reach: float = REACH) -> list[Point]:
    """Drop every waypoint a straight passable hop skips, greedily from the start."""
    tight = [points[0]]
    index = 0
    while index < len(points) - 1:
        hops = range(len(points) - 1, index + 1, -1)  # the next point is kept when nothing further is passable
        far = next((j for j in hops if passable(rooms, points[index], points[j], reach)), index + 1)
        tight.append(points[far])
        index = far
    return tight


def route(rooms: Iterable[Room], tile: Point, goal: Point, reach: float = REACH) -> list[Point] | None:
    """Teleport hops from `tile` to `goal` (both in tiles): the points to draw, or None off the rooms."""
    rooms = list(rooms)
    nodes = [room for room, _ in instances(rooms)]
    start, end = room_at(nodes, tile), room_at(nodes, goal)
    if start is None or end is None:
        return None
    if passable(rooms, tile, goal, reach):
        return [tile, goal]
    points = {node: centre(node) for node in nodes}
    points[start], points[end] = tile, goal
    cost = {start: 0.0}
    previous: dict[Room, Room | None] = {start: None}
    queue = [(0.0, 0, start)]
    tie = 1  # rooms don't order; break equal costs by insertion
    while queue:
        here_cost, _, here = heapq.heappop(queue)
        if here == end:
            path = []
            step: Room | None = here
            while step is not None:
                path.append(points[step])
                step = previous[step]
            return pull_tight(rooms, path[::-1], reach)
        if here_cost > cost[here]:
            continue
        for there in nodes:
            if there == here or gap(here, there) > reach:
                continue
            there_cost = here_cost + math.dist(points[here], points[there])
            if there_cost < cost.get(there, math.inf):
                cost[there], previous[there] = there_cost, here
                heapq.heappush(queue, (there_cost, tie, there))
                tie += 1
    return None
