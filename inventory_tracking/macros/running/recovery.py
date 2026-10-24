"""The KP_6 loop's stops and recoveries: a leg's stop classified and judged (macros/stops.py), the Gheed's swap, the
beset facts. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import math
import time
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Loot, Pack
from inventory_tracking.macros.actuator import Abort, Cause, Hand
from inventory_tracking.macros.agenda import SWAP_GOALS
from inventory_tracking.macros.bossledger import Boss, game_key, said, stop_line
from inventory_tracking.macros.charms import gheeds
from inventory_tracking.macros.hunting.base import SIGHT, hostiles
from inventory_tracking.macros.loop import CHOOSE, NO_PROGRESS_SECONDS, PICK
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.routines import Dead
from inventory_tracking.macros.safety import return_refused
from inventory_tracking.macros.stops import Beset, Remedy, Stopped, decide, first, low_life
from inventory_tracking.macros.tzloop import (
    bosses_alive as tz_bosses_alive,
    danger_trip as tz_danger_trip,
    gheeds_swap as tz_gheeds_swap,
    levels_owed as tz_levels_owed,
    owed as tz_owed,
    trip as tz_trip,
)
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


# The coordinator's rulings of 2026-10-22, the player's words: "we need to kill all bosses, no exceptions to that";
# recoveries: "yes, should try"; "we must not die". True: a recovery that would leave a zone game (stops.py RECOVER:
# the still watchdog, the repeat guard, a Town Portal or click that failed; LEAVE for a 'beset' stop) asks the game's
# boss ledger first (tzloop.py `bosses_alive`: macros/bossledger.py, its scope's bosses alive):
# - none alive: as before;
# - life low or unread (beset): survival first, the game left at once as before, the bosses named in the line;
# - beset otherwise (the fight back lost, or no attacker read): clear of it by the danger package (tzloop.py
#   `danger_trip`: Town Portal cast with no fight posted, the town visit, back through the portal), BOSS_KEEPS times
#   for a boss (`BossLedger.tried`, kept in the tracker's file-backed book), then the loop stops where it is;
# - any other: the game kept and the leg made again BOSS_KEEPS times for a boss, then the loop stops where it is,
#   naming the bosses (never left quietly); the game's time cap (loop.py `overdue`) stops at once (a kept leg would be
#   over the cap again at the next look).
# rca/2026-10-22/boss-audit-findings.md §4 cause 7: every recovery left the game, 177 games with a boss alive. False:
# as before
BOSS_RECOVERY = True
BOSS_KEEPS = 2
# The shard acts' levels owed (tzloop.py ACT_OWED, 2026-10-22) hold the game as a live boss does: kept BOSS_KEEPS times
# (counted on the agenda under this key: the game's record), then the loop stops where it is, naming them
OWED_KEY = ('levels owed',)
# The player, 2026-10-23: "make sure that we don't save/exit and waste the shards"; "we absolutely must preserve top
# items" (rca/2026-10-23/shard-exit-audit.md). True:
# - a game a Worldstone Shard terrorized (`Agenda.acts`, the game's record's) with no plan read (a restart's take-up
#   sets none until the next leg's `zone_of`, so `levels_owed` is empty) is held as its owed levels are (BOSS_KEEPS
#   keeps, then the loop stops in place): a recovery in that window left the shard game;
# - a 'beset' stop with life not low (the fight back lost) and a valuable left (`valuable_left`: in sight or
#   remembered, macros/sightings.py) is held as for a boss: clear of it by the danger package, never a leave;
# - a 'zone' stop (no playable excursion) in a game held so stops the loop in place instead of leaving it.
# Life low (beset) still leaves at once: survival first. False: as before
SHARD_HOLDS = True
UNPLANNED = 'the shard acts {acts} not planned yet'
VALUABLE_KEY = ('valuable left',)


def classify(why: object) -> Cause:
    """The cause of the stop `why` (actuator.py `Cause`): the one its raise named, else by its type; a room stop and
    the watchdog's stand always name theirs."""
    if isinstance(why, Abort) and why.cause is not None:
        return why.cause
    if isinstance(why, Hand):
        return 'hand'
    if isinstance(why, Refused):
        return 'refused'
    return 'other'


def _loop_stopped(self: MacroRunner, why: object) -> None:
    """A leg's stop: the loop leaves the game and goes on (macros/loop.py `recover`), or ends, saying why; the
    rules are macros/stops.py's. Under the lock or from the run's thread. A stand by a valuable is answered by it
    (watch.py `stood_after_cube` acts only on a later one)."""
    self.stand_answered = time.monotonic()
    dead = isinstance(why, Dead) or self._dead()
    cause = classify(why)
    seen = self.loop.seen[0] if self.loop.seen is not None else None
    beset = self._beset_facts(seen) if cause == 'beset' and self.loop.on and not dead and seen else None
    if cause == 'lobby':
        self.loop.lobby_fails += 1  # made afresh by a game made (loop.py `next_game`)
    early = first(cause, on=self.loop.on, dead=dead, beset=beset, lobby_fails=self.loop.lobby_fails)
    if early is Remedy.DEAD:
        self.attack_mode = False
        self._stop_loop(why if isinstance(why, Dead) else Dead(f'the character is dead ({why})'))
        return
    if early is Remedy.FIGHT and beset is not None and seen:
        self.loop.fight_back_due(seen)
        LOG.info('Macro: loop: %s: the attacker is fought back%s; the game is not left', why,
                 f', then {beset.left} is picked up' if beset.left is not None else '')  # fmt: skip
        self._show([f'Loop: {why}: fighting back'])
        return
    if early is Remedy.LEAVE:
        low = beset is None or beset.low
        # SHARD_HOLDS: the fight back lost with life not low; what the beset facts skip is read here
        left = self.valuable_left() if SHARD_HOLDS and cause == 'beset' and not low else None
        if cause == 'beset' and _boss_recovery(self, why, danger=True, low=low, left=left):
            return
        if SHARD_HOLDS and cause == 'zone' and (held := _held(self)) is not None:
            self._stop_loop(stop_line([], f'{why}: the game is not left', held))
            return
        if beset is not None:
            LOG.info('Macro: loop: beset with %s', 'life low' if beset.low else 'the fight back lost' if beset.again
                     else 'no attacker read and nothing on the ground')  # fmt: skip
        # The pause after recoveries is not stood in a battle level (loop.py `leg`)
        if self.loop.recover(why, time.monotonic()):
            LOG.info('Macro: loop: %s: the game is left at once and the loop goes on', why)
            self._show([f'Loop: {why}: leaving the game'])
        else:
            self._stop_loop(why)
        return
    if early is Remedy.AGAIN:
        LOG.info('Macro: loop: %s: the leg is made again', why)
        return
    if early is Remedy.STOP:
        self._stop_loop(why)
        return
    loop = self.loop
    left = self.valuable_left() if loop.on else None
    game = loop.seen[0] if loop.seen is not None else None
    # A refused click names its charm (macros/pickup.py `Refused`): the ground's first valuable may be another
    if self._gheeds_swap(why, why.drop.label if isinstance(why, Refused) and loop.on else left, game):
        return
    may_trip = loop.may_trip(game) and loop.carrying
    terrorized = bool(loop.kind.agenda and loop.agenda.acts)  # a shard's act in this game (actloop.py `use_shard`)
    remedy = decide(
        Stopped(
            cause, loop.on, left, game,
            fetched=loop.fetch_again == game,
            cubed=loop.cube_tried(game),
            dropped=loop.dropped == game,
            trips=loop.kind.trips and may_trip,
            packaged=loop.kind.packaged and may_trip and self.area_seen is not None,
            terrorized=terrorized,
            tripping=bool(loop.kind.packaged) and game is not None and loop.tripping(game),
        )
    )  # fmt: skip
    if remedy is Remedy.FETCH:
        loop.fetch_again = game
        LOG.info('Macro: loop: %s; %s lies on the ground: the leg is made again', why, left)
    elif remedy is Remedy.CUBE:
        loop.cube_try(game)
        LOG.info('Macro: loop: %s; %s lies on the ground: room is made in the cube', why, left)
    elif remedy is Remedy.PACKAGE:
        assert game is not None
        assert self.area_seen is not None
        tz_trip(loop, game, self.area_seen)
        LOG.info("Macro: loop: %s; %s lies on the ground: a trip to town for room (the agenda's package)", why, left)
    elif remedy is Remedy.TRIP:
        loop.trip_due = True
        LOG.info('Macro: loop: %s; %s lies on the ground: a trip to town for room', why, left)
    elif remedy is Remedy.DROP:
        loop.drop_room, loop.dropped = True, game
        LOG.info('Macro: loop: %s; %s lies on the ground: an item to identify is dropped for it', why, left)
    elif remedy is Remedy.KEEP:
        # The watch reads it (d2-loop-watch logwords.py EVENT, NOW)
        LOG.info('Macro: loop: %s: the game is kept (%s): the leg is made again', why,
                 f'act {", ".join(map(str, sorted(loop.agenda.acts)))} terrorized by a shard' if terrorized
                 else 'nothing valuable lies on the ground')  # fmt: skip
        self._show([f'Loop: {why}: game kept'])
    elif remedy is Remedy.TRIPPING:
        LOG.info('Macro: loop: %s; %s lies on the ground: the trip to town for room under way goes on', why, left)
    elif remedy is Remedy.HOLD:
        self._stop_loop(f'{why}; {left} lies on the ground: the loop stops here')
    elif remedy is Remedy.RECOVER:
        if _boss_recovery(self, why, danger=False):
            return
        if loop.recover(why, time.monotonic()):
            LOG.info('Macro: loop: %s: the game is left and the loop goes on', why)
            self._show([f'Loop: {why}: leaving the game'])
        else:
            self._stop_loop(why)


def _unplanned(self: MacroRunner) -> str | None:
    """SHARD_HOLDS: the shard acts of this game said when the agenda has no plan read to judge their levels by
    (`UNPLANNED`); None otherwise."""
    agenda = self.loop.agenda
    if not SHARD_HOLDS or not agenda.acts or isinstance(agenda.plan, Itinerary):
        return None
    return UNPLANNED.format(acts=list(agenda.acts))


def _this_game(self: MacroRunner) -> str | None:
    """The game the loop is in when the agenda is begun for it (an agenda kind, the loop on); None otherwise."""
    loop = self.loop
    if not loop.on or not loop.kind.agenda:
        return None
    game = loop.seen[0] if loop.seen is not None else None
    if game is None or loop.agenda.bosses.game != game_key(loop.game_id or game):
        return None
    return game


def _held(self: MacroRunner) -> str | None:
    """SHARD_HOLDS: what holds this game against a leave, said: its owed bosses and shard levels (tzloop.py `owed`),
    its shard acts with no plan read (`_unplanned`), a valuable left (`valuable_left`); None with none."""
    if _this_game(self) is None:
        return None
    if (held := tz_owed(self.loop.agenda) or _unplanned(self)) is not None:
        return held
    left = self.valuable_left()
    return f'{left} lies on the ground' if left is not None else None


def _boss_recovery(self: MacroRunner, why: object, *, danger: bool, low: bool = False, left: str | None = None) -> bool:
    """BOSS_RECOVERY: whether the recovery for `why` is answered for the bosses alive, the shard acts' levels owed (or
    not planned yet: SHARD_HOLDS) or, `left`, a valuable on the ground (said, kept, packaged or the loop stopped);
    False to leave the game as before (none, the switch off, the loop off, no agenda kind; or `low`: the character's
    life first, what holds the game named)."""
    loop = self.loop
    if not BOSS_RECOVERY:
        return False
    game = _this_game(self)
    if game is None:
        return False  # out of a game, or the agenda not begun for this one: its plan is another game's
    alive = tz_bosses_alive(loop.agenda)
    unplanned = _unplanned(self)
    levels = bool(tz_levels_owed(loop.agenda)) or unplanned is not None
    valuable = SHARD_HOLDS and left is not None and not alive and not levels
    if not alive and not levels and not valuable:
        return False
    held = tz_owed(loop.agenda) or unplanned or (f'{left} lies on the ground' if valuable else None) or said(alive)
    if danger and low:
        # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
        LOG.info("Macro: loop: %s: the game is left for the character's life with %s", why, held)
        return False

    def stop(text: str) -> None:
        self._stop_loop(stop_line(alive, text, held if levels or valuable else None))

    now = time.monotonic()
    if game is not None and loop.no_progress(game, now):
        # Owed levels or bosses: the game is cut by no progress, not by its clock (loop.py NO_PROGRESS_SECONDS)
        stop(f'{why}: no progress for {NO_PROGRESS_SECONDS:.0f} s')
        return True
    fresh: list[Boss] = [boss for boss in alive if boss.tries < BOSS_KEEPS]
    key = OWED_KEY if levels else VALUABLE_KEY
    owed_tries = loop.agenda.failures[key]
    if not fresh and (not (levels or valuable) or owed_tries >= BOSS_KEEPS):
        stop(f'{why}: tried {BOSS_KEEPS} times for them, the game is not left')
        return True
    loop.agenda.bosses.tried(fresh)
    if levels or valuable:
        loop.agenda.failures[key] += 1
    tries = max([boss.tries + 1 for boss in fresh] + ([owed_tries + 1] if levels or valuable else []))
    if danger:
        area = self.area_seen
        if area is None:
            stop(f'{why}: no level read to come back to, the game is not left')
            return True
        tz_danger_trip(loop, game, area)
        # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
        LOG.info('Macro: loop: %s: clear of it by the Town Portal, the town visit, back for %s (try %d of %d): this '
                 'game is kept', why, held, tries, BOSS_KEEPS)  # fmt: skip
        self._show([f'Loop: {why}: to town and back for the bosses'])
        return True
    # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
    LOG.info('Macro: loop: %s: this game is kept for %s (try %d of %d): the leg is made again', why, held,
             tries, BOSS_KEEPS)  # fmt: skip
    self._show([f'Loop: {why}: game kept for the bosses'])
    return True


def back_for_bosses(self: MacroRunner, loot: Loot | None) -> str | None:
    """At a beset recovery's portal return, after the town visit (macros/tzloop.py `perform`, `Loop.danger_return`):
    None to go back through the portal for the bosses alive (macros/safety.py RETURN_GATE `return_refused`: life and
    potions restocked, no veto at the last danger pricing), else the stop line naming them, for the loop to stop in
    town. None with no boss alive (SHARD_HOLDS: every danger return is gated), the loop off, BOSS_RECOVERY off or
    no hunt. `loot`: the life and belt read now."""
    loop = self.loop
    if not BOSS_RECOVERY or not loop.on or not loop.kind.agenda or self.hunter is None:
        return None
    alive = tz_bosses_alive(loop.agenda)
    # SHARD_HOLDS: a danger trip made for the shard acts' levels or a valuable asks the safety's gate as for a boss
    held = (tz_owed(loop.agenda) or _unplanned(self) or 'what the game holds') if SHARD_HOLDS and not alive else None
    if not alive and held is None:
        return None
    refused = return_refused(loot, self.hunter.safety.decision)
    if refused is None:
        LOG.info('Macro: loop: back through the portal for %s: the safety allows it', held or said(alive))
        return None
    return stop_line(alive, f'not back through the portal: {refused}', held)


def _field_trip(self: MacroRunner, label: str) -> bool:
    """The room rules' trip to town for a field item on the ground the cube can make no room for (loot/api.py
    `Field._room_for`, FIELD_AT_ONCE; the player, 2026-10-20 ~14:58: "if we have no room for optimization to keep
    picking up items - we need to do town routine"), as `_loop_stopped` makes it for a valuable: the agenda's room
    package, else the trip and back through the portal. Bounded as theirs (`Loop.may_trip`: TRIPS_A_GAME, the last
    trip made room; something a visit takes away), asked once an item a game and only in the quiet (no hostile within
    SIGHT: no Town Portal in a fight). The level run is ended for it as the stand's rules end it (watch.py
    `stood_after_cube`, the stand answered). Whether a trip is due."""
    with self.lock:
        loop = self.loop
        game = loop.seen[0] if loop.seen is not None else None
        if not loop.on or game is None:
            return False
        if not (loop.may_trip(game) and loop.carrying):
            LOG.info('Macro: loop: %s lies on the ground with no room in the inventory or the cube: no trip may be '
                     'made', label)  # fmt: skip
            return False
        if loop.kind.packaged and self.area_seen is not None:
            tz_trip(loop, game, self.area_seen)
            how = "the agenda's package"
        elif loop.kind.trips:
            loop.trip_due = True
            how = 'and back through the portal'
        else:
            return False
        LOG.info('Macro: loop: %s lies on the ground with no room in the inventory or the cube: a trip to town for '
                 'room (%s)', label, how)  # fmt: skip
        self.stand_answered = time.monotonic()  # a stand by it is answered: `stood_after_cube` stays the backstop
        self.attack_mode = False
        if self.working:
            self.cancelled.set()
        return True


def _stop_loop(self: MacroRunner, why: object) -> None:
    """The loop off by itself, saying why (the watch tools read the line: d2-loop-watch logwords.py STOPPED). The
    stand guard is armed (macros/guard.py): a stop of the loop's own is never a stand under attack; never for a death
    (`Dead`), when nothing more is pressed."""
    self.loop.stop()
    LOG.info('Macro: loop stopped: %s', why)
    self._show([f'Loop stopped: {why}'])
    self._guard_arm(why)


def _gheeds_swap(self: MacroRunner, why: object, left: str | None, game: str | None) -> bool:
    """Whether the stop `why` is the Gheed's swap's (macros/charms.py; the player, 2026-10-18: "picking up another
    gheed ... put our own gheed into SHARED tab"): a unique Grand Charm on the ground in the Andariel loop with the
    player's Gheed's Fortune carried, whatever the stop's words; once a game, before every room rule. No room: the
    cube first, then the swap all the same. The player's stashed, the new one not taken: theirs back (`CHOOSE`).
    An agenda kind's swap is a package (tzloop.py `gheeds_swap`, 2026-10-19): while it is on the stack it goes on."""
    loop = self.loop
    if left is None or 'Unique Grand Charm' not in left or not loop.kind.swaps_gheeds or game is None:
        return False
    swapping = loop.kind.agenda and loop.agenda.holds(SWAP_GOALS)
    if loop.parked is not None:
        if loop.gheed != PICK:
            return swapping
        loop.gheed = CHOOSE
        LOG.info("Macro: charms: %s; %s is still not taken with the player's Gheed's Fortune on shared page %s: "
                 'to town for theirs', why, left, loop.parked.page)  # fmt: skip
        return True
    if swapping:
        return True  # pushed already, not made yet
    if loop.swap == game or loop.own is None:
        return False
    pack = self.carried_now()
    ours = gheeds(pack, loop.own) if pack is not None else None
    if pack is None or ours is None:
        return False
    if not pack.inventory.has_room(ours.size):
        if not loop.cube_tried(game):
            # Room first, in the cube
            loop.cube_try(game)
            LOG.info("Macro: charms: %s; %s lies on the ground, the player's Gheed's Fortune carried, and no %d x "
                     '%d free: room is made in the cube first', why, left, *ours.size)  # fmt: skip
            return True
        # The cube tried: the swap all the same (the player, 2026-10-18: "refused grand charm - should cause a
        # trip")
        LOG.info("Macro: charms: %s lies on the ground, the player's Gheed's Fortune carried, no %d x %d free and "
                 "the cube tried: the swap all the same, the player's block takes the new one", left,
                 *ours.size)  # fmt: skip
    if loop.kind.agenda:
        if self.area_seen is None:
            return False
        tz_gheeds_swap(loop, game, self.area_seen)
    else:
        loop.swap_due = True
    LOG.info("Macro: charms: %s; %s with the player's Gheed's Fortune carried at (%d, %d) and room for another: "
             'the swap is due', why, left, ours.x, ours.y)  # fmt: skip
    return True


def _carry_one(self: MacroRunner, refused: Refused) -> bool:
    """A unique Grand Charm refused for the carried Gheed's Fortune (macros/pickup.py `Refused`) outside the loop's
    own routine: whether the swap is due for it (`_gheeds_swap`); the run stops for it then. Loop off or no swap:
    False, the run's own rules go on."""
    with self.lock:
        if not self.loop.on:
            return False
        game = self.loop.seen[0] if self.loop.seen is not None else None
        return self._gheeds_swap(refused, refused.drop.label, game)


def _forget_given_up(self: MacroRunner) -> None:
    """The level run's give-up memory cleared (hunting/choice.py `forget_given_up`): the Gheed's swap's
    GHEED_STASH."""
    if self.hunter is not None:
        self.hunter.forget_given_up()


def _beset_facts(self: MacroRunner, game: str) -> Beset:
    """The facts a 'beset' stop in `game` is judged by (macros/stops.py `first`): the last poll's life, a fight back
    just before, what lies on the ground and whether an attacker is in the read."""
    low = low_life(self.life_seen)
    again = self.loop.beset_again(game, time.monotonic())
    if low or again:
        return Beset(low, again)
    left = self.valuable_left()
    return Beset(low, again, foe=self.attacker_near(), left=left)


def _attacker_near(self: MacroRunner) -> bool:
    """Whether a hostile the hunt strikes stands within its SIGHT of the character now; False unread."""
    try:
        table = one_unit_table(self.source.capture)
        if table is None:
            return False
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
        try:
            world = memory.world()
        finally:
            memory.close()
    except Exception as exc:
        LOG.info('Macro: the hostiles could not be read (%s)', exc)
        return False
    here = world.player
    if here is None:
        return False
    return any(math.dist((m.x, m.y), (here.x, here.y)) <= SIGHT for m in hostiles(world))


def _carried_now(self: MacroRunner) -> Pack | None:
    """The carried inventory as read now (a GameMemory of its own, as `_valuable_left`); None unread."""
    try:
        table = one_unit_table(self.source.capture)
        if table is None:
            return None
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
        try:
            return memory.carried()
        finally:
            memory.close()
    except Exception as exc:
        LOG.info('Macro: the inventory could not be read (%s)', exc)
        return None
