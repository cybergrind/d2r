"""The loot policy: for a valuable on the ground, whether each deciding site takes it now and whether it must not be
left (rca/2026-10-18/arch-level-behaviour.md, Option A). Every site decides by `verdict` since 2026-10-19; the golden
table of what each said before is tests/…/macros/test_lootpolicy.py. Supplies (gold, potions) are the belt's and
gold's rules (pickup.py `choose`, macros/supply.py). Pure.

"We should stop and clear inventory with our designated town routine" (the player, 2026-10-18 17:50): with the KP_6
loop on (`looped`) the press and the sweep hold `NO_ROOM_PLAIN` too; KP_1 by hand moves on from it.
"""

from dataclasses import dataclass

from inventory_tracking.game.records import VALUABLE, Drop
from inventory_tracking.macros.pickmode import MOST, SURE, is_candidate, sure


__all__ = [
    'GUARD',
    'LOOP_HOLDS',
    'NO_ROOM_PLAIN',
    'PRESS',
    'RUN',
    'SIGHTINGS',
    'SITES',
    'SWEEP',
    'Dispute',
    'Verdict',
    'disputed',
    'trip_for',
    'verdict',
]

# The deciding sites (the study's N1-N5), as their log lines name them
PRESS = 'the press'  # macros/pickup.py `pick_up`: a KP_1 press stops ("inventory full") or goes on to its seek step
RUN = 'the level run'  # macros/hunting/choice.py `stay_by`: the level run (the KP_1 run, the loop's) stands by it
SWEEP = 'the sweep'  # macros/hunting/sweep.py `gather`: the sweep stays by it (`held`)
GUARD = 'the guard'  # runner.py `_valuable_left`: the loop does not leave the game with it on the ground
SIGHTINGS = 'the sightings'  # macros/sightings.py `Sightings.update`: remembered until off the ground
SITES = (PRESS, RUN, SWEEP, GUARD, SIGHTINGS)


@dataclass(frozen=True)
class Verdict:
    """What a site does with a drop. `take`: taken now. `hold`: must not be left (stand by, stop, keep the game).
    `why`: for the log. `disputed`: of the `NO_ROOM_PLAIN` class."""

    take: bool
    hold: bool
    why: str
    disputed: bool = False


@dataclass(frozen=True)
class Dispute:
    """A class of drops the sites answered differently by hand, with the question put and the player's ruling."""

    name: str
    stands_by: frozenset[str]
    moves_on: frozenset[str]
    question: str
    ruling: str


# Q1 of rca/2026-10-18/arch-level-behaviour.md §5: a valuable not prized, not filter-shown, no identify candidate, with
# no room (a low rune, a plain gem, a jewel, a magic ring or amulet). Ruled 2026-10-18 17:50 (module text).
NO_ROOM_PLAIN = Dispute(
    name='a plain valuable with no room',
    stands_by=frozenset((RUN, GUARD, SIGHTINGS)),
    moves_on=frozenset((PRESS, SWEEP)),
    question='stand by it, or move on (the guard keeps the game for it either way)?',
    ruling='held in the loop (its town routine makes room), moved on from by hand',
)
LOOP_HOLDS = 'no room, in the loop: held for its town routine (the ruling of 2026-10-18 17:50)'


def disputed(drop: Drop, *, room: bool, shown: bool) -> bool:
    """Whether `drop` is of the `NO_ROOM_PLAIN` class."""
    return drop.kind == VALUABLE and not room and not drop.prized and not shown and not is_candidate(drop)


def kept_by(drop: Drop, mode: str) -> bool:
    """Whether the pickup mode `mode` keeps `drop` (pickmode.py `kept`, one drop)."""
    return sure(drop) if mode == SURE else True


def _shard_taken(drop: Drop) -> bool:
    """A Worldstone Shard is taken whatever its stack (macros/actloop.py SHARD_ALWAYS_PICKED, 2026-10-22)."""
    from inventory_tracking.macros import actloop  # actloop's imports reach the pickup, which imports this

    return actloop.SHARD_ALWAYS_PICKED and drop.txt in actloop.SHARDS


def verdict(
    drop: Drop,
    site: str,
    *,
    room: bool,
    shown: bool,
    mode: str = MOST,
    sold_full: bool = False,
    shunned: bool = False,
    given_up: bool = False,
    looped: bool = False,
) -> Verdict:
    """What `site` (one of SITES) does with `drop`.

    - `room`: inventory room for it (True unread). `shown`: taken only because the loot filter shows it.
    - `mode`: the pickup mode the loot was filtered by. `sold_full`: its stash stack is full.
    - `shunned`: the pickup step leaves it alone a while; it still holds the guard and the sightings.
    - `given_up`: the site's own give-up (run: `waived`/spent tries; sweep: `GATHER_TRIES`). The press has none; the
      guard and the sightings ignore give-ups (the study's §2.2).
    - `looped`: the KP_6 loop is on: the press and the sweep hold `NO_ROOM_PLAIN` too.

    Distance is the site's own filter, asked before this."""
    if drop.kind != VALUABLE:
        return Verdict(False, False, 'a supply: the belt and gold rules')
    if not kept_by(drop, mode):
        return Verdict(False, False, f'not of the {mode} pickup')
    if sold_full and not _shard_taken(drop):
        return Verdict(False, False, 'its stash stack is full')
    pending = disputed(drop, room=room, shown=shown)
    take = room and not shunned and (site == PRESS or not given_up)  # the press keeps no give-ups
    if site in (GUARD, SIGHTINGS):
        if is_candidate(drop):
            return Verdict(take, False, 'an identify candidate: no game is kept for it', pending)
        return Verdict(take, True, 'a valuable on the ground', pending)
    if shunned:
        return Verdict(False, False, 'left alone a while', pending)
    if site == PRESS:
        if room:
            return Verdict(True, False, 'room for it: taken', pending)
        if drop.prized:
            return Verdict(False, True, 'prized, no room: the press stops', pending)
        if looped and pending:
            return Verdict(False, True, LOOP_HOLDS, pending)
        return Verdict(False, False, 'not prized, no room: the press goes on', pending)
    if given_up:
        return Verdict(False, False, 'given up', pending)
    if site == RUN:
        if room:
            return Verdict(True, False, 'room for it: a side goal', pending)
        if shown:
            return Verdict(False, False, 'filter-shown gear, no room: the run goes on', pending)
        return Verdict(False, True, 'no room: the run stands by it', pending)
    if site == SWEEP:
        if room:
            return Verdict(True, True, 'room for it: the sweep stays by it', pending)
        if drop.prized:
            return Verdict(False, True, 'prized, no room: the sweep stays by it', pending)
        if looped and pending:
            return Verdict(False, True, LOOP_HOLDS, pending)
        return Verdict(False, False, 'not prized, no room: the sweep goes on', pending)
    raise ValueError(f'no such site: {site}')


def trip_for(drop: Drop, *, shown: bool) -> bool:
    """Whether the shared no-room routine (macros/running/room.py) goes to town for `drop` once the cube made no room
    for it: what the guard keeps a game for, in the loop and by hand alike (the player, 2026-10-19: "EVERY loop and
    activity should have the same routines"): every valuable of the pickup level but an identify candidate."""
    return verdict(drop, GUARD, room=False, shown=shown, looped=True).hold
