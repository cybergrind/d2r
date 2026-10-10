"""The macro actions inside the service: start a run, cancel the one running, toggle attack mode.

The compositor bindings (input/compositor.py, the one place that names keys) send a request each
to the appraisal socket:

- `macro <monotonic>`, the macro request: the routine for where the character is (routines.py).
- `teleport <monotonic>`, the teleport step: one step toward the level card's mark (teleport.py).
- `hunt elites <monotonic>`, the seek step: one step toward the nearest elite (hunt.py); attack mode
  is on after it.
- `hunt any <monotonic>`, the attack mode toggle (hunt.py).
- `pickup <monotonic>`, the pickup step: pick up what is worth it, else a seek step (pickup.py).

A run works on its own thread with its own memory handle and X connection. A request while a run
works cancels it, except a step's own request during the step, which queues one more: steps are
asked for again and again. Attack mode is a run that lives until its toggle or the macro request
ends it (the macro then runs as usual). The teleport and seek steps pause it for their step and it
resumes after; the pickup step waits for the fight to be over first. Each spoken step and the reason
a run stopped go to the HUD card and the log; the card outlives the run, never blocking the next
request.
"""

import math
import os
import random
import threading
import time
from collections.abc import Callable
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keybindings import show_items_key
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.pickup import pick_up, wanted
from inventory_tracking.macros.routines import SKILLS, run_macro
from inventory_tracking.macros.skills import character_bindings, skill_keys
from inventory_tracking.macros.teleport import step_toward
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import GameMemory
from inventory_tracking.models import SessionIdentity


REQUEST_PREFIX = 'macro '
TELEPORT_PREFIX = 'teleport '
HUNT_ELITES_PREFIX, HUNT_ANY_PREFIX, PICKUP_PREFIX = 'hunt elites ', 'hunt any ', 'pickup '
PREBUFF, TELEPORT, HUNT_ELITES, HUNT_ANY = 'prebuff', 'teleport', 'hunt elites', 'hunt any'  # routines
PICKUP = 'pickup'  # the pickup step: pick up what is worth it, else a seek step (pickup.py)
STEPS = frozenset((TELEPORT, HUNT_ELITES, PICKUP))  # one press is one step; the same key queues another
ATTACK = HUNT_ANY  # the attack mode toggle
THROTTLE = 0.3  # seconds between accepted macro requests (a bounce is not a cancel)
CARD_SECONDS = 4.0
RESEARCH_ENV = 'D2R_MACRO_RESEARCH'  # set: log which bytes name the unit under the pointer at a Consume
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
        self.hunter: Hunter | None = None  # the seek step's and attack mode's state and sources (hunt.py)
        self.working = False  # a run is acting (the thread lives on a while to show its last card)
        self.routine = PREBUFF
        self.again = False  # the step key pressed during its step: one more step after it
        self.generation = 0
        self.attack_mode = False  # the attack run is wanted, now or once the current step is done
        self.closed = False  # `close` was called: nothing starts any more
        self.pending: str | None = None  # a step asked for during attack mode: runs once the mode has paused
        self.lock = threading.RLock()  # every transition: a request, a run's end and its successor, shutdown

    def request(self, requested_at: float, now: float, routine: str = PREBUFF) -> bool:
        """Start `routine` (PREBUFF or a step), or toggle attack mode (HUNT_ANY). While a run works, a
        request cancels it, except a step's own request during the step (one more step) and a step
        during attack mode (the mode pauses for it and resumes after; the pickup step waits for the
        fight); the macro request during attack mode ends the mode and runs the macro once it has stopped."""
        with self.lock:
            if self.closed or not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1:
                return False
            if routine == PREBUFF and now - self.last_request < THROTTLE:
                return False
            self.last_request = now
            if routine == ATTACK:
                return self._toggle_attack_mode()
            if routine == PREBUFF:
                self.attack_mode = False  # the macro request ends it
            if routine == HUNT_ELITES:
                self.attack_mode = True  # the mode follows the seek step
            if self.working:
                if routine in STEPS and self.routine == routine:
                    self.again = True
                elif self.routine == ATTACK and routine == PICKUP and self.hunter is not None:
                    self.pending = routine  # after the fight: the mode pauses itself once nothing is in reach
                    self.hunter.after_fight.set()
                elif self.routine == ATTACK:
                    self.pending = routine  # the mode pauses for the step, or ends for the macro
                    self.cancelled.set()
                else:
                    self.cancelled.set()
                return True
            self._start(routine)
            return True

    def _toggle_attack_mode(self) -> bool:
        """The attack mode toggle: the mode on or off. On while a step works, it follows the step; off
        while it works, it is cancelled. Under the lock (`request`)."""
        self.attack_mode = not self.attack_mode
        if not self.attack_mode:
            if self.working and self.routine == ATTACK:
                self.cancelled.set()
            return True
        if not self.working:
            self._start(ATTACK)
        return True

    def _start(self, routine: str) -> None:
        """A run of `routine` on its own thread. Under the lock."""
        if self.closed:
            return
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
        """Shutdown is final: the run is cancelled and nothing follows it (no pending step, no attack
        mode resumed, no queued repeat), and no request starts another."""
        with self.lock:
            self.closed = True
            self.attack_mode, self.pending, self.again = False, None, False
            self.cancelled.set()
            thread = self.thread
        if thread is not None:
            thread.join(timeout=3)  # outside the lock: the run's end takes it
        if self.focus is not None:
            self.focus.close()

    def _say(self, text: str) -> None:
        LOG.info('Macro: %s', text)
        self.display([f'Macro: {text}'])

    def _guarded(self, cancelled: threading.Event, routine: str, generation: int) -> None:
        failed = False
        try:
            while True:
                self.execute(cancelled, routine)
                with self.lock:
                    if self.again and not cancelled.is_set():
                        self.again = False  # the step's own request came during it: one more step
                        continue
                    if routine == ATTACK:
                        self.attack_mode = False  # the mode returned on its own: the toggle follows
                    if self._follow(routine):
                        return
                break
        except Cancelled as stop:
            if routine == ATTACK:
                self._say('Attack mode paused' if self.attack_mode else 'Attack mode off')
            else:
                LOG.info('Macro stopped: %s', stop)
                self.display([f'Macro stopped: {stop}'])
        except Abort as stop:
            LOG.info('Macro stopped: %s', stop)
            self.display([f'Macro stopped: {stop}'])
            failed = True
        except Exception as exc:
            LOG.exception('Macro failed')
            self.display([f'Macro failed: {exc}'])
            failed = True
        else:
            failed = None  # ended and followed above: only the card is left
        if failed is not None:
            with self.lock:
                if failed and routine == ATTACK:
                    self.attack_mode = False  # the mode ended on its own: the game was left, or it gave up
                if self._follow(routine):
                    return
        time.sleep(CARD_SECONDS)
        if self.generation == generation:  # no newer run owns the card
            self.display([])

    def _follow(self, routine: str) -> bool:
        """The run of `routine` is over: start what follows it, if anything, and say whether something
        did. A step asked for during attack mode comes first, then the mode a step paused. Under the
        lock, in one piece with `working` going off: a request sees either the run or its successor."""
        self.working = False
        following, self.pending = self.pending, None
        if following is None and self.attack_mode and routine != ATTACK:
            following = ATTACK  # the step is done: the mode resumes
        if following is None or self.closed:
            return False
        self._start(following)
        return True

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
                    actuator.allow(*STEP_KEYS)  # the binding's own keys; the macro request waits for a release instead

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
                    loot=lambda: memory.loot(**wanted()),
                )
                if os.environ.get(RESEARCH_ENV):
                    run.research = memory.hover_candidates  # a scan of the whole data section per Consume
                run.hovered = memory.hovered
                run.arrival = lambda: self.journey.arrival(time.monotonic())
                if routine == TELEPORT:
                    step_toward(run, self.target() if self.target is not None else None, key_names)
                elif routine == PICKUP:
                    hunter = self.hunter
                    if hunter is None:
                        raise Abort('no level guide to hunt with')
                    level = hunter.level() if hunter.level is not None else None
                    if not pick_up(run, level, key_names, lambda: hunter.seek(run, key_names)):
                        self.attack_mode = True  # nothing to pick up: the press was a seek step, the mode follows
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
