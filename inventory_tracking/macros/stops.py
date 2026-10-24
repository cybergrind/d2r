"""What the KP_6 loop does after a leg stops: runner.py `_loop_stopped`'s rules as pure functions of the stop's facts.
The runner asks `first`, then tries the Gheed's swap, then asks `decide`."""

from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.config import HEAL_PRIORITY
from inventory_tracking.macros.actuator import Cause


__all__ = ['KEEP_GAME', 'LEFT_TOWN_AGAIN', 'ROOM_CAUSES', 'Beset', 'Remedy', 'Stopped', 'decide', 'first', 'low_life']

# The causes the room rules answer. 'stall' counts as room until ruled otherwise
# (rca/2026-10-18/arch-loop-orchestration.md §5): a stand by a valuable must still reach the cube (2026-10-17 04:32:26).
ROOM_CAUSES: frozenset[Cause] = frozenset({'room', 'stall'})


class Remedy(StrEnum):
    DEAD = 'dead'  # the loop stops and nothing more is pressed, not even Save and Exit
    # Beset with life low, beset again after fighting back, or no attacker read and nothing on the ground: the game is
    # left at once, whatever lies on the ground
    LEAVE = 'leave'
    FIGHT = 'fight back'  # beset otherwise: the attacker fought, then the valuables fetched, the game not left
    AGAIN = 'again'  # the player's hand: the leg is made again, the game not left
    STOP = 'stop'  # the loop stops where it is (a keeper no stash page takes, nothing to play)
    FETCH = 'fetch'  # a valuable left for a cause other than room: the leg made again, once a game
    CUBE = 'cube'  # the loop's items into the cube for a valuable with no room, once a game
    # The room package onto the agenda (macros/tzloop.py `trip`): the terror zone kinds and Lower Kurast
    PACKAGE = 'package'
    TRIP = 'trip'  # a trip to town for room and back through the portal (macros/loop.py TRIP)
    DROP = 'drop'  # one of the loop's items to identify dropped for it, once a game
    TRIPPING = 'tripping'  # a valuable with no room while a trip for room is under way: the trip goes on, no stop
    HOLD = 'hold'  # a valuable on the ground and nothing left to try: the loop stops here, never leaves it
    RECOVER = 'recover'  # the game is left and the loop goes on (macros/loop.py `recover`)
    # The game kept: the leg made again; a goal that stops again is dropped by the agenda after its TRIES (agenda.py
    # `failed`), REPEATS bounds the leg (macros/loop.py)
    KEEP = 'keep'
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
    packaged: bool = False  # a kind tripping by the room package (loop.py `Kind.packaged`) may now, its level known
    terrorized: bool = False  # a Worldstone Shard terrorized an act of this game (agenda.py `Agenda.acts`)
    # The room package of a zone kind is under way in this game (`Loop.tripping`, loop.py `Kind.packaged`)
    tripping: bool = False


@dataclass(frozen=True)
class Beset:
    """The facts of a 'beset' stop (runner.py `_loop_stopped`)."""

    low: bool  # life under the healer's floor (`low_life`)
    again: bool = False  # beset again within BESET_AGAIN_SECONDS of fighting back (loop.py `Loop.beset_again`)
    foe: bool = False  # a hostile in the read near the character (runner.py `_attacker_near`)
    left: str | None = None  # the valuable on the ground (runner.py `valuable_left`)


# Game creations failed in a row (`first`, cause 'lobby') that stop the loop
LOBBY_STOPS = 2
# The player, 2026-10-21 ~13:40: "we have left terrorized act without finishing it => wasted shard" (a super healing
# potion no click took, Travincal 13:37:24; rca/2026-10-21/potion-click-findings.md). True: a pickup stop (pickup.py
# `Missed`) with nothing valuable left never leaves a game: KEEP. False: left as 'other' was
PICKUP_KEEPS = True
# True: in a game whose act a shard terrorized, a stop of a KEEP_GAME cause with nothing valuable left keeps the game
# (the goal given up, the act goes on); the watchdogs, the bounds, the safety and the unknown ('other': exceptions, the
# lost pointer) still leave. False: as before
TERRORIZED_KEEPS = True
KEEP_GAME: frozenset[Cause] = frozenset({'door', 'pickup'})
# 15:31:35.97 on 2026-10-23 (rca/2026-10-23/visit-portal-findings.md): a walk click toward Deckard Cain took the
# character back through its own Town Portal to the River of Flame, and the visit went on there. The visit now stops at
# the first look out of its town (macros/visit.py TOWN_ONLY, cause 'town'). True: the leg is made again from where the
# character is (the agenda's portal back to town, then the visit), the game not left (a shard's act kept). False: as
# 'other' (the game left, the loop on)
LEFT_TOWN_AGAIN = True


def low_life(life: tuple[int, int] | None) -> bool:
    """Whether `life` (points, maximum) is under the healer's critical floor (config.py `HEAL_PRIORITY.floor`, the
    macro's life budget's too); unread counts as low."""
    return life is None or life[1] <= 0 or life[0] < HEAL_PRIORITY.floor / 100 * life[1]


def first(cause: Cause, *, on: bool, dead: bool, beset: Beset | None = None, lobby_fails: int = 0) -> Remedy | None:
    """The rules before the Gheed's swap: by the cause, and a 'beset' stop's `beset` facts. `lobby_fails`: the game
    creations failed in a row, this one counted. None: the swap, then `decide`."""
    if dead:
        # The player, 2026-10-19: "if we died - we MUST not take ANY other actions, no reviving, no save/exits"
        return Remedy.DEAD
    if on and cause == 'beset':
        # The player, 2026-10-19: "Fight back first: fight the attacker, then pick up the valuable; leave only if life
        # gets low (the death rules still win)". Beset again after fighting back: the fight cannot be won
        if beset is None or beset.low or beset.again:
            return Remedy.LEAVE
        if beset.foe or beset.left is not None:
            return Remedy.FIGHT
        return Remedy.LEAVE  # no attacker read and nothing to keep: left as before
    if on and cause == 'hand':
        # Leaving the game for a moved mouse cost two games (2026-10-17 01:28:48); REPEATS bounds it
        return Remedy.AGAIN
    if on and LEFT_TOWN_AGAIN and cause == 'town':
        return Remedy.AGAIN  # nothing was done outside town: the next leg goes back to town first; REPEATS bounds it
    if on and cause == 'stash':
        # The player, 2026-10-18 16:50: "if stash is full - we need to stop loop"
        return Remedy.STOP
    if on and cause == 'zone':
        # A terror zone the loop cannot play (Moo Moo Farm): the game is left and the next zone waited for in the lobby
        # (tzloop.py `zone_wait`), the loop on. Stopped, it stood 30 min until someone looked (03:30:20 on 2026-10-20)
        return Remedy.LEAVE
    if on and cause == 'lobby':
        # A game creation failed: once is tried again (a one-off, 13:02 on 2026-10-18). Again is no lobby: Battle.net
        # dropped the client to the character screen (05:35:30 on 2026-10-20, the Offline tab), where the lobby's
        # clicks and keys went for 5 min. The player reconnects
        return Remedy.STOP if lobby_fails >= LOBBY_STOPS else Remedy.LEAVE
    if on and cause == 'idle':
        # Nothing to play: a game made and left again and again (Battle.net limits game creation). The player,
        # 2026-10-19: "we need to make sure that we don't stuck or die"
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
    if roomy and left is not None and game is not None and stop.tripping:
        # 2026-10-22 22:34: a trip pushed at 22:33:45, the run stood by the valuable again before its portal, and the
        # loop stopped: the trip under way is the answer
        return Remedy.TRIPPING
    if roomy and left is not None and game is not None:
        if stop.packaged:
            return Remedy.PACKAGE
        if stop.trips:
            # The player, 2026-10-18 16:50: "one game can do several trips to the town"
            return Remedy.TRIP
        if not stop.dropped:
            return Remedy.DROP
    if left is not None:
        # The player, 2026-10-17: "you we're killed the game while having valuable pickup on the ground!!! that is
        # the exact thing we want ot avoid"
        return Remedy.HOLD
    if stop.on and PICKUP_KEEPS and stop.cause == 'pickup':
        return Remedy.KEEP  # a potion, gold or a cheap item is worth no game
    if stop.on and TERRORIZED_KEEPS and stop.terrorized and stop.cause in KEEP_GAME:
        return Remedy.KEEP  # the shard's act goes on without the goal
    return Remedy.RECOVER if stop.on else Remedy.NOTHING
