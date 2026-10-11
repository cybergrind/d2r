"""The explore step's rule until 2026-10-11 (macros/hunt.py `frontier`, replaced by macros/tour.py),
kept here as the reference: the unexplored room nearest by the way there, a turn away from the last
step's heading counted as up to TURN_TILES more. Rooms no teleport lands in were never gone to.
"""

import math

from inventory_tracking.levels.model import Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.teleport import Way
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS

from .harness import Pick, Replay


TURN_TILES = 8.0


def nearest_rule(replay: Replay) -> Pick:
    heading: list[tuple[float, float]] = []

    def pick(level, player, rect):
        here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
        rooms = [
            room
            for room in level.rooms
            if (room.x, room.y, room.width, room.height) not in replay.explored and room_at((room,), here) is None
        ]
        origin = Way(Target(level.area, level.rooms, here, 'here', 'explore', False, level.ground), Viewport.of(rect))
        best = None
        for room in rooms:
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    cost = origin.cost.get((x, y))
                    if cost is None:
                        continue
                    score = cost
                    away = math.dist(here, (x + 0.5, y + 0.5))
                    if heading and away > 0:
                        along = ((x + 0.5 - here[0]) * heading[0][0] + (y + 0.5 - here[1]) * heading[0][1]) / away
                        score += TURN_TILES * (1 - along) / 2
                    if best is None or score < best[0]:
                        best = (score, cost, room, (x, y))
        if best is None:
            return None
        x, y = best[3]
        away = math.dist(here, (x + 0.5, y + 0.5))
        if away > 0:
            heading[:] = [((x + 0.5 - here[0]) / away, (y + 0.5 - here[1]) / away)]
        return best[1:]

    return pick
