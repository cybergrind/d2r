"""What one game has taught about its levels' rooms, kept until the game ends.

Room details arrive late (Room.leads_to once the player was near; a variant sometimes unreadable on entry),
but a level's layout is fixed for the game, so each read is merged with the earlier ones. Keyed by the
layout, so a new game never meets an old game's rooms; `reset()` (in the menu) only frees memory.
"""

from collections.abc import Iterable
from dataclasses import replace

from inventory_tracking.levels.model import Room


def room_key(room: Room) -> tuple[int, int, int, int, int]:
    return room.preset, room.x, room.y, room.width, room.height


def layout_key(area: int | None, rooms: Iterable[Room]) -> tuple:
    """Identifies one generated level: the same in every read of one game, whatever has loaded."""
    return area, frozenset(room_key(room) for room in rooms)


class LevelMemory:
    def __init__(self):
        self.levels: dict[tuple, dict[tuple, Room]] = {}

    def reset(self):
        self.levels.clear()

    def merge(self, area: int | None, rooms: Iterable[Room]) -> tuple[Room, ...]:
        """`rooms` with everything earlier reads of this level knew; remembers the result."""
        rooms = tuple(rooms)
        known = self.levels.setdefault(layout_key(area, rooms), {})
        merged = []
        for room in rooms:
            before = known.get(room_key(room))
            if before is not None:
                leads_to = (*before.leads_to, *(a for a in room.leads_to if a not in before.leads_to))
                room = replace(
                    room,
                    variant=before.variant if room.variant is None else room.variant,
                    block=before.block if room.block is None else room.block,
                    leads_to=leads_to,
                )
            known[room_key(room)] = room
            merged.append(room)
        return tuple(merged)
