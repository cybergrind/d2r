"""Win+X, KP_4, KP_2 and KP_3 inside the service: start a macro, cancel the one running, toggle attack mode.

The compositor bindings send `macro <monotonic>` (Win+X: the routine for where the character is,
routines.py), `teleport <monotonic>` (KP_4: one step toward the level card's mark, teleport.py),
`hunt elites <monotonic>` (KP_2: one step toward the nearest elite, hunt.py) and `hunt any
<monotonic>` (KP_3: attack mode on or off, hunt.py) to the appraisal socket. A run works on its own
thread with its own memory handle and X connection. A press of Win+X, KP_4 or KP_2 while a run works
cancels it, except the same step key during its own step, which queues one more step: the key is
pressed again and again (user, 2026-10-09). Attack mode is a run that lives until KP_3 again or
Win+X ends it (Win+X then runs the macro as usual); KP_3 toggles it and KP_2 turns it on after its
step (user, 2026-10-10 evening: KP_2 left the character standing beside the elite it had found until
KP_3 was pressed; the same morning's "KP_3 never turns it off" is withdrawn); KP_4 and KP_2 pause it
for their step and it resumes after (user, 2026-10-09 late: moving about must not stop it). Each
spoken step and the reason a run stopped go to the HUD card and the log; the card outlives the run,
never blocking the next press.
"""

import math
import random
import threading
import time
from collections.abc import Callable
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keybindings import show_items_key
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.routines import SKILLS, run_macro
from inventory_tracking.macros.skills import character_bindings, skill_keys
from inventory_tracking.macros.teleport import step_toward
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import GameMemory
from inventory_tracking.models import SessionIdentity


REQUEST_PREFIX = 'macro '
TELEPORT_PREFIX = 'teleport '
HUNT_ELITES_PREFIX, HUNT_ANY_PREFIX = 'hunt elites ', 'hunt any '
PREBUFF, TELEPORT, HUNT_ELITES, HUNT_ANY = 'prebuff', 'teleport', 'hunt elites', 'hunt any'  # routines
STEPS = frozenset((TELEPORT, HUNT_ELITES))  # one press is one step; the same key queues another
ATTACK = HUNT_ANY  # KP_3: the attack mode toggle
# Keys of the step bindings that may be down when a step starts: the keypad 4, 2 and 3 under either
# Num Lock state (since the evening of 2026-10-09; the compositor swallows them, but a release can
# come late) and the Mod of the earlier Win+T.
HOTKEY_KEYS = ('KP_4', 'KP_Left', 'KP_2', 'KP_Down', 'KP_3', 'KP_Next', 'Super_L', 'Super_R')
THROTTLE = 0.3  # seconds between accepted Win+X presses (a bounce is not a cancel)
CARD_SECONDS = 4.0
JOURNEY_SECONDS = 1.0  # how often the game and level are noted between presses


class MacroRunner:
    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        saved_games: Path,
        display: Callable[[list[str]], None] = lambda lines: None,
        execute: Callable[..., None] | None = None,
        place: Callable[[], tuple[str | None, int | None]] | None = None,
    ) -> None:
        self.source = source
        self.capture_lock = capture_lock
        self.saved_games = saved_games
        self.display = display
        self.execute = execute or self._execute
        self.cancelled = threading.Event()
        self.thread: threading.Thread | None = None
        self.focus: FocusTracker | None = None
        self.last_request = -math.inf
        self.journey = Journey()
        self.place = place or self._place
        self.last_poll = -math.inf
        self.unread = False
        self.target: Callable[[], Target | None] | None = None  # the level card's mark (levels/guide.py)
        self.hunter: Hunter | None = None  # KP_2/KP_3 state and sources (hunt.py), set by the service
        self.working = False  # a run is acting (the thread lives on a while to show its last card)
        self.routine = PREBUFF
        self.again = False  # the step key pressed during its step: one more step after it
        self.generation = 0
        self.attack_mode = False  # KP_3: the attack run is wanted, now or once the current step is done
        self.pending: str | None = None  # a step asked for during attack mode: runs once the mode has paused

    def request(self, requested_at: float, now: float, routine: str = PREBUFF) -> bool:
        """Start `routine` (PREBUFF, TELEPORT, HUNT_ELITES), or toggle attack mode (HUNT_ANY). While a run
        works, a press cancels it, except a step key during its own step (one more step) and a step key
        during attack mode (the mode pauses for the step and resumes after); Win+X during attack mode
        ends the mode and runs the macro once it has stopped."""
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1:
            return False
        if routine == PREBUFF and now - self.last_request < THROTTLE:
            return False
        self.last_request = now
        if routine == ATTACK:
            return self._toggle_attack_mode()
        if routine == PREBUFF:
            self.attack_mode = False  # Win+X ends it
        if routine == HUNT_ELITES:
            self.attack_mode = True  # KP_2 does its step and the mode follows it
        if self.working:
            if routine in STEPS and self.routine == routine:
                self.again = True
            elif self.routine == ATTACK:
                self.pending = routine  # the mode pauses for the step, or ends for the macro
                self.cancelled.set()
            else:
                self.cancelled.set()
            return True
        self._start(routine)
        return True

    def _toggle_attack_mode(self) -> bool:
        """KP_3: the mode on or off. On while a step works, it follows the step; off while it works, it
        is cancelled."""
        self.attack_mode = not self.attack_mode
        if not self.attack_mode:
            if self.working and self.routine == ATTACK:
                self.cancelled.set()
            return True
        if not self.working:
            self._start(ATTACK)
        return True

    def _start(self, routine: str) -> None:
        self.generation += 1
        self.cancelled, self.routine, self.again, self.working = threading.Event(), routine, False, True
        self.thread = threading.Thread(
            target=self._guarded, args=(self.cancelled, routine, self.generation), name='macro', daemon=True
        )
        self.thread.start()

    def poll(self, now: float) -> None:
        """Note the game and level for the journey; called from the service loop."""
        if now - self.last_poll < JOURNEY_SECONDS or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            self.journey.note(*self.place(), now)
            self.unread = False
        except Exception as exc:
            if not self.unread:  # once per outage, not once a second
                LOG.info('Macro: the level could not be noted (%s)', exc)
            self.unread = True
        finally:
            self.capture_lock.release()

    def _place(self) -> tuple[str | None, int | None]:
        self.source.ensure_connected()
        tables = {found['table_address'] for found in self.source.capture['unit_table_candidates']}
        if len(tables) != 1:
            raise ValueError('the game is not attached')
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], next(iter(tables)))
        try:
            return memory.place()
        finally:
            memory.close()

    def close(self) -> None:
        self.cancelled.set()
        if self.thread is not None:
            self.thread.join(timeout=3)
        if self.focus is not None:
            self.focus.close()

    def _say(self, text: str) -> None:
        LOG.info('Macro: %s', text)
        self.display([f'Macro: {text}'])

    def _guarded(self, cancelled: threading.Event, routine: str, generation: int) -> None:
        try:
            self.execute(cancelled, routine)
            while self.again and not cancelled.is_set():
                self.again = False
                self.execute(cancelled, routine)
            if routine == ATTACK:
                self.attack_mode = False  # the mode returned on its own: the toggle follows
        except Abort as stop:
            if routine == ATTACK and str(stop) == 'cancelled':
                self._say('Attack mode off' if not self.attack_mode else 'Attack mode paused')
            else:
                LOG.info('Macro stopped: %s', stop)
                self.display([f'Macro stopped: {stop}'])
                if routine == ATTACK:
                    self.attack_mode = False  # the mode ended on its own: the player attacked, or it gave up
        except Exception as exc:
            LOG.exception('Macro failed')
            self.display([f'Macro failed: {exc}'])
            if routine == ATTACK:
                self.attack_mode = False
        finally:
            self.working = False
        following, self.pending = self.pending, None
        if following is not None:
            self._start(following)
            return
        if self.attack_mode and routine != ATTACK:
            self._start(ATTACK)  # the step is done: the mode resumes
            return
        time.sleep(CARD_SECONDS)
        if self.generation == generation:  # no newer run owns the card
            self.display([])

    def _execute(self, cancelled: threading.Event, routine: str) -> None:
        with self.capture_lock:
            self.source.ensure_connected()
            pid, images, capture = self.source.pid, self.source.images, self.source.capture
        tables = {found['table_address'] for found in capture['unit_table_candidates']}
        if len(tables) != 1:
            raise Abort('the game is not attached')
        session = SessionIdentity(pid, images['identity']['start_ticks'], 0)
        if self.focus is None:
            self.focus = FocusTracker(INPUT)
            self.focus.wait_ready(timeout=1)
        focus = self.focus
        memory = GameMemory(pid, images['candidate_base'], next(iter(tables)))
        try:
            with X11Keyboard().connect(exclusive=False) as keys:
                if keys is None:
                    raise Abort('no X display')

                def focused() -> bool:
                    return focus(session) and owns_process(keys.focused_window_pid(), session)

                pace = Pace(random.Random())
                actuator = Actuator(keys, focused, pace)
                if routine in STEPS or routine == ATTACK:
                    actuator.allow(*HOTKEY_KEYS)  # the binding's own keys; Win+X waits for a release instead

                def key_names(world, skills=SKILLS):
                    if world.player is None:
                        raise Abort('not in a game')
                    show_items = show_items_key(self.saved_games, world.player.name)
                    if show_items:
                        actuator.allow(show_items)
                    try:
                        bindings = character_bindings(self.saved_games, world.player.name)
                        return skill_keys(world.slots, bindings, skills)
                    except (OSError, ValueError) as exc:
                        raise Abort(str(exc)) from exc

                run = Run(
                    memory.world,
                    actuator,
                    pace,
                    cancelled=cancelled,
                    say=self._say,
                    hands=memory.hands,
                    teleport=memory.teleport,
                )
                run.research = memory.hover_candidates
                run.arrival = lambda: self.journey.arrival(time.monotonic())
                if routine == TELEPORT:
                    step_toward(run, self.target() if self.target is not None else None, key_names)
                elif routine in (HUNT_ELITES, ATTACK):
                    if self.hunter is None:
                        raise Abort('no level guide to hunt with')
                    if routine == ATTACK:
                        actuator.drift, actuator.steady = 10**6, False  # the player's hand is on the mouse all along
                        self.hunter.attack_mode(run, key_names)
                    else:
                        self.hunter.seek(run, key_names)
                else:
                    run_macro(run, key_names)
        finally:
            memory.close()
