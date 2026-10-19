"""The KP_6 loop's stops and recoveries: a leg's stop classified and judged (macros/stops.py), the Gheed's swap, the
beset facts. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import math
import time
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Pack
from inventory_tracking.macros.actuator import Abort, Cause, Hand
from inventory_tracking.macros.charms import gheeds
from inventory_tracking.macros.hunting.base import SIGHT, hostiles
from inventory_tracking.macros.loop import CHOOSE, PICK
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.routines import Dead
from inventory_tracking.macros.stops import Beset, Remedy, Stopped, decide, first, low_life
from inventory_tracking.macros.tzloop import trip as tz_trip
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


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
    rules are macros/stops.py's. Under the lock or from the run's thread."""
    dead = isinstance(why, Dead) or self._dead()
    cause = classify(why)
    seen = self.loop.seen[0] if self.loop.seen is not None else None
    beset = self._beset_facts(seen) if cause == 'beset' and self.loop.on and not dead and seen else None
    early = first(cause, on=self.loop.on, dead=dead, beset=beset)
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
    remedy = decide(
        Stopped(
            cause, loop.on, left, game,
            fetched=loop.fetch_again == game,
            cubed=loop.room_tried == game,
            dropped=loop.dropped == game,
            trips=loop.kind.trips and may_trip,
            tz_trips=loop.kind.agenda and may_trip and self.area_seen is not None,
        )
    )  # fmt: skip
    if remedy is Remedy.FETCH:
        loop.fetch_again = game
        LOG.info('Macro: loop: %s; %s lies on the ground: the leg is made again', why, left)
    elif remedy is Remedy.CUBE:
        loop.make_room, loop.room_tried = True, game
        LOG.info('Macro: loop: %s; %s lies on the ground: room is made in the cube', why, left)
    elif remedy is Remedy.TZ_TRIP:
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
    elif remedy is Remedy.HOLD:
        self._stop_loop(f'{why}; {left} lies on the ground: the loop stops here')
    elif remedy is Remedy.RECOVER:
        if loop.recover(why, time.monotonic()):
            LOG.info('Macro: loop: %s: the game is left and the loop goes on', why)
            self._show([f'Loop: {why}: leaving the game'])
        else:
            self._stop_loop(why)


def _stop_loop(self: MacroRunner, why: object) -> None:
    """The loop off by itself, saying why (the watch tools read the line: d2-loop-watch logwords.py STOPPED)."""
    self.loop.stop()
    LOG.info('Macro: loop stopped: %s', why)
    self._show([f'Loop stopped: {why}'])


def _gheeds_swap(self: MacroRunner, why: object, left: str | None, game: str | None) -> bool:
    """Whether the stop `why` is the Gheed's swap's (macros/charms.py; the player, 2026-10-18: "picking up another
    gheed ... put our own gheed into SHARED tab"): a unique Grand Charm on the ground in the Andariel loop with the
    player's Gheed's Fortune carried, whatever the stop's words; once a game, before every room rule. No room: the
    cube first, then the swap all the same. The player's stashed, the new one not taken: theirs back (`CHOOSE`)."""
    loop = self.loop
    if left is None or 'Unique Grand Charm' not in left or not loop.kind.swaps_gheeds or game is None:
        return False
    if loop.parked is not None:
        if loop.gheed != PICK:
            return False
        loop.gheed = CHOOSE
        LOG.info("Macro: charms: %s; %s is still not taken with the player's Gheed's Fortune on shared page %s: "
                 'to town for theirs', why, left, loop.parked.page)  # fmt: skip
        return True
    if loop.swap == game or loop.own is None:
        return False
    pack = self.carried_now()
    ours = gheeds(pack, loop.own) if pack is not None else None
    if pack is None or ours is None:
        return False
    if not pack.inventory.has_room(ours.size):
        if loop.room_tried != game:
            # Room first, in the cube
            loop.make_room, loop.room_tried = True, game
            LOG.info("Macro: charms: %s; %s lies on the ground, the player's Gheed's Fortune carried, and no %d x "
                     '%d free: room is made in the cube first', why, left, *ours.size)  # fmt: skip
            return True
        # The cube tried: the swap all the same (the player, 2026-10-18: "refused grand charm - should cause a
        # trip")
        LOG.info("Macro: charms: %s lies on the ground, the player's Gheed's Fortune carried, no %d x %d free and "
                 "the cube tried: the swap all the same, the player's block takes the new one", left,
                 *ours.size)  # fmt: skip
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
