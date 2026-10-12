"""The macro actions inside the service: start a run, cancel the one running, toggle attack mode.

The compositor bindings (input/compositor.py, the one place that names keys) send a request each
to the appraisal socket:

- `macro <monotonic>`, the macro request: the routine for where the character is (routines.py).
- `teleport <monotonic>`, the teleport step: one step toward the level card's mark (teleport.py).
- `hunt elites <monotonic>`, the seek step: one step toward the nearest elite, else into the room
  tour's next stop (hunt.py); attack mode is on after it.
- `hunt any <monotonic>`, the attack mode toggle (hunt.py).
- `pickup <monotonic>`, the pickup step: pick up what is worth it, else with hostiles near the sweep
  (attack mode moves on its own), else a seek step toward any hostile or the tour's next stop
  (pickup.py, hunt.py `step`); inside a fight also a step to a better stand.

A run works on its own thread with its own memory handle and X connection. A request while a run
works cancels it, except a step's own request during the step, which queues one more: steps are
asked for again and again. Attack mode is a run that lives until its toggle or the macro request
ends it (the macro then runs as usual). The teleport and seek steps pause it for their step and it
resumes after; the pickup step waits for the fight to be over first. Each spoken step and the reason
a run stopped go to the HUD card and the log; the card outlives the run, never blocking the next
request.

The runner is handed the builds (macros/build.py) by the process that makes it and imports none. A
run plays one of them: the one that claims the character in the game (`choose`), named at the run's
first look that shows a character (`choosing`), with no look of its own for it. It is on the run
(`Run.build`) for what moves, picks up and prebuffs, and the hunt is told it (`Hunter.use`).
"""

import math
import os
import random
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keybindings import show_items_key
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled
from inventory_tracking.macros.build import Build, choose
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter, threat
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.latency import Press, Trace
from inventory_tracking.macros.opening import open_near
from inventory_tracking.macros.pickup import pick_up, wanted, worth_a_stop
from inventory_tracking.macros.routines import prebuff_keys, run_macro, take_battle_weapons
from inventory_tracking.macros.skills import character_bindings, skill_keys
from inventory_tracking.macros.teleport import LOST_KEY, step_toward
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.waiting import Waiting
from inventory_tracking.macros.world import GameMemory, World
from inventory_tracking.models import SessionIdentity
from inventory_tracking.routes.progress import Progress


REQUEST_PREFIX = 'macro '
TELEPORT_PREFIX = 'teleport '
HUNT_ELITES_PREFIX, HUNT_ANY_PREFIX, PICKUP_PREFIX = 'hunt elites ', 'hunt any ', 'pickup '
PREBUFF, TELEPORT, HUNT_ELITES, HUNT_ANY = 'prebuff', 'teleport', 'hunt elites', 'hunt any'  # routines
PICKUP = 'pickup'  # the pickup step: pick up what is worth it, else a seek step (pickup.py)
STEPS = frozenset((TELEPORT, HUNT_ELITES, PICKUP))  # one press is one step; the same key queues another
ATTACK = HUNT_ANY  # the attack mode toggle
# What waits for the run working now, the first to go first: where the player wants to be, then what
# to fight, then the macro, then what lies on the ground.
PRIORITY = (TELEPORT, HUNT_ELITES, PREBUFF, PICKUP)
# Seconds after its press a request is still worth beginning, and a hop still worth its key (user,
# 2026-10-12: "teleporting after 2 seconds is way too late, maybe even lower"). Of the teleport
# presses that waited for a step, 90% had their key within 0.48 s and the slowest two took 0.7 and
# 1.5 s (21:26 and 21:35 on 2026-10-11). The pickup step that waits for a fight to end has no limit.
EXPIRES = {TELEPORT: 1.0, HUNT_ELITES: 1.5, PREBUFF: 3.0, PICKUP: 2.0}
THROTTLE = 0.3  # seconds between accepted macro requests (a bounce is not a cancel)
CARD_SECONDS = 4.0
# A warning of a routine (engine.Run `warn`: the inventory full) stays on the card this long after it was
# last given, above whatever is said, unless it is taken back sooner.
WARNING_SECONDS = 30.0
RESEARCH_ENV = 'D2R_MACRO_RESEARCH'  # set: log which bytes name the unit under the pointer at a Consume
# Seconds attack mode stays out after a teleport step before it resumes. The next press of a player
# travelling came 40 to 700 ms after the step before was over (30 presses, 21:26 on 2026-10-11), found
# the mode running and waited for it to stop, with a strike of its own in flight up to 0.4 s longer:
# half of those presses took over 250 ms to their Teleport key. The mode needs 0.3 s to its first
# strike after it starts anyway. 0.2 s at first: 8 of 34 such presses came within it and went to their
# key in 134 to 205 ms; most came 200 to 600 ms after (21:35 that day), hence 0.5 (user, 2026-10-12:
# the teleport key is to work instantly).
TRAVEL_QUIET = 0.5
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
        staff_in_hand: Callable[[], bool | None] | None = None,
        trace: Trace | None = None,
        builds: Sequence[Build] = (),
        fallback: Build | None = None,
    ) -> None:
        self.source = source
        # The builds a run is played by, in the order they are asked whose the character is, and the one
        # for a character none of them claims (macros/build.py `choose`). Given by the process that makes
        # the runner (the composition root: inventory_tracking/builds). Without a fallback nothing runs.
        self.builds = tuple(builds)
        self.fallback = fallback
        # The build the last run played: a run starts with it and names its own at its first look that
        # shows the character (`choosing`). The fallback until a character was seen.
        self.build: Build | None = fallback
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
        self.staff_in_hand = staff_in_hand or self._staff_in_hand
        self.staff_checked: str | None = None  # the game whose first look at the hands is done
        self.last_poll = -math.inf
        self.unread = False
        self.target: Callable[[], Target | None] | None = None  # the level card's mark (levels/guide.py)
        # the routes' stage of each level in this game (routes/progress.py): told the game and level here,
        # asked by the teleport step; `marks`: the places of the card's marks with a label (levels/guide.py)
        self.progress: Progress | None = None
        self.marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
        self.hunter: Hunter | None = None  # the seek step's and attack mode's state and sources (hunt.py)
        self.supers: Callable[[int], list[tuple[float, float]]] | None = None  # terror tracker's `supers`
        self.working = False  # a run is acting (the thread lives on a while to show its last card)
        self.routine = PREBUFF
        self.generation = 0
        self.warning: tuple[str, float] | None = None  # (text, the clock it was given at)
        self.attack_mode = False  # the attack run is wanted, now or once the current step is done
        self.closed = False  # `close` was called: nothing starts any more
        self.trace = trace or Trace()  # how long each press takes (latency.py)
        # the requests whose run has not begun: a step's own key during it, a step during attack mode (waiting.py)
        self.queue = Waiting(PRIORITY, self.trace)
        self.deadline = math.inf  # the run working now is worth its input until then (EXPIRES)
        self.press: Press | None = None  # the press of the run working now
        self.hurry: Callable[[], None] | None = None  # the service reads the level now (teleport.card_for)
        self.quiet_until = -math.inf  # attack mode resumes no sooner (TRAVEL_QUIET)
        self.lock = threading.RLock()  # every transition: a request, a run's end and its successor, shutdown

    def request(self, requested_at: float, now: float, routine: str = PREBUFF, **notes: object) -> bool:
        """Start `routine` (PREBUFF or a step), or toggle attack mode (HUNT_ANY). While a run works, a
        request cancels it, except a step's own request during the step (one more step) and a step
        during attack mode (the mode pauses for it and resumes after; the pickup step waits for the
        fight); the macro request during attack mode ends the mode and runs the macro once it has stopped."""
        with self.lock:
            during = self.routine if self.working else None
            press = self.trace.press(routine, requested_at, now, during=during, **notes)
            if self.closed or not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1:
                if not self.closed:
                    # Never silent: a press that did nothing is what "unresponsive" looks like.
                    LOG.warning('Macro: request %s dropped: %.0f ms old', routine, 1000 * (now - requested_at))
                self.trace.close(press, outcome='dropped: closed' if self.closed else 'dropped: too old')
                return False
            if routine == PREBUFF and now - self.last_request < THROTTLE:
                self.trace.close(press, outcome='dropped: a bounce')
                return False
            self.last_request = now
            LOG.info(
                'Macro: request %s, %.0f ms old, while %s',
                routine, 1000 * (now - requested_at), self.routine if self.working else 'nothing runs',
            )  # fmt: skip
            if routine == ATTACK:
                toggled = self._toggle_attack_mode()
                press.mark('accepted')
                self.trace.close(press, outcome='attack mode on' if self.attack_mode else 'attack mode off')
                return toggled
            if routine == PREBUFF:
                self.attack_mode = False  # the macro request ends it
            if routine == HUNT_ELITES:
                self.attack_mode = True  # the mode follows the seek step
            # Good until: the limit counts from the press, on the clock the queue reads.
            until = time.monotonic() + EXPIRES.get(routine, math.inf) - (now - requested_at)
            if routine != PICKUP:
                self.queue.drop(PICKUP, 'the player moved on')  # as the sweep below: no walk back for it
            if routine != PICKUP and self.hunter is not None:
                # A teleport or seek step, the macro: the player takes the character somewhere, and
                # the sweep a pickup request started (hunt.py) must not walk it back (Tower Cellar 3,
                # 2026-10-11 00:49: it walked 25 units back between two teleport steps to the stairs).
                self.hunter.sweep.end()
            if self.working:
                if routine in STEPS and self.routine == routine:
                    self._wait(press, 'queued behind its own step', until)
                elif routine == TELEPORT and self.routine == PICKUP:
                    # The pickup stops and the teleport step follows at once. The step itself takes a
                    # valuable near before it hops (`worth_a_stop`: that Ring, 17:35:18 on 2026-10-11,
                    # when the press cancelled its pickup and the next steps left the level without
                    # it); a potion is not worth the wait. Tower Cellar 5, 22:51:00 that day: the
                    # press to get out came while the pickup clicked 5 s at a potion among eight
                    # monsters, waited behind it, and the character died 0.4 s later.
                    self.cancelled.set()
                    self._wait(press, 'the pickup stops for it', until)
                elif self.routine == ATTACK and routine == PICKUP and self.hunter is not None:
                    # After the fight: the mode pauses itself once nothing is in reach. Inside a fight the
                    # press is also a step to a better stand, and the mode drops the wait (`_unwait`)
                    # when there is nothing to pick up.
                    self.hunter.unwait = self._unwait
                    self.hunter.after_fight.set()
                    self.hunter.step_asked.set()
                    self._wait(press, 'waits for the fight', math.inf)  # however long the fight takes
                elif self.routine == ATTACK:
                    self.cancelled.set()  # the mode pauses for the step, or ends for the macro
                    self._wait(press, 'attack mode pauses for it', until)
                else:
                    self.cancelled.set()
                    press.mark('accepted')
                    self.trace.close(press, outcome=f'cancelled {self.routine}')
                return True
            self._wait(press, 'started', until)
            self._start(routine)
            return True

    def _wait(self, press: Press, outcome: str, until: float) -> None:
        """`press` leads to a run that has not begun: it waits in the queue for it, good until `until`
        (`_start` takes it). Under the lock."""
        press.mark('accepted')
        press.notes['outcome'] = outcome
        self.queue.put(press.routine, until, press)

    @property
    def pending(self) -> str | None:
        """The routine that follows the run working now, if one waits."""
        ranked = sorted(self.queue.entries, key=PRIORITY.index)
        return ranked[0] if ranked else None

    def _pick(self) -> None:
        """The sweep found something to pick up (hunt.py `gather`): the pickup step follows the mode's pause."""
        with self.lock:
            if not self.queue.entries and not self.closed:
                self.queue.put(PICKUP)

    def _unwait(self) -> None:
        """The pickup step that waited for the fight is not wanted any more (hunt.py `asked_step`)."""
        with self.lock:
            self.queue.drop(PICKUP, 'not wanted any more')

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
        self.cancelled, self.routine, self.working = threading.Event(), routine, True
        self.thread = threading.Thread(
            target=self._guarded,
            args=(self.cancelled, routine, self.generation, *self.queue.take(routine)),
            name='macro',
            daemon=True,
        )
        self.thread.start()

    def poll(self, now: float) -> None:
        """Note the game and level for the journey; called from the service loop."""
        if now - self.last_poll < JOURNEY_SECONDS or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            game, area = self.place()
            self.journey.note(game, area, now)
            if self.progress is not None:
                self.progress.note(game, area)
            self.unread = False
            if game is None:
                self.staff_checked = None
            elif game != self.staff_checked and area is not None:
                # A game begun with the staff in hand was left that way, and the game then drops
                # Teleport from its key (user, 2026-10-11): said once, before the first step fails.
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

    def _staff_in_hand(self) -> bool | None:
        """Whether the Teleport staff is in the set in hand; None without a staff or when unreadable."""
        tables = {found['table_address'] for found in self.source.capture['unit_table_candidates']}
        if len(tables) != 1:
            return None
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], next(iter(tables)))
        try:
            staff = memory.teleport()
            return None if staff is None else staff.in_hand
        finally:
            memory.close()

    def close(self) -> None:
        """Shutdown is final: the run is cancelled and nothing follows it (no pending step, no attack
        mode resumed, no queued repeat), and no request starts another."""
        with self.lock:
            self.closed = True
            self.attack_mode = False
            self.queue.clear('the service closed')
            self.cancelled.set()
            thread = self.thread
        if thread is not None:
            thread.join(timeout=3)  # outside the lock: the run's end takes it
        if self.focus is not None:
            self.focus.close()

    def ground(self) -> Ground | None:
        """The walkable ground of the level the guide has a map of (routines.open_spots), None without one."""
        hunter = self.hunter
        level = hunter.level() if hunter is not None and hunter.level is not None else None
        return Ground(level.ground) if level is not None and level.ground else None

    def _show(self, lines: list[str]) -> None:
        """The card: the warning that stands, if any, above `lines`. A card with only the warning stays
        up when the lines are cleared."""
        warning = self.warning
        if warning is not None and time.monotonic() - warning[1] > WARNING_SECONDS:
            warning = self.warning = None
        self.display(([f'Macro: {warning[0]}'] if warning is not None else []) + lines)

    def _warn(self, text: str | None) -> None:
        """A warning that stays on the card (None takes it back): the next line said does not wipe it.
        user, 2026-10-12: "we should give an active warning that must be visible to the user"."""
        if text is None:
            if self.warning is not None:
                self.warning = None
                self._show([])
            return
        if self.warning is None or self.warning[0] != text:
            LOG.warning('Macro: %s', text)
        self.warning = (text, time.monotonic())
        self._show([])

    def _say(self, text: str) -> None:
        LOG.info('Macro: %s', text)
        self._show([f'Macro: {text}'])

    def _guarded(
        self,
        cancelled: threading.Event,
        routine: str,
        generation: int,
        until: float = math.inf,
        press: Press | None = None,
    ) -> None:
        failed = False
        try:
            while True:
                self.press, self.deadline = press, until
                self.trace.begin(press)
                if routine == ATTACK and cancelled.wait(max(0.0, self.quiet_until - time.monotonic())):
                    raise Cancelled
                ended = 'done'
                try:
                    self.execute(cancelled, routine)
                except Cancelled:
                    ended = 'cancelled'
                    raise
                except Exception as exc:
                    ended = f'stopped: {exc}'
                    raise
                finally:
                    self.trace.close(press, ended=ended)
                with self.lock:
                    if not cancelled.is_set() and self.queue.first() == routine:
                        until, press = self.queue.take(routine)  # the step's own request came during it
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
                self._show([f'Macro stopped: {stop}'])
        except Abort as stop:
            LOG.info('Macro stopped: %s', stop)
            self._show([f'Macro stopped: {stop}'])
            failed = True
        except Exception as exc:
            LOG.exception('Macro failed')
            self._show([f'Macro failed: {exc}'])
            failed = True
        else:
            failed = None  # ended and followed above: only the card is left
        if failed is not None:
            with self.lock:
                self.queue.drop(routine, 'the step before it stopped')  # no repeat of a step that did
                if failed and routine == ATTACK:
                    self.attack_mode = False  # the mode ended on its own: the game was left, or it gave up
                if self._follow(routine):
                    return
        time.sleep(CARD_SECONDS)
        if self.generation == generation:  # no newer run owns the card
            self._show([])

    def _follow(self, routine: str) -> bool:
        """The run of `routine` is over: start what follows it, if anything, and say whether something
        did. A step asked for during attack mode comes first, then the mode a step paused. Under the
        lock, in one piece with `working` going off: a request sees either the run or its successor."""
        self.working = False
        following = self.queue.first()
        if following is None and self.attack_mode and routine != ATTACK:
            following = ATTACK  # the step is done: the mode resumes
        if following is None or self.closed:
            return False
        if routine == TELEPORT and following == ATTACK:
            self.quiet_until = time.monotonic() + TRAVEL_QUIET
        self._start(following)
        return True

    def choosing(self, run: Run) -> None:
        """Have the run's build chosen at its first look at the game that shows a character: the
        first of the builds that claims it, else the fallback (macros/build.py `choose`). The look is
        the routine's own, whichever it is and however light, so choosing costs no look at the game
        and moves none; a routine reads the build (`Run.build`, and the hunt its own) only after it
        has seen the character. Chosen anew by every run, so a game with another character is
        followed; the hunt is told (`Hunter.use`), which keeps its memory while the build stays."""
        fallback = self.fallback
        if fallback is None:
            raise Abort('no build to play: the runner was given none')
        read, chosen = run.read, []

        def first() -> World:
            world = read()
            if not chosen and world.player is not None:
                chosen.append(True)  # once a run
                self.wear(run, choose(self.builds, world, fallback))
            return world

        run.read = first

    def wear(self, run: Run, build: Build) -> None:
        """`build` is the one the run plays, and the hunt with it."""
        if build is not self.build:
            LOG.info('Macro: the build is %s%s', build.name, '' if build.weapons else ', no weapon sets of its own')
        self.build = run.build = build
        if self.hunter is not None:
            self.hunter.use(build)

    def _execute(self, cancelled: threading.Event, routine: str) -> None:
        press = self.press
        build = self.build
        if build is None:
            raise Abort('no build to play: the runner was given none')

        def mark(name: str) -> None:
            if press is not None:
                press.mark(name)

        with self.capture_lock:
            mark('locked')
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
        reads = [0, 0.0]  # how many looks at the game this run took, and their seconds (latency.py)

        def look():
            began = time.perf_counter()
            try:
                return memory.world(light=run.light > 0)
            finally:
                reads[0] += 1
                reads[1] += time.perf_counter() - began

        try:
            with X11Keyboard().connect(exclusive=False) as keys:
                if keys is None:
                    raise Abort('no X display')

                def focused() -> bool:
                    return focus(session) and owns_process(keys.focused_window_pid(), session)

                pace = Pace(random.Random())
                actuator = Actuator(keys, focused, pace)
                actuator.mark = mark
                actuator.cancelled = cancelled
                if routine in STEPS or routine == ATTACK:
                    actuator.allow(*STEP_KEYS)  # the binding's own keys; the macro request waits for a release instead

                def key_names(world, skills=None):
                    # `skills` None: the keys of the prebuff of the build the run plays (routines.prebuff_keys)
                    if world.player is None:
                        raise Abort('not in a game')
                    show_items = show_items_key(self.saved_games, world.player.name)
                    if show_items:
                        actuator.allow(show_items)
                    try:
                        bindings = character_bindings(self.saved_games, world.player.name)
                        return skill_keys(world.slots, bindings, prebuff_keys(run.build) if skills is None else skills)
                    except (OSError, ValueError) as exc:
                        raise Abort(str(exc)) from exc

                run = Run(
                    look,
                    actuator,
                    pace,
                    cancelled=cancelled,
                    say=self._say,
                    hands=memory.hands,
                    teleport=memory.teleport,
                    loot=lambda: memory.loot(**wanted()),
                    build=build,
                )
                if os.environ.get(RESEARCH_ENV):
                    run.research = memory.hover_candidates  # a scan of the whole data section per Consume
                run.hovered = memory.hovered
                run.hover_note = memory.hover_note
                run.mark = mark
                run.warn = self._warn
                run.hurry = self.hurry
                run.deadline = self.deadline
                run.warps = memory.warps
                run.things = memory.things
                run.containers = memory.containers
                run.objects = memory.objects
                run.corpses = memory.corpses
                run.arrival = lambda: self.journey.arrival(time.monotonic())
                run.supers = self.supers
                run.ending = self.progress.ending if self.progress is not None else None
                run.ground = self.ground
                mark('ready')
                self.perform(run, actuator, routine, key_names)
        finally:
            memory.close()
            if press is not None:
                press.notes.update(reads=reads[0], read_ms=round(1000 * reads[1], 1))

    def staged(self, run: Run, key_names, plain: Callable[[Target | None], None]) -> None:
        """One press of the stage the level is at (macros/route.py `press`); `plain` is the step toward the
        card's mark for a level or a stage without one of its own."""
        walker = self.hunter

        def leave_the_game(run: Run, key_names) -> None:
            self.attack_mode = False  # as the macro request ends it
            route.leave(run, key_names)

        route.press(
            run,
            self.progress,
            self.target,
            self.marks,
            key_names,
            plain=plain,
            level=lambda: walker.level() if walker is not None and walker.level is not None else None,
            attack=lambda: setattr(self, 'attack_mode', True),
            leave=leave_the_game,
        )

    def perform(self, run: Run, actuator: Actuator, routine: str, key_names) -> None:
        """One routine on the run made for it (`_execute`), by the build chosen at its first look (`choosing`)."""
        self.choosing(run)
        if routine == TELEPORT:
            walker = self.hunter

            def plain(card: Target | None, run=run, walker=walker) -> None:
                drop = worth_a_stop(run) if walker is not None else None
                if walker is None:
                    step_toward(run, card, key_names)
                elif drop is not None:
                    # The step does not leave a valuable behind: this press takes it, the next hops.
                    LOG.info('Macro: the teleport step takes %s first', drop.label)
                    pick_up(run, walker.level() if walker.level is not None else None, key_names, lambda: None)
                elif card is not None and (crowd := walker.pack_ahead(run, card)):
                    # No hop into a pack that stands where the step would stand (user, 2026-10-12: "diving into
                    # big pack with staff in hand - could be fatal"): the main weapons, and the fight from where
                    # the character is, by the sweep's own places. The press after the pack is dead goes on.
                    run.say(f'{crowd} monsters by {card.label}: the fight first')
                    take_battle_weapons(run)
                    walker.step(run, key_names)
                    self.attack_mode = True
                elif card is not None and walker.boss_step(run, card, key_names):
                    pass  # the boss stands where its mark has no shot at it: the step went for the boss
                else:
                    step_toward(
                        run,
                        card,
                        key_names,
                        lambda target: walker.foot_step(run, target, key_names),
                        lambda target, player, spot: walker.warp_hop(run, target, player, spot, key_names),
                    )

            # One step of the stage the level is at (macros/route.py); the plain step without one.
            self.staged(run, key_names, plain)
        elif routine == PICKUP:
            hunter = self.hunter
            if hunter is None:
                raise Abort('no level guide to hunt with')
            level = hunter.level() if hunter.level is not None else None
            stepped = []

            def otherwise(run=run, hunter=hunter, level=level, stepped=stepped) -> None:
                if open_near(run, level, key_names, threat(run)):  # a chest by the character, a super chest
                    return
                with run.lightly():
                    player = run.world().player
                if self.progress is not None and player is not None and self.progress.ending(player.area):
                    # The route's bosses are dead: nothing is sought any more. The ground is the route's to
                    # call clean, and the press after that leaves the game, as the teleport key's does.
                    self.staged(run, key_names, lambda card: None)
                    return
                stepped.append(hunter.step(run, key_names))

            pick_up(run, level, key_names, otherwise, threat(run))
            if stepped:
                self.attack_mode = True  # nothing to pick up or open: a seek step, the mode follows
        elif routine in (HUNT_ELITES, ATTACK):
            if self.hunter is None:
                raise Abort('no level guide to hunt with')
            if routine == ATTACK:
                actuator.drift, actuator.steady = 10**6, False  # the player's hand is on the mouse all along
                self.hunter.pick = self._pick
                self.hunter.attack_mode(run, key_names)
            else:
                self.hunter.seek(run, key_names)
        else:
            run_macro(run, key_names)
