"""The attack mode key's active modes and buff mode's routine (the player, 2026-10-19: "KP_3 - toggle attack mode,
let's add double tap to cycle different active modes (ATTACK, BUFF - where buff - we keep desired buffs active)").

One press turns the active mode on or off at once, as before; exactly two within DOUBLE, judged once the window closes,
cycle the active mode (macros/buffmode.py `next_active`), switching a mode that was on in place (`_judge_mode_taps`).
Buff mode (`_keep_buffs`) casts the build's upkeep rows as they come due or near their end while the player plays by
hand; its rules are buffmode.py's. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import threading
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort, Flipped, Hand
from inventory_tracking.macros.buffmode import (
    LOOK,
    NAMES,
    OWED_SECONDS,
    RENEW_AHEAD,
    Rest,
    castable,
    held_back,
    next_active,
)
from inventory_tracking.macros.buffs import Buffs, Due
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunting.base import hostiles
from inventory_tracking.macros.routines import DEAD, Dead, swap_until
from inventory_tracking.macros.runmode import DOUBLE
from inventory_tracking.macros.running.base import ATTACK, BUFF
from inventory_tracking.macros.skills import SWAP_WEAPONS, skill_name


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


# (the set found in hand, the set a stopped cast left, when): swapped back once the hand rests (`_keep_buffs`)
type Owed = tuple[frozenset[str], frozenset[str], float]


def _mode_running(self: MacroRunner) -> str | None:
    """The active mode on now, if any (attack mode first: a level run turns it on over buff mode)."""
    return ATTACK if self.attack_mode else BUFF if self.buff_mode else None


def _mode_tap(self: MacroRunner, at: float) -> None:
    """A press of the attack mode key at `at`: the first of a group toggles the active mode at once; the group is
    judged once DOUBLE seconds pass with no other (`_judge_mode_taps`). Under the lock."""
    if self.mode_taps and at - self.mode_taps[-1] > DOUBLE:
        self._judge_mode_taps()
    if not self.mode_taps:
        self.mode_was = self._mode_running()
        self._toggle_mode()
    self.mode_taps.append(at)
    if self.mode_timer is not None:
        self.mode_timer.cancel()
    self.mode_timer = threading.Timer(DOUBLE, self._mode_window, (at, len(self.mode_taps)))
    self.mode_timer.daemon = True
    self.mode_timer.start()


def _mode_window(self: MacroRunner, at: float, taps: int) -> None:
    """The window after the press at `at` is over: its group is judged, unless a press came since."""
    with self.lock:
        if self.closed or len(self.mode_taps) != taps or not self.mode_taps or self.mode_taps[-1] != at:
            return
        self._judge_mode_taps()


def _judge_mode_taps(self: MacroRunner) -> None:
    """The group of attack mode key presses is over (`_mode_tap`). Two: the first press's toggle undone, the active
    mode the next one, on if a mode was on before the pair ("if a mode is running, the double press switches it in
    place"). More: mashed, nothing switched. Under the lock."""
    count, self.mode_taps = len(self.mode_taps), []
    was, self.mode_was = self.mode_was, None
    if count == 1:
        return
    if count > 2:
        self._say(f'attack mode key pressed {count} times together: no mode switched')
        return
    self._mode_off()
    self.active = next_active(was or self.active)
    self._say(f'Active mode: {NAMES[self.active]}')
    if was is not None:
        self._mode_on(self.active)


def _toggle_mode(self: MacroRunner) -> None:
    """The attack mode key's toggle: a mode on goes off, else the active mode goes on. Under the lock."""
    if self._mode_running() is not None:
        self._mode_off()
    else:
        self._mode_on(self.active)


def _mode_on(self: MacroRunner, mode: str) -> None:
    """`mode` on: started now, or after the run working (`_follow`). Buff mode waits while the loop is on. Under the
    lock."""
    if mode == ATTACK:
        self.attack_mode, self.attack_declined = True, False
    else:
        self.buff_mode = True
        self.attack_declined = True  # the player chose no fight: a teleport press's fight leaves attack mode off
    if not self.working and (mode == ATTACK or not self.loop.on):
        self._start(mode)


def _mode_off(self: MacroRunner) -> None:
    """Both modes off; the one working cancelled. Under the lock."""
    if self.attack_mode:
        self.attack_mode, self.attack_declined = False, True
        self._end_run('attack mode off')
    self.buff_mode = False
    if self.working and self.routine in (ATTACK, BUFF):
        self.cancelled.set()


def _keep_buffs(self: MacroRunner, run: Run, key_names) -> None:
    """Buff mode until cancelled: at each look the hand watched (buffmode.py `Rest`), and once it has rested, out of
    town with no panel open, the first due upkeep row of the build cast (`_buff_cast`). Never a strike or a move.
    A death ends it: nothing more is pressed."""
    actuator = run.actuator
    rest = Rest(at=run.clock())  # the press that turned it on was the hand's: the first cast after a rest too
    said: str | None = ''
    owed: Owed | None = None
    own: Buffs | None = None
    allowed = False
    run.say('Buff mode on')
    while True:
        world = run.world()  # Cancelled when the runner ends the mode
        now = run.clock()
        player = world.player
        if player is not None and player.mode in DEAD:
            raise Dead('buff mode off: the character died')
        self._buff_flipped(run)
        if player is not None and not allowed:
            allowed = True
            try:
                key_names(world, ())  # the Show Items key another service presses is not the player's
            except Abort as stop:
                if run.stops(stop):
                    raise
        pressed = actuator.key_held() or actuator.button_held(1) or actuator.button_held(3)
        rest.look(now, pointer=actuator.keys.pointer(), pressed=pressed, mode=player.mode if player else None)
        rect = actuator.keys.focused_window_rect()
        why = held_back(world, pad=run.pad is not None, focused=rect is not None)
        if why != said:
            said = why
            LOG.info('Macro: buff mode: %s', f'waiting ({why})' if why else 'keeping the buffs up')
        if why is not None or rect is None or not rest.rested(now):
            run.pace.sleep(LOOK)
            continue
        if owed is not None:
            owed = self._swap_back(run, world, key_names, owed, now)
            if owed is not None:
                rest.stopped(run.clock())
                continue
        if self.hunter is not None:
            buffs = self.hunter.buffs  # attack mode's: one memory of the casts
        else:
            if own is None or own.plan is not run.build.buffs:
                own = Buffs(run.build)
            buffs = own
        buffs.let_go = None  # no strike is held in buff mode
        foes = hostiles(world)
        facts = buffs.facts(run, world, foes, ahead=RENEW_AHEAD)
        due = None
        for row in buffs.rows('upkeep'):
            if castable(row, world, foes):
                due = buffs.due(run, row, facts)
                if due is not None:
                    break
        if due is None:
            run.pace.sleep(LOOK)
            continue
        owed = self._buff_cast(run, buffs, due, key_names, rect[2] / rect[3], rest)


def _buff_cast(
    self: MacroRunner, run: Run, buffs: Buffs, due: Due, key_names, aspect: float, rest: Rest
) -> Owed | None:
    """Cast `due` as the hand rests: the weapon set and the pointer found are put back after; a stop by the hand
    counts as the row's try. The set a stopped cast left in hand is returned, owed."""
    actuator, row = run.actuator, due.row
    before = frozenset(run.hands()) if run.hands is not None else frozenset()
    back = actuator.keys.pointer()
    LOG.info(
        'Macro: buff mode: %s %s', skill_name(row.skill), 'near its end: cast again' if due.facts.lapsing else 'cast'
    )
    try:
        with actuator.held_act():
            buffs.cast(run, due, key_names, aspect)
            if row.caster is None:
                run.pause('key')
    except Abort as stop:
        if run.stops(stop):
            raise
        if isinstance(stop, Hand):
            rest.stopped(run.clock())
        LOG.info('Macro: buff mode: no %s (%s)', skill_name(row.skill), stop)
        buffs.remember(row, run.clock())
    owed = None
    left = frozenset(run.hands()) if run.hands is not None else frozenset()
    if before and left and left != before:
        owed = self._swap_back(run, run.world(), key_names, (before, left, run.clock()), run.clock())
    now = actuator.keys.pointer()
    mark = actuator.left_at
    if (
        back is not None
        and now is not None
        and mark is not None
        and now != back
        and max(abs(now[0] - mark[0]), abs(now[1] - mark[1])) <= actuator.drift
        and not (actuator.key_held() or actuator.button_held(1) or actuator.button_held(3))
    ):
        # The pointer the cast moved goes back where the player left it (as hunt.py `serve_move`'s click does)
        actuator.keys.move_pointer(*back)
        actuator.keys.sync()
    rest.cast(run.clock(), actuator.keys.pointer())
    return owed


def _swap_back(self: MacroRunner, run: Run, world, key_names, owed: Owed, now: float) -> Owed | None:
    """The weapon set found in hand before a cast swapped back, while the set the cast left is still in hand and
    OWED_SECONDS have not passed; None once nothing is owed."""
    found, left, since = owed
    hands = run.hands
    held = frozenset(hands()) if hands is not None else frozenset()
    if hands is None or held != left or now - since > OWED_SECONDS:
        if held != found:
            LOG.warning('Macro: buff mode: the weapon set found in hand is not back; left to the player')
        return None
    try:
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        if swap_until(run, lambda: frozenset(hands()) == found):
            LOG.info('Macro: buff mode: the weapon set found in hand is back')
            return None
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: buff mode: the weapon set found in hand not swapped back yet (%s)', stop)
    return owed


def _buff_flipped(self: MacroRunner, run: Run) -> None:
    """In controller mode buff mode casts nothing; the game back in keyboard mode makes the run again (`again`)."""
    play = self.pad_play
    if run.pad is None or play is None:
        return
    mode = play.mode()
    if mode is not None and not mode.controller and not mode.pending:
        raise Flipped('the game left controller mode')
