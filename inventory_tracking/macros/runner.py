"""The macro runner inside the service: starts a run per request, cancels the one running, toggles attack mode.

Requests come from the compositor bindings (input/compositor.py) over the appraisal socket: `macro` (routines.py),
`teleport` (teleport.py), `hunt elites` (the seek step), `hunt any` (attack mode), `pickup` (pickup.py), `loop` (KP_6).
A run works on its own thread with its own memory handle and X connection; the cancel rules are `_dispatch`'s. The
builds (macros/build.py) are handed in; a run plays the one that claims the character (`choosing`).
"""

import dataclasses
import math
import os
import random
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from pathlib import Path

from inventory_tracking.automation.ledger import OSD_LEDGER, PotionLedger
from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.game.kept import BeltKept, PutDown
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import VALUABLE, Loot, Pack, Player, World, has_room
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keybindings import INVENTORY, action_key, show_items_key
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled, Cause, Flipped, Hand
from inventory_tracking.macros.build import Build, choose
from inventory_tracking.macros.cain import identify_all
from inventory_tracking.macros.charms import Parked, gheeds
from inventory_tracking.macros.cta import cast_in_hand
from inventory_tracking.macros.cube import (
    SURE_BLOCK,
    arrange_keys,
    drop_for,
    perfect_of,
    stash,
    stash_only,
    transmute,
    unpack,
)
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import USE_NEAR, spot_of
from inventory_tracking.macros.hunt import Bearings, Hunter, threat
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.junk import identify, junk_of, named
from inventory_tracking.macros.keepers import amulet_keeper
from inventory_tracking.macros.latency import Press, Trace
from inventory_tracking.macros.loop import (
    CHOOSE,
    GAME_SECONDS,
    PICK,
    STILL_SECONDS,
    LegHands,
    Loop,
    loop_kinds,
)
from inventory_tracking.macros.lootpolicy import GUARD, verdict
from inventory_tracking.macros.navigation import Abilities, means
from inventory_tracking.macros.opening import open_near
from inventory_tracking.macros.pad import PadActs, PadActuator, PadPlay, input_policy
from inventory_tracking.macros.pickmode import MODES, REGULAR, SURE, TRADE, kept, next_mode
from inventory_tracking.macros.pickup import (
    FETCH_HOPS,
    SHUNNED,
    TAKEN,
    Refused,
    approach,
    moved_in_hand,
    pick_up,
    wanted,
    worth_a_stop,
)
from inventory_tracking.macros.portal import portal_source
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.routines import DEAD, Dead, prebuff_keys, run_macro, show_items_on
from inventory_tracking.macros.runmode import DOUBLE, TERROR, badge
from inventory_tracking.macros.sightings import Sightings
from inventory_tracking.macros.skills import TELEPORT as TELEPORT_SKILL, character_bindings, skill_keys, skill_name
from inventory_tracking.macros.stops import Remedy, Stopped, decide, first
from inventory_tracking.macros.teleport import LOST_KEY, ready, step_toward
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.town import Contract, Exit, Needs, kept_gem
from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT, cut
from inventory_tracking.macros.tzloop import full_clear, trip as tz_trip
from inventory_tracking.macros.tzroutine import Itinerary, policy_of
from inventory_tracking.macros.visit import Hands, Remembered, note_view, visit
from inventory_tracking.macros.waiting import Waiting
from inventory_tracking.models import Actor, SessionIdentity
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.native.memory import one_unit_table
from inventory_tracking.routes.model import FIGHT
from inventory_tracking.routes.progress import Progress


REQUEST_PREFIX = 'macro '
TELEPORT_PREFIX = 'teleport '
HUNT_ELITES_PREFIX, HUNT_ANY_PREFIX, PICKUP_PREFIX = 'hunt elites ', 'hunt any ', 'pickup '
LOOP_PREFIX = 'loop '
PREBUFF, TELEPORT, HUNT_ELITES, HUNT_ANY = 'prebuff', 'teleport', 'hunt elites', 'hunt any'  # routines
PICKUP = 'pickup'  # pick up what is worth it, else a seek step (pickup.py)
# The HUD's word for the loop's pickup mode (macros/pickmode.py)
LOOP_WORDS = {SURE: 'LOOP SURE', TRADE: 'LOOP TRADE', REGULAR: 'LOOP ALL'}
TRANSMUTES = 3  # transmutes of one gem kind per stash visit, at most (macros/cube.py `transmute`)
PICK_SLACK = 3  # pickups past the parked gems' count before the ground is taken for clear (`transmute_gems`)
MAKE_ROOM_AFTER = 5.0  # seconds stood by a valuable with no room before the loop makes room in the cube
FOCUS_POLL = 0.5  # seconds between focus checks while the loop waits for the game window
DROPPED_SECONDS = 600.0  # an item dropped for a valuable's room is not taken up again for this long (a game)
VERDICT_SECONDS = 4.0  # wait for the identify watcher's appraisals (it polls once a second)
LOOP = 'loop'  # the KP_6 loop's toggle; a run of it is one leg (macros/loop.py)
STEPS = frozenset((TELEPORT, HUNT_ELITES, PICKUP))  # one press is one step; the same key queues another
# A terror zone's full clear that ends at a door goes on through it with no press (the player, 2026-10-18: "yes, go to
# next level without press"): a teleport press ONWARD_PAUSE after, then the pickup press on the new level; nothing more
# once ONWARD_SECONDS pass.
DOOR_PRESS = 'going through takes a press'
ONWARD_PAUSE = 0.3
ONWARD_SECONDS = 20.0
ATTACK = HUNT_ANY  # the attack mode toggle
# The order waiting requests run in: where the player wants to be, what to fight, the macro, the ground.
PRIORITY = (TELEPORT, HUNT_ELITES, PREBUFF, PICKUP)
# Seconds after its press a request is still worth starting (user, 2026-10-12: "teleporting after 2 seconds is way too
# late"); 90 % of waiting teleport presses had their key within 0.48 s (2026-10-11). The fight-waiting pickup has none.
EXPIRES = {TELEPORT: 1.0, HUNT_ELITES: 1.5, PREBUFF: 3.0, PICKUP: 2.0}
# Within this of the route's door an empty pickup press is the step through it (rca/2026-10-15/kp1-door-findings.md).
DOOR_NEAR = USE_NEAR
AT_DROP_UNITS = 3.0  # a trip back to a valuable this near is at it: no move to it first
THROTTLE = 0.3  # seconds between accepted macro requests (a bounce is not a cancel)
CARD_SECONDS = 4.0
# A routine's warning (engine.Run `warn`) stays on the card this long after it was last given, unless taken back.
WARNING_SECONDS = 30.0
RESEARCH_ENV = 'D2R_MACRO_RESEARCH'  # set: log which bytes name the unit under the pointer at a Consume
# Seconds attack mode stays out after a teleport step, so the next travel press finds no strike in flight (user,
# 2026-10-12: the teleport key is to work instantly); most presses came 200-600 ms after the step (2026-10-11).
TRAVEL_QUIET = 0.5
JOURNEY_SECONDS = 1.0  # how often the game and level are noted between presses
# A run the input mode flipped under restarts in the new mode (`again`, actuator.py `Flipped`), its start waiting up
# to FLIP_SETTLE for the flip (flips took 10-12 ms, 2026-10-14). FLIPS_AGAIN restarts within FLIPS_WINDOW s stop it.
FLIP_SETTLE = 1.0
FLIP_POLL = 0.02
FLIPS_AGAIN, FLIPS_WINDOW = 3, 10.0


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
        loop_items: Path | None = None,
    ) -> None:
        self.source = source
        # The builds asked in order to claim the character, and the one for none (build.py `choose`)
        self.builds = tuple(builds)
        self.fallback = fallback
        # The build the last run played; each run names its own at its first look (`choosing`).
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
        # the routes' stage of each level this game (routes/progress.py); `marks`: the card's labelled marks
        self.progress: Progress | None = None
        self.marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
        self.hunter: Hunter | None = None  # the seek step's and attack mode's state and sources (hunt.py)
        # (level, clock) of a terror zone run ended at a door (`_run_over`); the level the last poll read
        self.onward: tuple[int | None, float] | None = None
        self.area_seen: int | None = None
        self.supers: Callable[[int], list[tuple[float, float]]] | None = None  # terror tracker's `supers`
        # each belt column's last content this game: an emptied healing column stays one
        # (rca/2026-10-13/potions-findings.md)
        self.belt = BeltKept()
        # the items the player put down this game (game/kept.py): out of every run's loot and the HUD's ground marks
        self.put_down = PutDown()
        # skill -> clock of its last cast that took, across runs (macros/buffs.py `took_of`)
        self.lasting: dict[int, float] = {}
        # the healer's (`make osd`) potion ledger: read for the mercenary's gaps, written by the drinker's claim
        # (automation/ledger.py `PotionLedger.claim`)
        self.healer: PotionLedger | None = None
        with suppress(OSError):
            self.healer = PotionLedger(OSD_LEDGER)
        self.working = False  # a run is acting (the thread lives on a while to show its last card)
        self.routine = PREBUFF
        self.generation = 0
        self.warning: tuple[str, float] | None = None  # (text, the clock it was given at)
        self.standing = False  # the warning is the level run's stand by a valuable with no room (`_stand_by`)
        self.attack_mode = False  # the attack run is wanted, now or once the current step is done
        # The player's toggle turned the mode off: a teleport press whose goal is a fight leaves it off (`pursues`)
        self.attack_declined = False
        self.closed = False  # `close` was called: nothing starts any more
        # The KP_6 loop (macros/loop.py): on, it follows every run that nothing else follows.
        self.loop = Loop(store=loop_items)
        self.loop.forget = self._forget_given_up  # GHEED_STASH: the level run tries the charm again
        # the game whose stash view was logged, the shared page shown last (macros/visit.py `Remembered`)
        self.stash_memory = Remembered()
        self.where: tuple[float, float] | None = None  # where the character was at the last poll (`_place`)
        self.dead_mode: int | None = None  # the character's mode at the last poll (`_dead`)
        self.life_seen: tuple[int, int] | None = None  # (life, max life) at the last poll (loop.py `beset`)
        self.valuable_left: Callable[[], str | None] = self._valuable_left  # (tests give their own)
        self.carried_now: Callable[[], Pack | None] = self._carried_now  # the inventory now, for `_gheeds_swap`
        # An item unit's stats from the run's memory (GameMemory.item_stats)
        self.item_stats: Callable[[int], dict[int, int]] | None = None
        # Valuables seen this game and still on the ground (sightings.py); the ground census's items (game/memory.py)
        self.sightings = Sightings()
        self.ground_seen: set[tuple[int, int]] = set()
        # The identify watcher's appraisals by unit id (identify/service.py `verdicts_now`): the loop's junk
        self.verdicts: Callable[[], dict[int, str]] = dict
        # The verdicts of carried identified items, read now (`IdentifyWorker.appraise`, macros/junk.py `junk_of`)
        self.appraise: Callable[[list[int]], dict[int, str]] = lambda units: {}
        self.resuming = False  # the loop was on before the service restarted (`resume`): turned on at the next poll
        # The loop's pickup mode (macros/pickmode.py); the KP_6 presses not judged yet and their timer
        self.pickup_mode = MODES[0]
        self.loop_taps: list[float] = []
        self.loop_timer: threading.Timer | None = None
        self.shut = threading.Event()  # set by `close`: a run's card wait ends with it
        self.trace = trace or Trace()  # how long each press takes (latency.py)
        # the requests whose run has not begun (waiting.py)
        self.queue = Waiting(PRIORITY, self.trace)
        self.deadline = math.inf  # the run working now is worth its input until then (EXPIRES)
        self.press: Press | None = None  # the press of the run working now
        self.hurry: Callable[[], None] | None = None  # the service reads the level now (teleport.card_for)
        # told each look's seconds (the service's load meter, appraisal/load.py)
        self.looked: Callable[[float], None] | None = None
        self.quiet_until = -math.inf  # attack mode resumes no sooner (TRAVEL_QUIET)
        # the combat recorder's `note` (takes/record.py): each request and each line said goes into the take
        self.noted: Callable[..., None] | None = None
        # The pad and the game's input mode (macros/pad.py); None: every run plays by the keys and the mouse.
        self.pad_play: PadPlay | None = None
        self.flips: list[float] = []  # when a run was made again after a flip of the input mode (`again`)
        self.settling = False  # the next run's start waits for a flip under way to be over (`play_by`)
        self.lock = threading.RLock()  # every transition: a request, a run's end and its successor, shutdown

    def request(self, requested_at: float, now: float, routine: str = PREBUFF, **notes: object) -> bool:
        """A player/API request; autonomous continuation uses the private dispatch path."""
        return self._dispatch(requested_at, now, routine, autonomous=False, **notes)

    def _dispatch(self, requested_at: float, now: float, routine: str, *, autonomous: bool, **notes: object) -> bool:
        """Start `routine` (PREBUFF or a step), or toggle attack mode (HUNT_ANY). A request cancels the run working,
        except a step's own key during the step (one more step) and a step during attack mode (the mode pauses; the
        pickup waits for the fight); the macro request ends the mode and runs once it has stopped."""
        with self.lock:
            during = self.routine if self.working else None
            press = self.trace.press(routine, requested_at, now, during=during, **notes)
            if self.noted is not None:
                self.noted('request', routine=routine, age=round(now - requested_at, 3), during=during)
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
            if routine == LOOP:
                self._loop_tap(now)
                press.mark('accepted')
                self.trace.close(press, outcome='judged with the presses around it')
                return True
            if routine == ATTACK:
                toggled = self._toggle_attack_mode()
                press.mark('accepted')
                self.trace.close(press, outcome='attack mode on' if self.attack_mode else 'attack mode off')
                return toggled
            if routine == PREBUFF:
                self.attack_mode = False  # the macro request ends it
                self.attack_declined = False  # the next game's fights want it
                self._end_run('the macro request')
            if routine == HUNT_ELITES:
                self.attack_mode = True  # the mode follows the seek step
                self.attack_declined = False
            # The limit counts from the press, on the queue's clock.
            until = time.monotonic() + EXPIRES.get(routine, math.inf) - (now - requested_at)
            if routine == TELEPORT and self.working and self.routine == ATTACK and self.pursuit:
                # The pursuit (macros/pursuit.py): the press is posted to the mode, nothing is cancelled and no quiet
                # follows, so a press that resolves to "fight here" costs the fight nothing.
                assert self.hunter is not None
                self.hunter.hand_over = self._hand_over
                self.hunter.post(Pursuit(TELEPORT, time.monotonic() - (now - requested_at)))
                press.mark('accepted')
                self.trace.close(press, outcome='posted to attack mode')
                return True
            if routine == PICKUP and self.pursuit:
                # One press runs the level's route through attack mode (the player, 2026-10-13: "one press of KP_1,
                # then it runs the whole level automatically"); a press during the run only renews it.
                assert self.hunter is not None
                self.hunter.hand_over, self.hunter.run_over = self._hand_over, self._run_over
                self.hunter.post(Pursuit(PICKUP, time.monotonic() - (now - requested_at), advance=False, leash=FULL))
                self.attack_mode, self.attack_declined = True, False
                if not self.working:
                    self._start(ATTACK)
                press.mark('accepted')
                self.trace.close(press, outcome='posted to attack mode')
                return True
            if routine != PICKUP:
                self.queue.drop(PICKUP, 'the player moved on')  # as the sweep below: no walk back for it
            if routine != PICKUP and self.hunter is not None:
                # The player takes the character somewhere: the pickup's sweep must not walk it back (it walked
                # 25 units back between two teleport steps, 2026-10-11 00:49).
                self.hunter.sweep.end()
            if self.working:
                if routine in STEPS and self.routine == routine:
                    self._wait(press, 'queued behind its own step', until)
                elif routine == TELEPORT and self.routine == PICKUP:
                    # The pickup stops and the step follows at once; the step itself takes a valuable near first
                    # (`worth_a_stop`). Waiting behind a potion's pickup got the character killed (2026-10-11 22:51).
                    self.cancelled.set()
                    self._wait(press, 'the pickup stops for it', until)
                elif self.routine == ATTACK and routine == PICKUP and self.hunter is not None:
                    # Inside a fight the press is also a step to a better stand; the mode drops the wait (`_unwait`)
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
        """Queue `press` for its run, good until `until` (`_start` takes it). Under the lock."""
        press.mark('accepted')
        press.notes['outcome'] = outcome
        self.queue.put(press.routine, until, press)

    @property
    def pending(self) -> str | None:
        """The routine that follows the run working now, if one waits."""
        ranked = sorted(self.queue.entries, key=PRIORITY.index)
        return ranked[0] if ranked else None

    def _pick(self) -> None:
        """The sweep found something to pick up (hunting/sweep.py `gather`): the pickup step follows the pause."""
        with self.lock:
            if not self.queue.entries and not self.closed:
                self.queue.put(PICKUP)

    @property
    def run_badge(self) -> str | None:
        """The HUD's words for the run mode (macros/runmode.py `badge`) and, with the loop on, its pickup mode and kind;
        None when none shows."""
        words = (
            badge(self.hunter.mode) if self.hunter is not None else None,
            LOOP_WORDS[self.pickup_mode] if self.loop.on else None,
            self.loop.kind.name.upper() if self.loop.on and self.loop.kind.badge else None,
        )
        return ' '.join(word for word in words if word) or None

    @property
    def pursuit(self) -> bool:
        """Whether the pursuit is on for the last run's build (`BuildSettings.pursuit`), with a hunt to make it."""
        return self.hunter is not None and self.build is not None and self.build.settings.pursuit

    def _hand_over(self, routine: str = TELEPORT) -> None:
        """The key posted to the mode is a step of its own after all (hunting/judging.py `defer`: a door, the loot, the
        leaving): `routine` follows the mode's pause."""
        with self.lock:
            if not self.queue.entries and not self.closed:
                self.queue.put(routine, time.monotonic() + EXPIRES.get(routine, EXPIRES[TELEPORT]))

    def _run_over(self, why: str) -> None:
        """A level run ended by the hunt itself (hunt.py `end_run`). With the loop on, the attack mode its leg turned
        on ends with it and the next leg follows (rca/2026-10-16/loop-chests-findings.md §2). From the run's thread."""
        with self.lock:
            if self.loop.on and self.loop.kind.agenda and why != 'the level was left':
                # A terror zone kind's run worked its level (macros/agenda.py `Agenda.ran`), unless it left it
                area = self.hunter.ended_area if self.hunter is not None else None
                self.loop.agenda.ran(area if area is not None else self.area_seen)
            if not self.loop.on:
                mode = self.hunter.mode if self.hunter is not None else None
                if self.attack_mode and mode is not None and mode.why == TERROR and DOOR_PRESS in why:
                    self.onward = (self.area_seen, time.monotonic())
                    LOG.info('Macro: run: terror zone: through the door with no press, then the next level runs')
                    threading.Timer(ONWARD_PAUSE, self._press, args=(TELEPORT,)).start()
                return
            if not self.attack_mode:
                return
            self.attack_mode = False
            if self.working and self.routine == ATTACK:
                self.cancelled.set()

    def _press(self, routine: str) -> None:
        """A press of the macro's own, as the player's key would make it (`request`)."""
        now = time.monotonic()
        self._dispatch(now, now, routine, autonomous=True)

    def _loop_level_run(self, hunter: Hunter, rush: bool = True, agenda: bool = False) -> None:
        """The loop's chests leg: the KP_1 level run through attack mode; its end is the leg's (`_run_over`). `rush`:
        past what does not attack (not for Andariel's fight); `agenda`: a terror zone kind's targets
        (macros/goals-plan.md)."""
        with self.lock:
            hunter.hand_over, hunter.run_over = self._hand_over, self._run_over
            hunter.carry_one = self._carry_one  # a refused unique Grand Charm: the Gheed's swap (macros/pickup.py)
            if agenda:
                hunter.agenda, hunter.agenda_policy = self.loop.agenda, self._agenda_policy
            post = Pursuit(PICKUP, time.monotonic(), advance=False, leash=FULL, rush=rush, looped=True, agenda=agenda)
            hunter.post(post)
            self.attack_mode, self.attack_declined = True, False

    def _agenda_policy(self, area: int) -> str:
        """How a terror zone kind's level run works level `area` (macros/tzroutine.py `policy_of`)."""
        plan = self.loop.agenda.plan
        trip = plan.excursion_of(area, self.loop.agenda.finished) if isinstance(plan, Itinerary) else None
        return policy_of(area, trip, full_clear(self.loop))

    def _way_on(self, run: Run, key_names, take_one: Callable[[], bool], level_run: Callable[[], None]) -> None:
        """At the way on (stairs, a door): what lies there first, then the press through (macros/pursuit.py
        `to_the_door`); else the level run to it. The level is not come back to, so its loot goes first."""
        player = run.world().player
        if player is not None and self.at_the_way_on(player):
            if take_one():
                return
            self._teleport_step(run, key_names)
        else:
            level_run()

    def _loop_hands(self, run: Run, key_names) -> LegHands:
        """The hands of one leg of the KP_6 loop (macros/loop.py `LegHands`)."""
        hunter = self.hunter

        def labels() -> None:
            # Item labels on before a level run (routines.py `show_items_on`)
            world = run.world()
            name = world.player.name if world.player is not None else None
            show_items_on(run, show_items_key(self.saved_games, name) if name else None)

        agenda = self.loop.kind.agenda

        def level_run() -> None:
            if hunter is None:
                raise Abort('no level guide to hunt with')
            labels()  # the player's hard rule
            if agenda:
                self._loop_level_run(hunter, rush=False, agenda=True)  # the terror zone kinds: the agenda's targets
            else:
                self._loop_level_run(hunter)

        def way_on() -> None:
            self._way_on(run, key_names, take_one, level_run)

        def fight() -> None:
            if hunter is None:
                raise Abort('no level guide to hunt with')
            labels()
            self._loop_level_run(hunter, rush=False)

        def take_one() -> bool:
            level = hunter.level() if hunter is not None and hunter.level is not None else None
            # No room for a valuable: a 'room' stop, and the room rules make room (the player, 2026-10-18: "we should
            # stop and clear inventory with our designated town routine")
            if pick_up(run, level, key_names, lambda: None, threat(run), looped=True):
                return True
            # Else a valuable seen this game and not picked up is gone back for (routes/lower-kurast-loop-plan.md §14)
            return self._fetch(run, level, key_names)

        def inventory_key() -> str | None:
            world = run.world()
            return action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None

        def transmute_gems(full: frozenset[int]) -> tuple[int, int]:
            # Kept flawless gems, three into a perfect one at the stash (the player, 2026-10-17: "we need to cube 3
            # flawless -> perfect"); what has no room meanwhile is put down and picked up after (2026-10-18: "drop on
            # the ground then pickup and move to cube"). Returns (made, still on the ground).
            key = inventory_key()
            if key is None:
                return 0, 0
            parked: list[int] = []

            def staying() -> frozenset[tuple[int, int, int]]:
                # the cube takes the loop's items, not the full stacks' runes and materials (for Jamella)
                pack = run.reads.carried()
                sold = self.loop.sold_full
                held = {(i.txt, i.x, i.y) for i in pack.items if i.txt in sold} if pack is not None else set()
                return (self.loop.own or frozenset()) | held

            def park(unit_id: int) -> None:
                self.put_down.park(unit_id)
                parked.append(unit_id)

            made = left = 0
            for txt in sorted(t for t in full if perfect_of(t) not in (None, *full)):
                for _ in range(TRANSMUTES):
                    done = transmute(run, key, txt, park)
                    made += done
                    if parked:
                        stash(run, key, staying())  # room to pick them up
                        for _ in range(len(parked) + PICK_SLACK):
                            if not pick_up(run, None, key_names, lambda: None):
                                break
                        now = run.reads.carried()
                        held = {i.unit_id for i in (*now.items, *now.in_cube)} if now is not None else set()
                        left = sum(1 for unit in parked if unit not in held)
                        LOG.info('Macro: cube: %d put down for the transmute, %d picked up again', len(parked),
                                 len(parked) - left)  # fmt: skip
                        parked.clear()
                    if not done:
                        break
            if made:
                # A kept gem still carried (a fourth of a kind) waits in the emptied cube for its next three; left in
                # the 2 x 4 block it broke the contract (2026-10-19 07:26)
                try:
                    stash_only(run, key, self.loop.own or frozenset(), lambda item: kept_gem(item, full))
                except Abort as stop:
                    if run.stops(stop):
                        raise
                    LOG.info('Macro: cube: the kept gems not put in: %s', stop)
            return made, left

        def town_visit(exit: Exit) -> Contract:
            return self._shared_town_visit(run, exit, transmute_gems)

        def identify_loot(items: Sequence) -> None:
            self._identify_loot(run, items)

        def bring(items: Sequence) -> int:
            key = inventory_key()
            return unpack(run, key, items) if key is not None else 0

        def sighted(area: int | None) -> str | None:
            found = [s for s in self.sightings.outstanding() if area is None or s.area == area]
            return f'{found[0].label} at ({found[0].x:.0f}, {found[0].y:.0f})' if found else None

        def terrorized(area: int) -> bool | None:
            wanted = getattr(self.progress, 'wanted', None)
            return wanted(area) if wanted is not None else None

        def navigate() -> None:
            if hunter is None:
                return
            world = run.world()
            build = run.build or self.build
            free = None
            for moves in build.movement if build is not None else ():
                for source in getattr(moves, 'sources', ()):
                    skill = source.jump.skill
                    if skill != TELEPORT_SKILL and skill in world.slots and free is None:
                        free = skill_name(skill)
            found = means(
                Abilities(
                    run.reads.own_teleport(),
                    run.reads.teleport(),
                    self.loop.teleports,
                    free,
                )
            )
            if hunter.looped is not found.intent:
                LOG.info('Macro: navigation: %s (%s)', found.kind, found.why)
            hunter.looped = found.intent

        return LegHands(
            level_run,
            take_one,
            visit=town_visit,
            identify=identify_loot,
            bring=bring,
            way_on=way_on,
            fight=fight,
            left=self.valuable_left,
            sighted=sighted,
            terrorized=terrorized,
            navigate=navigate,
        )

    def _end_run(self, why: str) -> None:
        """End the pickup key's level run with attack mode (macros/pursuit.py, the leash)."""
        if self.hunter is not None:
            self.hunter.end_run(None, why)

    def _unwait(self) -> None:
        """The pickup step that waited for the fight is not wanted any more (hunting/sweep.py `asked_step`)."""
        with self.lock:
            self.queue.drop(PICKUP, 'not wanted any more')

    def _picked(self, loot: Loot) -> Loot:
        """The drops the pickup goes for: with the loop on, those of its pickup mode (macros/pickmode.py)."""
        if not self.loop.on:
            return loot
        loot = kept(loot, self.pickup_mode)
        skipped = self.loop.sold_full  # a full stash stack's rune is not picked up (macros/loop.py `sold_full`)
        if skipped:
            loot = dataclasses.replace(
                loot, drops=tuple(d for d in loot.drops if d.kind != VALUABLE or d.txt not in skipped)
            )  # the potions the belt wants are taken whatever the stash holds
        return loot

    def _sighted(self, memory: GameMemory, loot: Loot) -> Loot:
        """`loot` noted in the game's sightings (macros/sightings.py), with the loop on and in one of its levels (not
        its town reads)."""
        if self.loop.on and memory.where_area in self.loop.kind.levels:
            self.sightings.update(loot, memory.where, memory.where_area, time.monotonic())
        return loot

    def _fetch(self, run: Run, level, key_names) -> bool:
        """A trip back to a valuable the loop saw and no press picked up (macros/sightings.py `fetch`); whether one was
        made. `Abort` when its trips back fail: the leg stops and the guard (`_valuable_left`) keeps the game."""
        player = run.world().player
        if player is None:
            return False
        trip = self.loop.trip
        if trip is not None and self.loop.returned == trip and self.loop.forgiven != (trip, self.loop.trips):
            # Back from a trip for room: its valuables' trips back start over (the player, 2026-10-18: "one game can
            # do several trips to the town")
            self.loop.forgiven = (trip, self.loop.trips)
            self.sightings.again()
        return self.sightings.fetch(
            (player.x, player.y),
            player.area,
            time.monotonic(),
            lambda found: self._go_back(run, found, level, key_names),
        )

    def _go_back(self, run: Run, found, level, key_names) -> None:
        """A trip back to `found`: within a click (`approach`), the pickup's give-up lifted, and, if not at it, a move
        to it so the clicks come from another footing (11 clicks from one place took nothing, 2026-10-18 15:53)."""
        SHUNNED.pop(found.unit_id, None)
        approach(run, found, level, key_names, FETCH_HOPS)
        player = run.world().player if level is not None else None
        if player is None or math.dist((player.x, player.y), (found.x, found.y)) <= AT_DROP_UNITS:
            return
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            return
        try:
            moved_in_hand(run, found, level, rect[2] / rect[3], key_names, Abort('a trip back, within a click'))
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: a trip back to %s: no move to it (%s); clicked from here', found.label, stop)

    def _loop_tap(self, at: float) -> None:
        """A KP_6 press at `at`, judged with its group once DOUBLE seconds pass with no other: one toggles the loop,
        two switch the pickup mode (the player, 2026-10-16), three the run's kind. Under the lock."""
        if self.loop_taps and at - self.loop_taps[-1] > DOUBLE:
            self._judge_loop_taps()
        self.loop_taps.append(at)
        if self.loop_timer is not None:
            self.loop_timer.cancel()
        taps = len(self.loop_taps)
        self.loop_timer = threading.Timer(DOUBLE, self._loop_window, (at, taps))
        self.loop_timer.daemon = True
        self.loop_timer.start()

    def _loop_window(self, at: float, taps: int) -> None:
        """The window after the press at `at` is over: its group is judged, unless a press came since."""
        with self.lock:
            if self.closed or len(self.loop_taps) != taps or not self.loop_taps or self.loop_taps[-1] != at:
                return
            self._judge_loop_taps()

    def _judge_loop_taps(self) -> None:
        """The group of KP_6 presses is over (`_loop_tap`). Under the lock."""
        count, self.loop_taps = len(self.loop_taps), []
        if count == 1:
            self._toggle_loop()
        elif count == 2:
            self.pickup_mode = next_mode(self.pickup_mode)
            self._say(f'Loop pickup: {self.pickup_mode}')
        elif count == 3:
            # The run's kind (macros/loop.py KINDS; the player, 2026-10-18: "rebuild loop start to accept what type of
            # run we're going to run"), for a start in the Fortress or the lobby
            kinds = list(loop_kinds().values())  # the terror zone kinds once promoted (macros/tzloop.py ENABLED)
            self.loop.kind = kinds[(kinds.index(self.loop.kind) + 1) % len(kinds)]
            self.loop.chosen = True  # by hand: no place overrides it
            self._say(f'Loop run: {self.loop.kind.name}')
        else:
            self._say(f'KP_6 pressed {count} times together: nothing switched')

    def _toggle_loop(self) -> None:
        """KP_6: the loop on from where the character is (a run working now is followed by its first leg), or off at
        once (the run cancelled, the character left where it is). Under the lock."""
        if self.loop.on:
            self.loop.stop()
            self.attack_mode = False
            self._end_run('the loop off')
            if self.working:
                self.cancelled.set()
            self._say('Loop off')
            return
        self.loop.start()
        self._say('Loop on')
        if not self.working:
            self._start(LOOP)

    def _loop_stopped(self, why: object) -> None:
        """A leg's stop: the loop leaves the game and goes on (macros/loop.py `recover`), or ends, saying why; the
        rules are macros/stops.py's. Under the lock or from the run's thread."""
        dead = isinstance(why, Dead) or self._dead()
        cause = classify(why)
        early = first(cause, on=self.loop.on, dead=dead)
        if early is Remedy.DEAD:
            self.attack_mode = False
            self._stop_loop(why if isinstance(why, Dead) else Dead(f'the character is dead ({why})'))
            return
        if early is Remedy.LEAVE:
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
            LOG.info(
                "Macro: loop: %s; %s lies on the ground: a trip to town for room (the agenda's package)", why, left
            )
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

    def _stop_loop(self, why: object) -> None:
        """The loop off by itself, saying why (the watch tools read the line: d2-loop-watch logwords.py STOPPED)."""
        self.loop.stop()
        LOG.info('Macro: loop stopped: %s', why)
        self._show([f'Loop stopped: {why}'])

    def _gheeds_swap(self, why: object, left: str | None, game: str | None) -> bool:
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

    def _carry_one(self, refused: Refused) -> bool:
        """A unique Grand Charm refused for the carried Gheed's Fortune (macros/pickup.py `Refused`) outside the loop's
        own routine: whether the swap is due for it (`_gheeds_swap`); the run stops for it then. Loop off or no swap:
        False, the run's own rules go on."""
        with self.lock:
            if not self.loop.on:
                return False
            game = self.loop.seen[0] if self.loop.seen is not None else None
            return self._gheeds_swap(refused, refused.drop.label, game)

    def _forget_given_up(self) -> None:
        """The level run's give-up memory cleared (hunting/choice.py `forget_given_up`): the Gheed's swap's
        GHEED_STASH."""
        if self.hunter is not None:
            self.hunter.forget_given_up()

    def _carried_now(self) -> Pack | None:
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

    def _toggle_attack_mode(self) -> bool:
        """The attack mode toggle. On while a step works, it follows the step; off while it works, it is cancelled.
        Under the lock (`request`)."""
        self.attack_mode = not self.attack_mode
        self.attack_declined = not self.attack_mode
        if not self.attack_mode:
            self._end_run('attack mode off')
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
                    and self.loop.room_tried != game
                ):
                    # Room is made before the watchdog stops the stand; the Gheed's swap first when it is one
                    if not self._gheeds_swap(warned[0], self.valuable_left(), game):
                        self.loop.make_room, self.loop.room_tried = True, game
                        LOG.info('Macro: loop: %s: room is made in the cube', warned[0])
                    self.attack_mode = False
                    if self.working:
                        self.cancelled.set()
                if self.loop.waiting:
                    pass  # for the game window's focus: the player's time, not the loop's
                elif self.loop.on and self.loop.overdue(game, now):
                    seconds = self.loop.kind.game_seconds or GAME_SECONDS
                    why = f'over {seconds:.0f} s in {game or "the lobby"}'
                elif (
                    self.loop.on
                    and not self.attack_mode
                    and self.loop.beset(self.where, self.life_seen, now, game, area)
                ):
                    # Hit standing outside a fight: the game is left at once (the player, 2026-10-19: "we must not die
                    # or we lose exp and our gear"; rca/2026-10-19/near-death-findings.md)
                    life = self.life_seen or (0, 0)
                    why, cause = f'the character is hit standing outside a fight (life {life[0]}/{life[1]})', 'beset'
                elif self.loop.on and game is not None and self.loop.still(self.where, now, game):
                    why, cause = f'the character has not moved for {STILL_SECONDS:.0f} s', 'stall'
                if why is not None:
                    # The loop is stuck (macros/loop.py GAME_SECONDS, STILL_SECONDS): the run is cancelled, the next
                    # leg leaves the game
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

    def _valuable_left(self) -> str | None:
        """What the loop would pick up lying on the ground in sight ('unread' when the ground cannot be read): a game
        with one is never left (`_loop_stopped`)."""
        try:
            table = one_unit_table(self.source.capture)
            if table is None:
                return 'unread'
            memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
            memory.ground_seen = self.ground_seen
            try:
                loot = self._sighted(memory, self._picked(self.put_down.see(memory.loot(**wanted()))))
            finally:
                memory.close()
        except Exception as exc:
            LOG.info('Macro: the ground could not be read (%s)', exc)
            return 'unread'
        # What the guard must not leave is the policy's (macros/lootpolicy.py `verdict`)
        found = [
            drop
            for drop in loot.drops
            if verdict(
                drop, GUARD, room=has_room(loot.room, drop.size), shown=drop.unit_id in loot.shown, looped=True
            ).hold
        ]
        if found:
            return found[0].label
        # One seen this game and out of the client's reach now lies there all the same (macros/sightings.py)
        return self.sightings.left()

    def _dead(self) -> bool:
        """Whether the character reads dead now (routines.py DEAD); False when the game is not read."""
        try:
            self._place()
        except Exception:  # an unread game is no death
            return False
        return self.dead_mode in DEAD

    def _place(self) -> tuple[str | None, int | None]:
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

    def _room_in_cube(self, run: Run) -> int:
        """Outside the KP_6 loop, the valuables the macro picked up itself (pickup.py TAKEN) into the cube; how many."""
        if self.loop.on or run.carried is None:
            return 0
        pack = run.carried()
        world = run.world()
        if pack is None or world.player is None:
            return 0
        key = action_key(self.saved_games, world.player.name, INVENTORY)
        if key is None:
            return 0
        own = frozenset((item.txt, item.x, item.y) for item in pack.items if item.unit_id not in TAKEN)
        return stash(run, key, own)

    def _staff_in_hand(self) -> bool | None:
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

    def resume_state(self) -> dict:
        """What a restart of the service carries over (appraisal/service.py `Restart`)."""
        with self.lock:
            return {
                'loop': self.loop.on,
                'pickup_mode': self.pickup_mode,
                'loop_kind': self.loop.kind.key,
                'sightings': self.sightings.state(),
                # The player's Gheed's Fortune on a shared page mid-swap (macros/charms.py): fetched back after it
                'gheeds': self.loop.parked.state() if self.loop.parked is not None else None,
            }

    def resume(self, state: dict) -> None:
        """Take up what the service before a restart left (`resume_state`): the pickup mode at once, the loop at the
        first poll that reads the game (`poll`)."""
        with self.lock:
            if state.get('pickup_mode') in MODES:
                self.pickup_mode = state['pickup_mode']
            if state.get('loop_kind') in loop_kinds():
                self.loop.kind = loop_kinds()[state['loop_kind']]
                self.loop.chosen = True  # kept from before the restart
            if isinstance(state.get('sightings'), dict):
                self.sightings.restore(state['sightings'])
                # A restart is made for a fix: the trips back start over, or a valuable out of trips stops it at once
                self.sightings.again()
            parked = Parked.restore(state.get('gheeds'))
            if parked is not None:
                self.loop.parked = parked
                LOG.info("Macro: charms: the player's Gheed's Fortune (unit %d) is on shared page %s: fetched back "
                         'first', parked.unit_id, parked.page)  # fmt: skip
            self.resuming = bool(state.get('loop'))
        LOG.info(
            'Macro: resumed after a restart: loop %s, pickup %s, run %s',
            'on' if self.resuming else 'off',
            self.pickup_mode,
            self.loop.kind.name,
        )

    def close(self) -> None:
        """Shutdown is final: the run is cancelled, nothing follows it, and no request starts another."""
        with self.lock:
            self.closed = True
            self.shut.set()
            self.attack_mode = False
            if self.loop_timer is not None:
                self.loop_timer.cancel()
            self.loop.stop()
            self._end_run('the service closed')
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
            self.standing = False
        self.display(([f'Macro: {warning[0]}'] if warning is not None else []) + lines)

    def _warn(self, text: str | None) -> None:
        """A warning that stays on the card until taken back with None (user, 2026-10-12: "we should give an active
        warning that must be visible to the user")."""
        self.standing = False
        if text is None:
            if self.warning is not None:
                self.warning = None
                self._show([])
            return
        if self.warning is None or self.warning[0] != text:
            LOG.warning('Macro: %s', text)
        self.warning = (text, time.monotonic())
        self._show([])

    def _stand_by(self, text: str) -> None:
        """The warning of the level run standing by a valuable with no room (engine.Run `stand_by`): `poll` makes room
        in the cube after MAKE_ROOM_AFTER."""
        self._warn(text)
        self.standing = True

    def _say(self, text: str) -> None:
        LOG.info('Macro: %s', text)
        if self.noted is not None:
            self.noted('said', text=text)
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
                        self._end_run('attack mode ended')
                    if self._follow(routine):
                        return
                break
        except Cancelled as stop:
            if routine == ATTACK:
                self._say('Attack mode paused' if self.attack_mode else 'Attack mode off')
            else:
                LOG.info('Macro stopped: %s', stop)
                self._show([f'Macro stopped: {stop}'])
        except Flipped as stop:
            with self.lock:
                if self.again(cancelled, routine, generation, stop):
                    return
            LOG.info('Macro stopped: %s', stop)
            self._show([f'Macro stopped: {stop}'])
            failed = True
            if routine == LOOP:
                self._loop_stopped(stop)
        except Abort as stop:
            LOG.info('Macro stopped: %s', stop)
            self._show([f'Macro stopped: {stop}'])
            failed = True
            if routine == LOOP:
                self._loop_stopped(stop)
            elif isinstance(stop, Refused) and self._carry_one(stop):
                # A pickup met the carry-one refusal: the mode and its level run end, the loop's swap leg follows
                with self.lock:
                    self.attack_mode = False
                    self._end_run("the Gheed's swap")
        except Exception as exc:
            LOG.exception('Macro failed')
            self._show([f'Macro failed: {exc}'])
            failed = True
            if routine == LOOP:
                self._loop_stopped(exc)
        else:
            failed = None  # ended and followed above: only the card is left
        if failed is not None:
            with self.lock:
                self.queue.drop(routine, 'the step before it stopped')  # no repeat of a step that did
                if failed and routine == ATTACK:
                    self.attack_mode = False  # the mode ended on its own: the game was left, or it gave up
                    self._end_run('attack mode stopped')
                if self._follow(routine):
                    return
        self.shut.wait(CARD_SECONDS)
        if self.generation == generation:  # no newer run owns the card
            self._show([])

    def again(self, cancelled: threading.Event, routine: str, generation: int, stop: Flipped) -> bool:
        """The input mode flipped under the run of `routine`: the same request starts again in the new mode
        (`play_by`); whether it did. Not when the run was cancelled, a newer run owns the runner, attack mode is off, or
        the mode flipped FLIPS_AGAIN times within FLIPS_WINDOW. Under the lock."""
        if self.closed or cancelled.is_set() or generation != self.generation:
            return False
        if routine == ATTACK and not self.attack_mode:
            return False
        now = time.monotonic()
        self.flips = [at for at in self.flips if now - at < FLIPS_WINDOW]
        if len(self.flips) >= FLIPS_AGAIN:
            LOG.info(
                'Macro: input mode flipped under %s again (%s): %d restarts in %.0f s, the run stops',
                routine, stop, len(self.flips), FLIPS_WINDOW,
            )  # fmt: skip
            return False
        self.flips.append(now)
        LOG.info(
            'Macro: input mode flipped under %s (%s): the run ends and the same request starts again', routine, stop
        )
        self.settling = True
        if routine != ATTACK:
            # As a fresh press of the key, the flip's settling on top
            self.queue.put(routine, now + FLIP_SETTLE + EXPIRES.get(routine, math.inf))
        self._start(routine)
        return True

    def _follow(self, routine: str) -> bool:
        """The run of `routine` is over: start what follows it (a queued step, the mode a step paused, the loop's next
        leg); whether something did. Under the lock, in one piece with `working` going off: a request sees either the
        run or its successor."""
        self.working = False
        following = self.queue.first()
        if following is None and self.attack_mode and routine != ATTACK:
            following = ATTACK  # the step is done: the mode resumes
        if following is None and self.loop.on:
            following = LOOP  # its next leg
        if following is None or self.closed:
            return False
        if routine == TELEPORT and following == ATTACK and not self.pursuit:
            # Not with the pursuit on: the mode itself gives up a strike for the next press (hunting/judging.py
            # `key_asks`).
            self.quiet_until = time.monotonic() + TRAVEL_QUIET
        self._start(following)
        return True

    def choosing(self, run: Run) -> None:
        """Have the run's build chosen at its first look that shows a character (macros/build.py `choose`), on the
        routine's own look so it costs none; anew each run, so another character is followed."""
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
        if build.weapons is not None:
            # Every run knows the build's weapon sets: the teleport step's empty-staff swap (hunt.py `empty_hop`)
            # did nothing in a run that held none (2026-10-13 12:33).
            run.prebuff_hands, run.battle_hands = build.weapons.prebuff, build.weapons.battle
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
        table = one_unit_table(capture)
        if table is None:
            raise Abort('the game is not attached')
        session = SessionIdentity(pid, images['identity']['start_ticks'], 0)
        if self.focus is None:
            self.focus = FocusTracker(INPUT)
            self.focus.wait_ready(timeout=1)
        focus = self.focus
        memory = GameMemory(pid, images['candidate_base'], table)
        memory.ground_seen = self.ground_seen  # one census across runs (game/memory.py `_census`)
        reads = [0, 0.0]  # how many looks at the game this run took, and their seconds (latency.py)

        looked = self.looked

        def look():
            began = time.perf_counter()
            try:
                return memory.world(light=run.light > 0)
            finally:
                took = time.perf_counter() - began
                reads[0] += 1
                reads[1] += took
                if looked is not None:
                    looked(took)

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
                actuator.noted = self.noted  # the pointer check's abort goes into the take (actuator.py)
                if routine in STEPS or routine in (ATTACK, LOOP):
                    actuator.allow(*STEP_KEYS)  # the binding's own keys; the macro request waits for a release instead

                def key_names(world, skills=None):
                    # `skills` None: the keys of the prebuff of the build the run plays (routines.prebuff_keys)
                    if world.player is None:
                        raise Abort('not in a game')
                    show_items = show_items_key(self.saved_games, world.player.name)
                    if show_items:
                        actuator.allow(show_items)
                    wanted = prebuff_keys(run.build) if skills is None else skills
                    name = world.player.name
                    try:
                        if run.pad is not None:  # controller mode: the records' labels (macros/pad.py)
                            return run.pad.keys(wanted, lambda: character_bindings(self.saved_games, name))
                        bindings = character_bindings(self.saved_games, name)
                        return skill_keys(world.slots, bindings, wanted)
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
                    loot=lambda: self._sighted(
                        memory, self._picked(self.put_down.see(self.belt.see(memory.loot(**wanted()))))
                    ),
                    build=build,
                )
                if os.environ.get(RESEARCH_ENV):
                    run.research = memory.hover_candidates  # a scan of the whole data section per Consume
                run.hovered = memory.hovered
                run.own_teleport = memory.own_teleport
                run.worn_skills = memory.worn_skills
                if self.hunter is not None:
                    self.hunter.room_maker = self._room_in_cube
                    self.hunter.looping = lambda: self.loop.on  # the sweep holds a plain valuable then (`take_one`)
                run.wear = memory.wear
                run.cta = memory.cta
                run.arrival_swap = lambda: cast_in_hand(run, key_names)
                run.lasting = self.lasting  # the buffs' casts that took, across runs (macros/buffs.py `took_of`)
                run.hover_note = memory.hover_note
                run.mark = mark
                run.warn = self._warn
                run.stand_by = self._stand_by
                run.hurry = self.hurry
                run.deadline = self.deadline
                run.warps = memory.warps
                run.things = memory.things
                run.containers = memory.containers
                run.carried = memory.carried
                run.stock = memory.stock
                run.stash_view = memory.stash_view
                self.item_stats = memory.item_stats
                run.players_item = lambda item: self.loop.players_item(item, memory.item_stats(item.unit_id))
                run.kept_item = lambda item: amulet_keeper(item, memory.item_stats(item.unit_id))
                run.objects = memory.objects
                run.corpses = memory.corpses
                run.flights = memory.flights
                if self.healer is not None:
                    run.given = lambda kind, ledger=self.healer: ledger.given_at(Actor.MERC, kind)
                    run.ledger = self.healer  # the drinker claims the character's potion in it
                run.arrival = lambda: self.journey.arrival(time.monotonic())
                run.supers = self.supers
                run.ending = self.progress.ending if self.progress is not None else None
                run.ground = self.ground
                self.play_by(run, actuator, routine)
                mark('ready')
                try:
                    self.perform(run, actuator, routine, key_names)
                finally:
                    if run.pad is not None:
                        run.pad.actuator.neutral()  # nothing of the pad is left held after a run
        finally:
            memory.close()
            if press is not None:
                press.notes.update(reads=reads[0], read_ms=round(1000 * reads[1], 1))

    def play_by(self, run: Run, actuator: Actuator, routine: str) -> None:
        """The run plays by the pad when the game is in controller mode (macros/pad.py `input_policy`: the game's mode
        followed, never changed; Abort when the routine cannot be played in it now). The keys' actuator is told the
        mode either way: it presses no mouse button in controller mode."""
        play = self.pad_play
        if play is None:
            return
        actuator.mode = play.mode
        mode = play.mode()
        if self.settling:
            # The request made again after a flip (`again`): the flip under way is waited out, not refused
            self.settling = False
            ends = time.monotonic() + FLIP_SETTLE
            while mode is not None and mode.pending and time.monotonic() < ends and not run.cancelled.is_set():
                run.cancelled.wait(FLIP_POLL)
                mode = play.mode()
        if not input_policy(mode, enabled=play.enabled):
            actuator.keyboard_run = True  # the game leaving keyboard mode stops it (actuator.py `guard`)
            return
        pad = PadActs(run, PadActuator(play.device, play.mode, actuator), play.controller, play.bindings, play.route)
        run.pad = pad
        run.hovered = pad.target
        LOG.info('Macro: %s in controller mode, by the pad', routine)

    def pursues(self, run: Run, key_names) -> bool:
        """With the pursuit on for some build: the teleport press made by one pass of attack mode's decision
        (hunting/moves.py `pursue_once`); whether it was. A press whose goal is a fight turns the mode on, unless the
        player's toggle turned it off (rca/2026-10-13/kp4-findings.md §1, §2.8)."""
        walker = self.hunter
        if walker is None or not any(build.settings.pursuit for build in (*self.builds, self.fallback) if build):
            return False
        ready(run)  # the run's first look that shows the character names the build (`choosing`)
        wants = not self.attack_declined
        found = walker.pursue_once(run, key_names, attacking=self.attack_mode or wants)
        if found is None:
            return False
        if found.goal is not None and found.goal.do == FIGHT and wants:
            self.attack_mode = True  # the mode follows this step (`_follow`)
        return True

    def staged(self, run: Run, key_names, plain: Callable[[Target | None], None]) -> None:
        """One press of the stage the level is at (macros/route.py `press`); `plain` is the step toward the
        card's mark for a level or a stage without one of its own."""
        walker = self.hunter

        def leave_the_game(run: Run, key_names) -> None:
            self.attack_mode = False  # as the macro request ends it
            self._end_run('the game is left')
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

    def at_the_way_on(self, player: Player) -> bool:
        """Whether the route's stage on the character's level is its way on (a door, stairs, a portal) and the
        character is within DOOR_NEAR of its mark, where a level run ends (pursuit.py `to_the_door`)."""
        staged = route.staged(self.progress, player.area)
        card = self.target() if self.target is not None and staged is not None and staged[1].to else None
        if card is None or staged is None or card.area != player.area or card.label != staged[1].mark:
            return False
        return math.dist((player.x, player.y), spot_of(card)) <= DOOR_NEAR

    def _teleport_step(self, run: Run, key_names) -> None:
        """One teleport press with no pursuit to make it: a step of the level's stage (`staged`), else the plain step.
        Also the Andariel loop's press through the stairs."""
        walker = self.hunter

        def empty(target: Target, run=run) -> bool:
            # A chest mark with no chest shown at it is done with (route.note_empty; the player, 2026-10-16).
            return route.note_empty(run, target, self.progress, self.marks)

        def plain(card: Target | None, run=run, walker=walker) -> None:
            drop = worth_a_stop(run) if walker is not None else None
            if walker is None:
                step_toward(run, card, key_names, empty=empty)
            elif drop is not None:
                # The step does not leave a valuable behind: this press takes it, the next hops.
                LOG.info('Macro: the teleport step takes %s first', drop.label)
                pick_up(run, walker.level() if walker.level is not None else None, key_names, lambda: None)
            elif card is not None and walker.boss_step(run, card, key_names):
                pass  # the boss stands where its mark has no shot at it: the step went for the boss
            else:
                step_toward(
                    run,
                    card,
                    key_names,
                    lambda target: walker.foot_step(run, target, key_names),
                    lambda target, player, spot: walker.warp_hop(run, target, player, spot, key_names),
                    empty=empty,
                )

        self.staged(run, key_names, plain)

    def _identify_loot(self, run: Run, items: Sequence) -> None:
        # Mass identify at Deckard Cain (the player, 2026-10-17: "we need to perform mass identify at decard cain"),
        # the Tome of Identify the fallback (macros/cain.py, macros/junk.py)
        try:
            done = identify_all(run, items)
        except Abort as stop:
            if cut(run, stop):
                raise
            LOG.info('Macro: identify: Cain: %s: the tome instead', stop)
            player = run.world().player
            key = action_key(self.saved_games, player.name, INVENTORY) if player is not None else None
            pack = run.reads.carried()
            inside = {i.unit_id for i in pack.items} if pack is not None else set()
            try:
                done = len(identify(run, key, [i for i in items if i.unit_id in inside])) if key else 0
            except Abort as again:
                if cut(run, again):
                    raise
                LOG.info('Macro: identify: %s', again)
                return
        units = {item.unit_id for item in items}
        if done and run.seen(lambda w: units <= set(self.verdicts()), VERDICT_SECONDS) is None:
            LOG.info('Macro: identify: %d of %d appraised in time', len(units & set(self.verdicts())), len(units))
        pack = run.reads.carried()
        if pack is not None:
            for item in (*pack.items, *pack.in_cube):
                if item.unit_id in units and item.unit_id in self.verdicts():
                    LOG.info('Macro: identify: appraised %s at (%d, %d): %s', named(item), item.x, item.y,
                             self.verdicts()[item.unit_id])  # fmt: skip
        run.say(f'Identified {done}')

    def _shared_town_visit(
        self,
        run: Run,
        exit: Exit,
        transmute_gems: Callable[[frozenset[int]], tuple[int, int]] | None = None,
    ) -> Contract:
        """The town visit (macros/visit.py `visit`) for the loop's items (its `own`: the player's protected cells,
        macros/volatile.py)."""

        def inventory_key() -> str | None:
            player = run.world().player
            return action_key(self.saved_games, player.name, INVENTORY) if player is not None else None

        def identify_loot(items: Sequence) -> None:
            self._identify_loot(run, items)

        own = self.loop.own
        if own is None:
            raise Abort("the player's items are not told apart yet")
        hands = Hands(inventory_key, identify_loot, lambda items: junk_of(items, self.appraise),
                      lambda: run.reads.stash_view(), transmute_gems)  # fmt: skip
        needs = Needs(keys=self.loop.kind.keys, portals=self.loop.portal or portal_source(run))
        done = visit(run, hands, needs, own, exit, full=frozenset(self.loop.full),
                     waited=self.loop.repair_waited(), memory=self.stash_memory)  # fmt: skip
        if done.full != frozenset(self.loop.full):
            self.loop.full = set(done.full)
            self.loop.keep_full()
        if done.repair_failed:
            self.loop.repair_failed = self.loop.games
        return done.contract

    def perform(self, run: Run, actuator: Actuator, routine: str, key_names) -> None:
        """One routine on the run made for it (`_execute`), by the build chosen at its first look (`choosing`)."""
        self.choosing(run)
        if self.hunter is not None:
            self.hunter.bearings = Bearings(self.progress, self.target, self.marks, self.supers)
        if routine == TELEPORT and self.pursues(run, key_names):
            pass  # one pass of the pursuit's decision made the press (hunting/moves.py `pursue_once`)
        elif routine == TELEPORT:
            self._teleport_step(run, key_names)
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
                    # The route's bosses are dead: nothing is sought; the press is the route's (the ground called
                    # clean, then the game left), as the teleport key's is.
                    self.staged(run, key_names, lambda card: None)
                    return
                if player is not None and self.at_the_way_on(player):
                    # At the route's door the press goes through (rca/2026-10-15/kp1-door-findings.md).
                    self.staged(run, key_names, lambda card: None)
                    return
                stepped.append(hunter.step(run, key_names))

            pick_up(run, level, key_names, otherwise, threat(run))
            if stepped:
                self.attack_mode = True  # nothing to pick up or open: a seek step, the mode follows
        elif routine == LOOP:
            self.loop.marks = self.marks
            note_view(run, self.stash_memory)  # the stash as read, once a game in the Fortress (town-plan.md step 0)
            if self.loop.make_room:
                self.loop.make_room = False
                world = run.world()
                key = action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None
                if key is not None and self.loop.own is not None:
                    try:
                        # A key stack out of the 2 x 4 block first: the room is often there already, in pieces
                        arrange_keys(run, key)
                        stash(run, key, self.loop.own)  # the loop's items into the cube: room for what lies there
                    except Abort as stop:
                        if cut(run, stop):
                            raise
                        LOG.info('Macro: loop: no room made in the cube: %s', stop)
            if self.loop.drop_room:
                self.loop.drop_room = False
                world = run.world()
                key = action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None
                if key is not None and self.loop.own is not None:
                    try:
                        gone = drop_for(run, key, self.loop.own, SURE_BLOCK)
                    except Abort as stop:
                        if cut(run, stop):
                            raise
                        LOG.info('Macro: loop: no item dropped: %s', stop)
                    else:
                        if gone is not None:
                            SHUNNED[gone.unit_id] = run.clock() + DROPPED_SECONDS  # not taken up again this game
            if actuator.keys.focused_window_rect() is None:
                # The game's window lost the focus (the player at another window): nothing can be clicked, so the loop
                # waits, and the watchdogs (`poll`) count none of it
                LOG.info('Macro: loop: waiting for the game window to have the focus')
                self.loop.waiting = True
                try:
                    while actuator.keys.focused_window_rect() is None:
                        if run.cancelled.wait(FOCUS_POLL):
                            raise Cancelled
                finally:
                    self.loop.waiting, self.loop.seen, self.loop.moved = False, None, None
                LOG.info('Macro: loop: the game window has the focus again')
            if self.hunter is not None:
                # Teleport while the gold pays for the staff's charges (macros/loop.py `teleports`), and always when it
                # is the character's own (Enigma: no charge, no swap)
                own = run.reads.own_teleport()
                looped = LOOPED_TELEPORT if self.loop.teleports or own else LOOPED
                if own and self.hunter.looped is not looped:
                    LOG.info("Macro: loop: Teleport is the character's own: in every move")
                self.hunter.looped = looped

            self.loop.leg(
                run,
                key_names,
                self.progress,
                self._loop_hands(run, key_names),
                item_stats=self.item_stats,
                shown=self.stash_memory,
            )
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
