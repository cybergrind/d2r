"""What the KP_6 loop does after a leg stops: runner.py `_loop_stopped`'s rules as pure functions of the stop's facts.
The runner asks `first`, then tries the Gheed's swap, then asks `decide`."""

from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.macros.actuator import Cause


__all__ = ['ROOM_CAUSES', 'Remedy', 'Stopped', 'decide', 'first']

# The causes the room rules answer. 'stall' counts as room until ruled otherwise
# (rca/2026-10-18/arch-loop-orchestration.md §5): a stand by a valuable must still reach the cube (2026-10-17 04:32:26).
ROOM_CAUSES: frozenset[Cause] = frozenset({'room', 'stall'})


class Remedy(StrEnum):
    DEAD = 'dead'  # the loop stops and nothing more is pressed, not even Save and Exit
    LEAVE = 'leave'  # hit standing outside a fight: the game is left at once, whatever lies on the ground
    AGAIN = 'again'  # the player's hand: the leg is made again, the game not left
    STOP = 'stop'  # the loop stops where it is (a keeper no stash page takes)
    FETCH = 'fetch'  # a valuable left for a cause other than room: the leg made again, once a game
    CUBE = 'cube'  # the loop's items into the cube for a valuable with no room, once a game
    TZ_TRIP = 'tz trip'  # a terror zone kind: the room package onto the agenda (macros/tzloop.py `trip`)
    TRIP = 'trip'  # a trip to town for room and back through the portal (macros/loop.py TRIP)
    DROP = 'drop'  # one of the loop's items to identify dropped for it, once a game
    HOLD = 'hold'  # a valuable on the ground and nothing left to try: the loop stops here, never leaves it
    RECOVER = 'recover'  # the game is left and the loop goes on (macros/loop.py `recover`)
    NOTHING = 'nothing'  # the loop is off


@dataclass(frozen=True)
class Stopped:
    """The facts of a leg's stop the rules read."""

    cause: Cause
    on: bool  # the loop is on
    left: str | None = None  # the valuable on the ground (runner.py `valuable_left`); None with the loop off
    game: str | None = None  # the game the loop is in
    fetched: bool = False  # the leg was made again for a valuable in this game already (`Loop.fetch_again`)
    cubed: bool = False  # room was made in the cube in this game already (`Loop.room_tried`)
    dropped: bool = False  # an item was dropped for room in this game already (`Loop.dropped`)
    trips: bool = False  # the kind trips to town for room and may now (Andariel: `Loop.may_trip`, carrying)
    tz_trips: bool = False  # a terror zone kind that may trip now, its level known (`tz_trip`)


def first(cause: Cause, *, on: bool, dead: bool) -> Remedy | None:
    """The rules before the Gheed's swap: by the cause alone. None: the swap, then `decide`."""
    if dead:
        # The player, 2026-10-19: "if we died - we MUST not take ANY other actions, no reviving, no save/exits"
        return Remedy.DEAD
    if on and cause == 'beset':
        # The player, 2026-10-19: "we must not die or we lose exp and our gear": no room rule nor a fetch first
        return Remedy.LEAVE
    if on and cause == 'hand':
        # Leaving the game for a moved mouse cost two games (2026-10-17 01:28:48); REPEATS bounds it
        return Remedy.AGAIN
    if on and cause == 'stash':
        # The player, 2026-10-18 16:50: "if stash is full - we need to stop loop"
        return Remedy.STOP
    return None


def decide(stop: Stopped) -> Remedy:
    """The rules after the Gheed's swap, in their order. A trip or a drop only for room: for another cause it bought a
    trip to town for nothing (2026-10-18 13:15:40)."""
    roomy = stop.cause in ROOM_CAUSES
    left, game = stop.left, stop.game
    if left is not None and not roomy and not stop.fetched:
        return Remedy.FETCH
    if left is not None and game is not None and not stop.cubed:
        return Remedy.CUBE
    if roomy and left is not None and game is not None:
        if stop.tz_trips:
            return Remedy.TZ_TRIP
        if stop.trips:
            # The player, 2026-10-18 16:50: "one game can do several trips to the town"
            return Remedy.TRIP
        if not stop.dropped:
            return Remedy.DROP
    if left is not None:
        # The player, 2026-10-17: "you we're killed the game while having valuable pickup on the ground!!! that is
        # the exact thing we want ot avoid"
        return Remedy.HOLD
    return Remedy.RECOVER if stop.on else Remedy.NOTHING
