"""The loot policy: for a valuable on the ground, whether it is taken now and whether it must not be left, as each place
that decides it answers today (rca/2026-10-18/arch-level-behaviour.md, Option A, steps 1 and 2).

"Is this worth taking" and "must we not leave it" are answered at several sites, and they disagree (§2.1 of the
study): the KP_1 press stops for a valuable with no room only when it is prized (macros/pickup.py `stops_for`); a level
run stands by one the loot filter alone does not show (macros/hunt.py `stands_by`); the sweep stays by one that is
prized or has room (hunt.py `holds`); the loop's guard keeps the game, and its sightings remember, every one that is
no identify candidate (runner.py `_valuable_left`, macros/sightings.py: pickmode.py `is_candidate`). `verdict` gives
each site's answer from explicit facts, so the sites can be switched to one rule later, one at a time (step 4), with a
test of what each said before (tests/…/macros/test_lootpolicy.py, a golden table over every site's own predicates).

The supplies (gold, potions) are not here: the belt's and gold's rules (pickup.py `choose`, macros/supply.py) decide
them, and `verdict` calls them neither taken nor held.

Shadow mode (step 2): the sites of pickup.py and hunt.py ask `SHADOW.check` beside their own decision; a site that
decided otherwise than its verdict, or a drop of the once disputed class (`NO_ROOM_PLAIN`), is said once a unit a game.
Nothing here reads the game.

Step 4 (the player's ruling of Q1, 2026-10-18 17:50: "we should stop and clear inventory with our designated town
routine"): with the KP_6 loop on (`looped`) the press and the sweep decide `NO_ROOM_PLAIN` by `verdict(...).hold`, as
the level run, the guard and the sightings already did: the valuable is held, and the loop's room rules (runner.py
`_loop_stopped`: the cube, then a trip to town and back through the portal) make the room to take it. KP_1 by hand is
as before: the press and the sweep move on from it.
"""

from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.macros.pickmode import REGULAR, SURE, TRADE, is_candidate, sure, traded
from inventory_tracking.macros.world import VALUABLE, Drop


__all__ = [
    'GUARD',
    'LOOP_HOLDS',
    'NO_ROOM_PLAIN',
    'PRESS',
    'RUN',
    'SHADOW',
    'SIGHTINGS',
    'SITES',
    'SWEEP',
    'Dispute',
    'Shadow',
    'Verdict',
    'disputed',
    'verdict',
]

# The sites that ask (the study's N1-N5), named as their own log lines name them
PRESS = 'the press'  # macros/pickup.py `pick_up`: a KP_1 press stops ("inventory full") or goes on to its seek step
RUN = 'the level run'  # macros/hunt.py `Hunter.stay_by`: the level run (the KP_1 run, the loop's) stands by it
SWEEP = 'the sweep'  # macros/hunt.py `Hunter.gather`: the sweep stays by it (`held`)
GUARD = 'the guard'  # runner.py `_valuable_left`: the loop does not leave the game with it on the ground
SIGHTINGS = 'the sightings'  # macros/sightings.py `Sightings.update`: remembered until off the ground
SITES = (PRESS, RUN, SWEEP, GUARD, SIGHTINGS)
SAID_MOST = 500  # (site, unit) pairs the shadow remembers saying in a game; cleared past it


@dataclass(frozen=True)
class Verdict:
    """What a site does with a drop. `take`: a mover takes it now (pickup.py `choose`'s valuables: room for it, not
    left alone a while, not given up by the site). `hold`: the site's "must not leave it" (stand by it, stop for it,
    keep the game for it). `why`: in a few words, for the log. `disputed`: of the class the sites disagreed on
    (`NO_ROOM_PLAIN`, ruled 2026-10-18 17:50: held in the loop, moved on from by hand)."""

    take: bool
    hold: bool
    why: str
    disputed: bool = False


@dataclass(frozen=True)
class Dispute:
    """A class of drops the sites answered differently: which of them stand by it with KP_1 by hand and which move on,
    the question put to the player and the player's ruling (every site holds it in the KP_6 loop)."""

    name: str
    stands_by: frozenset[str]
    moves_on: frozenset[str]
    question: str
    ruling: str


# Q1 of rca/2026-10-18/arch-level-behaviour.md §5. A valuable that is not prized (world.py `prized`: below the marks),
# not taken only because the loot filter shows it (`Loot.shown`) and no identify candidate (pickmode.py
# `is_candidate`), with no room for it: a low rune El-Ral (taken from r01, marked from Io), a chipped or plain gem, a
# jewel or a magic ring or amulet (REGULAR only: the sure mode keeps rings and amulets only when rare, set or unique).
# By hand the press warns and goes on, and the sweep sweeps on; a level run stands by it. Ruled by the player,
# 2026-10-18 17:50: "we should stop and clear inventory with our designated town routine": in the KP_6 loop every site
# holds it (`verdict`'s `looped`), and the loop's room rules make the room (the cube, then a trip to town and back
# through the portal; the Lower Kurast loop has no trip yet: the cube, an item to identify dropped, the stop for the
# player). Outside the loop nothing changed. Today's cases (16:34-17:55): a set Amulet (16:59:14) and a magic Jewel
# (17:26:50) on Catacombs Level 4, both stood by by the level run and taken after the cube made room.
NO_ROOM_PLAIN = Dispute(
    name='a plain valuable with no room',
    stands_by=frozenset((RUN, GUARD, SIGHTINGS)),
    moves_on=frozenset((PRESS, SWEEP)),
    question='stand by it, or move on (the guard keeps the game for it either way)?',
    ruling='held in the loop (its town routine makes room), moved on from by hand',
)
LOOP_HOLDS = 'no room, in the loop: held for its town routine (the ruling of 2026-10-18 17:50)'


def disputed(drop: Drop, *, room: bool, shown: bool) -> bool:
    """Whether `drop` is of the disputed class (`NO_ROOM_PLAIN`): a valuable, not prized, not `shown`, no identify
    candidate, and no `room` for it."""
    return drop.kind == VALUABLE and not room and not drop.prized and not shown and not is_candidate(drop)


def kept_by(drop: Drop, mode: str) -> bool:
    """Whether the pickup mode `mode` keeps `drop` (pickmode.py `kept`, one drop)."""
    if mode == SURE:
        return sure(drop)
    if mode == TRADE:
        return traded(drop)
    return True


def verdict(
    drop: Drop,
    site: str,
    *,
    room: bool,
    shown: bool,
    mode: str = REGULAR,
    sold_full: bool = False,
    shunned: bool = False,
    given_up: bool = False,
    looped: bool = False,
) -> Verdict:
    """What `site` (one of SITES) does today with `drop`, of the facts:

    - `room`: the inventory has room for it (world.py `has_room`; True unread).
    - `shown`: taken only because the loot filter shows it (`drop.unit_id in loot.shown`).
    - `mode`: the pickup mode the loot was filtered by (runner.py `_picked`: the loop's, REGULAR with the loop off).
    - `sold_full`: its stack in the stash is full (loop.py `sold_full`): not picked up.
    - `shunned`: the pickup step leaves it alone a while (pickup.py `SHUNNED`); the guard and the sightings read the
      ground without it (`_valuable_left`), so it holds them all the same.
    - `given_up`: the site's own give-up of it: the level run's `waived` (a press went on from it) for its stand and
      its spent tries for its take, the sweep's spent tries (`GATHER_TRIES`). The press has none; the guard and the
      sightings ignore every give-up (the study's §2.2).
    - `looped`: the KP_6 loop is on: the press and the sweep hold `NO_ROOM_PLAIN` too (the player's ruling of Q1).

    How near it lies is the site's own filter (the run's PICK_NEAR, the sweep's HOLD_SIGHT), asked before this."""
    if drop.kind != VALUABLE:
        return Verdict(False, False, 'a supply: the belt and gold rules')
    if not kept_by(drop, mode):
        return Verdict(False, False, f'not of the {mode} pickup')
    if sold_full:
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


def word(hold: bool) -> str:
    return 'hold' if hold else 'leave'


class Shadow:
    """The shadow checks of one process (step 2 of the study): `check` is asked by a site beside its own decision and
    logs, once a site and unit a game, a decision other than its verdict, or a drop of the once disputed class (the
    count of Q1's cases the loop meets, and what each site did). It never raises: a check that fails is said once and
    the site goes on."""

    def __init__(self) -> None:
        self.game: object = None
        self.said: set[tuple[str, int]] = set()
        self.failed = False

    def check(self, site: str, drop: Drop, says: bool, *, game: object, **facts) -> None:
        """`says`: the site's own "must not leave it" for `drop`; `game`: the loot's (`Loot.game`); `facts`: those of
        `verdict`."""
        try:
            if game != self.game:
                self.game, self.said = game, set()
            if drop.kind != VALUABLE or (site, drop.unit_id) in self.said:
                return
            found = verdict(drop, site, **facts)
            if found.hold == says and not found.disputed:
                return
            if len(self.said) > SAID_MOST:
                self.said.clear()
            self.said.add((site, drop.unit_id))
            if found.hold != says:
                LOG.info(
                    'Macro: lootpolicy: %s %s (unit %d): site says %s, policy says %s (%s)',
                    site, drop.label, drop.unit_id, word(says), word(found.hold), found.why,
                )  # fmt: skip
            else:
                LOG.info(
                    'Macro: lootpolicy: %s %s (unit %d): site says %s; %s, %s',
                    site, drop.label, drop.unit_id, word(says), NO_ROOM_PLAIN.name, NO_ROOM_PLAIN.ruling,
                )  # fmt: skip
        except Exception as exc:
            if not self.failed:
                self.failed = True
                LOG.info('Macro: lootpolicy: the shadow check failed (%r); the site decides alone', exc)


SHADOW = Shadow()
