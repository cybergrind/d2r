"""The service loop's poll: the journey, the terror zone's onward run, the loop's watchdogs (overdue, beset, still), the
staff check, and the reads of the place it takes. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import threading
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.macros.actuator import Abort, Cause
from inventory_tracking.macros.hunting.base import SIGHT
from inventory_tracking.macros.loop import GAME_SECONDS, STILL_SECONDS
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.running.base import (
    JOURNEY_SECONDS,
    MAKE_ROOM_AFTER,
    ONWARD_PAUSE,
    ONWARD_SECONDS,
    PICKUP,
)
from inventory_tracking.macros.teleport import LOST_KEY
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def poll(self: MacroRunner, now: float) -> None:
    """Note the game and level for the journey; called from the service loop."""
    if now - self.last_poll < JOURNEY_SECONDS or not self.capture_lock.acquire(blocking=False):
        return
    self.last_poll = now
    try:
        game, area = self.place()
        self.journey.note(game, area, now)
        self.area_seen = area
        onward = self.onward
        if onward is not None and area is not None and area != onward[0]:
            # Through the door (`_run_over`): the next level's run, when it is the zone's too
            self.onward = None
            hunter = self.hunter
            if area not in TOWN_IDS and hunter is not None and hunter.bearings.terror(area) and self.attack_mode:
                LOG.info('Macro: run: terror zone: level %d entered: its full clear with no press', area)
                threading.Timer(ONWARD_PAUSE, self._press, args=(PICKUP,)).start()
        elif onward is not None and now - onward[1] > ONWARD_SECONDS:
            self.onward = None
        if self.resuming:
            with self.lock:
                self.resuming = False
                if not self.loop.on and not self.closed:
                    self._say('Loop resumed after a restart')
                    self._toggle_loop()
        if self.progress is not None:
            self.progress.note(game, area)
        self.unread = False
        with self.lock:
            why = None
            cause: Cause | None = None
            if self.attack_mode:
                self.loop.hurt.clear()  # a fight's losses are not a stand's (`beset`): counted from its end
            warned = self.warning
            if (
                warned is not None
                # only the stand-by by a valuable (hunting/choice.py `stay_by`), in a game: a plain warning carried
                # into the lobby once cancelled the next game's creation (2026-10-17 12:45)
                and self.standing
                and game is not None
                and now - warned[1] > MAKE_ROOM_AFTER
                and self.loop.on
            ):
                if self.loop.room_tried != game:
                    # Room is made before the watchdog stops the stand; the Gheed's swap first when it is one. The
                    # stand is answered: only one made after it is `stood_after_cube`'s
                    self.stand_answered = now
                    if not self._gheeds_swap(warned[0], self.valuable_left(), game):
                        self.loop.make_room, self.loop.room_tried = True, game
                        LOG.info('Macro: loop: %s: room is made in the cube', warned[0])
                    self.attack_mode = False
                    if self.working:
                        self.cancelled.set()
                else:
                    stood_after_cube(self, warned)
            kills = self.hunter.score.killed if self.hunter is not None else 0  # a fight in place is no stall
            # The Throne's wave wait is no stall either (hunting/throne.py `Waves.due`, bounded by its WAVE_WAIT)
            waves = self.hunter is not None and self.hunter.waves.due(now)
            if self.loop.waiting:
                pass  # for the game window's focus: the player's time, not the loop's
            elif self.loop.on and self.loop.overdue(game, now):
                seconds = self.loop.kind.game_seconds or GAME_SECONDS
                why = f'over {seconds:.0f} s in {game or "the lobby"}'
            elif self.loop.on and not self.attack_mode and self.loop.beset(self.where, self.life_seen, now, game, area):
                # Hit standing outside a fight: fought back, or left with life low (macros/stops.py `first`; the
                # player, 2026-10-19: "we must not die or we lose exp and our gear"; "Fight back first")
                life = self.life_seen or (0, 0)
                why, cause = f'the character is hit standing outside a fight (life {life[0]}/{life[1]})', 'beset'
            elif self.loop.on and game is not None and self.loop.still(self.where, now, game, kills, waves):
                why, cause = f'the character has not moved for {STILL_SECONDS:.0f} s', 'stall'
            if why is not None:
                # The loop is stuck (macros/loop.py GAME_SECONDS, STILL_SECONDS) or beset: the run is cancelled,
                # the next leg leaves the game or fights back
                self._loop_stopped(Abort(why, cause=cause))
                self.attack_mode = False
                if self.working:
                    self.cancelled.set()
        if game is None:
            self.staff_checked = None
        elif game != self.staff_checked and area is not None:
            # A game begun with the staff in hand drops Teleport from its key (user, 2026-10-11): said once.
            held = self.staff_in_hand()
            if held is not None:
                self.staff_checked = game
                if held and not self.working:
                    self._say(f'This game began with the staff in hand. {LOST_KEY}')
    except Exception as exc:
        if not self.unread:  # once per outage, not once a second
            LOG.info('Macro: the level could not be noted (%s)', exc)
        self.unread = True
    finally:
        self.capture_lock.release()


def stood_after_cube(self: MacroRunner, warned: tuple[str, float]) -> None:
    """The run's stand by a valuable with no room (`warned`: the warning and its clock), the cube already tried in
    this game (`Loop.room_tried`, once a game): the next room rule now, not after the still watchdog's 45 s. Under the
    lock. In the Canyon of the Magi at 14:03:35 on 2026-10-20 the run stood 45 s by a magic Ring, the cube made room
    for a Unique Razor Bow 40 s before; the watchdog's stop found no valuable the guard keeps a game for (the Ring is
    an identify candidate, the field identify's) and left the game, the Ring on the ground; at 01:24:02 that day a
    Grand Charm's stand got its trip (the room package) only after 40 s (rca/2026-10-20/stand-after-fight-findings.md).

    - No valuable the guard keeps a game for (`valuable_left` None): the stood one is given up (the hunt's `waived`)
      and the run goes on; the game is not left for it.
    - Else the stop rules (macros/stops.py `decide`: the room package, a trip, a drop, the loop held), as the
      watchdog's 'stall' stop would, once no hostile is within SIGHT (a Town Portal is not cast in a fight); while
      one is, the stand is held (said once) and the watchdog stays the backstop."""
    text, since = warned
    if since <= self.stand_answered:
        return  # answered already (the cube's room, a stop's rules): the watchdog stays its backstop
    left = self.valuable_left()
    if left is None:
        self.standing = False
        hunter = self.hunter
        if hunter is not None and hunter.warned is not None:
            hunter.waived.add(hunter.warned)
        LOG.info('Macro: loop: %s: the cube was tried in this game and no game is kept for it: the run goes on', text)
        return
    if self.attacker_near():
        if self.stand_held != since:
            self.stand_held = since
            LOG.info('Macro: loop: %s: the cube was tried in this game; %s lies on the ground: the next room rule '
                     'once no hostile is within %.0f', text, left, SIGHT)  # fmt: skip
        return
    self.standing = False
    self._loop_stopped(Abort(f'{text}: the cube was tried in this game', cause='room'))
    self.attack_mode = False
    if self.working:
        self.cancelled.set()


def _place(self: MacroRunner) -> tuple[str | None, int | None]:
    self.source.ensure_connected()
    table = one_unit_table(self.source.capture)
    if table is None:
        raise ValueError('the game is not attached')
    memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
    try:
        place = memory.place()
        self.where, self.dead_mode, self.life_seen = memory.where, memory.mode, memory.life
        return place
    finally:
        memory.close()


def _dead(self: MacroRunner) -> bool:
    """Whether the character reads dead now (routines.py DEAD); False when the game is not read."""
    try:
        self._place()
    except Exception:  # an unread game is no death
        return False
    return self.dead_mode in DEAD


def _staff_in_hand(self: MacroRunner) -> bool | None:
    """Whether the Teleport staff is in the set in hand; None without a staff or when unreadable."""
    table = one_unit_table(self.source.capture)
    if table is None:
        return None
    memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
    try:
        staff = memory.teleport()
        return None if staff is None else staff.in_hand
    finally:
        memory.close()
