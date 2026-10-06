"""Win+X inside the service: start the macro for where the character is, or cancel a running one.

The compositor binding sends `macro <monotonic>` to the appraisal socket. A run works on its
own thread with its own memory handle and X connection; the next press while it runs cancels
it. Each spoken step and the reason a run stopped go to the HUD card and the log.
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
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.routines import SKILLS, run_macro
from inventory_tracking.macros.skills import character_bindings, skill_keys
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import GameMemory
from inventory_tracking.models import SessionIdentity


REQUEST_PREFIX = 'macro '
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

    def request(self, requested_at: float, now: float) -> bool:
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1 or now - self.last_request < 0.3:
            return False
        self.last_request = now
        if self.thread is not None and self.thread.is_alive():
            self.cancelled.set()
            return True
        self.cancelled = threading.Event()
        self.thread = threading.Thread(target=self._guarded, args=(self.cancelled,), name='macro', daemon=True)
        self.thread.start()
        return True

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

    def _guarded(self, cancelled: threading.Event) -> None:
        try:
            self.execute(cancelled)
        except Abort as stop:
            LOG.info('Macro stopped: %s', stop)
            self.display([f'Macro stopped: {stop}'])
        except Exception as exc:
            LOG.exception('Macro failed')
            self.display([f'Macro failed: {exc}'])
        time.sleep(CARD_SECONDS)
        if self.thread is threading.current_thread():  # no newer run owns the card
            self.display([])

    def _execute(self, cancelled: threading.Event) -> None:
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

                def key_names(world):
                    if world.player is None:
                        raise Abort('not in a game')
                    try:
                        bindings = character_bindings(self.saved_games, world.player.name)
                        return skill_keys(world.slots, bindings, SKILLS)
                    except (OSError, ValueError) as exc:
                        raise Abort(str(exc)) from exc

                pace = Pace(random.Random())
                run = Run(
                    memory.world,
                    Actuator(keys, focused, pace),
                    pace,
                    cancelled=cancelled,
                    say=self._say,
                    hands=memory.hands,
                )
                run.research = memory.hover_candidates
                run.arrival = lambda: self.journey.arrival(time.monotonic())
                run_macro(run, key_names)
        finally:
            memory.close()
