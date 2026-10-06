"""Route through a maze: preset names spell their doorways ('Act 1 - Crypt NSE').

The route runs over preset instances (levels.handler.instances): single-room presets, and
large presets split into 8x8 Room2 chunks (Worldstone Keep's 16x16 rooms) as one node.
Doorway letters use map axes, N = -y, E = +x. Checked 2026-09-30 on the Tower Cellar 1-4,
Durance 2, Arcane, Jail 1 and Worldstone Keep 2-3 fixtures: every doorway faced a neighbouring
instance with the opposite doorway. Two instances connect when they share an edge and both open
onto it. Names without a trailing doorway token have none; Temple quadrant names ('Temple NE')
are positions, not doorways, so Temple levels get no route.
"""

import re
from collections import deque
from collections.abc import Iterable

from inventory_tracking.levels.handler import instances
from inventory_tracking.levels.model import Room
from inventory_tracking.levels.presets import preset_name


OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
DOORWAYS = re.compile(r' ([NSEW]+)$')
NO_DOORWAY_FAMILIES = ('Act 5 - Temple',)  # quadrant names give positions


def doorways(room: Room) -> set[str] | None:
    name = preset_name(room.preset)
    if name.startswith(NO_DOORWAY_FAMILIES):
        return None
    if room.block is not None and room.block != (room.x, room.y, room.width, room.height):
        return None  # a chunk: its preset instance carries the doorways
    match = DOORWAYS.search(name)
    return set(match.group(1)) if match else None


def room_at(rooms: Iterable[Room], tile: tuple[float, float]) -> Room | None:
    x, y = tile
    return next((r for r in rooms if r.x <= x < r.x + r.width and r.y <= y < r.y + r.height), None)


def adjacent(here: Room, there: Room, letter: str) -> bool:
    """`there` touches `here`'s `letter` edge and overlaps it along that edge."""
    if letter in 'EW':
        touching = there.x == here.x + here.width if letter == 'E' else there.x + there.width == here.x
        return touching and there.y < here.y + here.height and here.y < there.y + there.height
    touching = there.y == here.y + here.height if letter == 'S' else there.y + there.height == here.y
    return touching and there.x < here.x + here.width and here.x < there.x + there.width


def route(rooms: Iterable[Room], tile: tuple[float, float], goal: Room) -> list[Room] | None:
    """Shortest path of preset instances from the one holding `tile` to `goal`, or None."""
    nodes = [room for room, _ in instances(rooms)]
    start = room_at(nodes, tile)
    if start is None or goal not in nodes or doorways(start) is None:
        return None  # no doorways where the player stands (a Temple quadrant): nothing to route through
    previous: dict[Room, Room | None] = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            path = []
            while here is not None:
                path.append(here)
                here = previous[here]
            return path[::-1]
        for letter in doorways(here) or ():
            for there in nodes:
                if (
                    there not in previous
                    and adjacent(here, there, letter)
                    and OPPOSITE[letter] in (doorways(there) or ())
                ):
                    previous[there] = here
                    queue.append(there)
    return None
