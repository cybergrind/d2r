"""What one game has taught about its levels' rooms, kept until the game ends.

A room's details arrive late: the levels behind it (Room.leads_to) are readable only after the
player has been near that edge, and its preset's DS1 variant and bounds are sometimes unreadable
on entry (21 of the evidence records up to 2026-10-05, giving '25 rooms match' in the Halls of
Pain). A level's layout is fixed for the whole game, so whatever was read once stays true: each
read is merged with the earlier ones, and an exit named once keeps its name after a town trip.

The memory is keyed by the level's layout (every room's preset and bounds), so a new game's
levels never meet an old game's rooms even if leaving the game was missed; `reset()` (the guide
calls it when the player is in no level, i.e. the menu) only frees the old game's levels.
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
