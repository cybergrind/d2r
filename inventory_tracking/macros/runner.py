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
  (pickup.py, hunting/moves.py `step`); inside a fight also a step to a better stand.

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
PICKUP = 'pickup'  # the pickup step: pick up what is worth it, else a seek step (pickup.py)
# The HUD's word for the loop's pickup mode (macros/pickmode.py), with the loop on
LOOP_WORDS = {SURE: 'LOOP SURE', TRADE: 'LOOP TRADE', REGULAR: 'LOOP ALL'}
TRANSMUTES = 3  # a full gem stack's transmutes in one stash visit, at most (macros/cube.py `transmute`)
PICK_SLACK = 3  # pickups past the parked gems' count before the ground is taken for clear (`transmute_gems`)
MAKE_ROOM_AFTER = 5.0  # seconds stood by a valuable with no room before the loop makes room in the cube
FOCUS_POLL = 0.5  # seconds between looks for the game window's focus while the loop waits for it
DROPPED_SECONDS = 600.0  # an item dropped for a valuable's room is not taken up again for this long (a game)
VERDICT_SECONDS = 4.0  # for the identify watcher's appraisals of the items just identified (it polls once a second)
LOOP = 'loop'  # the KP_6 loop's toggle (Lower Kurast, Andariel); a run of it is one leg (macros/loop.py)
STEPS = frozenset((TELEPORT, HUNT_ELITES, PICKUP))  # one press is one step; the same key queues another
# A terror zone's full clear that ends at a door goes on through it with no press (the player, 00:27 on 2026-10-18:
# "yes, go to next level without press"; up to 21 s and 50 s waited at doors that night): the teleport key's press
# the player made there, then, the level changed and terrorized, the pickup key's that runs it. Pressed ONWARD_PAUSE
# after; the door not gone through within ONWARD_SECONDS, nothing more is pressed.
DOOR_PRESS = 'going through takes a press'
ONWARD_PAUSE = 0.3
ONWARD_SECONDS = 20.0
ATTACK = HUNT_ANY  # the attack mode toggle
# What waits for the run working now, the first to go first: where the player wants to be, then what
# to fight, then the macro, then what lies on the ground.
PRIORITY = (TELEPORT, HUNT_ELITES, PREBUFF, PICKUP)
# Seconds after its press a request is still worth beginning, and a hop still worth its key (user,
# 2026-10-12: "teleporting after 2 seconds is way too late, maybe even lower"). Of the teleport
# presses that waited for a step, 90% had their key within 0.48 s and the slowest two took 0.7 and
# 1.5 s (21:26 and 21:35 on 2026-10-11). The pickup step that waits for a fight to end has no limit.
EXPIRES = {TELEPORT: 1.0, HUNT_ELITES: 1.5, PREBUFF: 3.0, PICKUP: 2.0}
# Units from the route's door within which a pickup press with nothing to pick up is the route's step, the one that goes
# through (rca/2026-10-15/kp1-door-findings.md): an object's click range (goals.py USE_NEAR), as a level run ends at a
# door either within its PLACE_NEAR or where the navigator has no step left toward it.
DOOR_NEAR = USE_NEAR
# The stops a lack of room explains (`_loop_stopped`: room made, a trip to town, an item dropped): the pickup's and the
# pursuit's "inventory full", "no room", and the stand-by by a valuable ("has not moved")
AT_DROP_UNITS = 3.0  # a trip back to a valuable this near is at it: no move to it first
ROOM_WORDS = ('no room', 'inventory full', 'Inventory full', 'has not moved')
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
# A run the game's input mode flipped under ends, and the same request starts again in the new mode (`_guarded`,
# actuator.py `Flipped`). Its start waits up to FLIP_SETTLE for the flip to be over: the game of 22:04 on 2026-10-14
# had its four flips done 10-12 ms after they were asked (the probe's `Input mode:` lines). FLIPS_AGAIN restarts within
# FLIPS_WINDOW seconds: a mode that keeps flipping stops the run instead.
FLIP_SETTLE = 1.0
FLIP_POLL = 0.02
FLIPS_AGAIN, FLIPS_WINDOW = 3, 10.0


def classify(why: object) -> Cause:
    """The cause of the stop `why` (actuator.py `Cause`), for `_loop_stopped`: the one its raise named; with none, told
    as the stop rules told it before causes (2026-10-18): the player's hand by the type (`Hand`), a lack of room by the
    message's words (ROOM_WORDS, "has not moved" the watchdog's stand), the Gheed's carry-one refusal by the type
    (`Refused`, after the words: a refusal whose message names no room was never room), the rest 'other'. The words are
    the fallback only, until every raise the room rules answer names its cause (rca/2026-10-18/
    arch-loop-orchestration.md Option A)."""
    if isinstance(why, Abort) and why.cause is not None:
        return why.cause
    if isinstance(why, Hand):
        return 'hand'
    said = str(why)
    if 'has not moved' in said:
        return 'stall'
    if any(word in said for word in ROOM_WORDS):
        # Said so that a day of logs shows whether the words can go (cleanup phase 3, 2026-10-19)
        LOG.info('Macro: loop: a stop with no cause read as room by its words: %s', said)
        return 'room'
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
        # The level and clock of a terror zone's run that ended at a door (`_run_over`); the level the last poll read
        self.onward: tuple[int | None, float] | None = None
        self.area_seen: int | None = None
        self.supers: Callable[[int], list[tuple[float, float]]] | None = None  # terror tracker's `supers`
        # what each belt column last held this game, across presses: an emptied healing column stays one
        # (rca/2026-10-13/potions-findings.md, step 1); every run's loot carries it (`Loot.columns`)
        self.belt = BeltKept()
        # the items the player put down this game (game/kept.py `PutDown`): out of every run's loot, and of the HUD's
        # ground marks (the service hands `put_down.at` to loot/watch.py)
        self.put_down = PutDown()
        # skill -> clock time of its last cast that took, across runs (`Run.lasting`, macros/buffs.py `took_of`): the
        # prebuff's Consume, which attack mode renews before a boss's fight rather than let it end inside it
        self.lasting: dict[int, float] = {}
        # when the healer (`make osd`) last gave the mercenary a potion of a kind: its ledger, read (`Run.given`;
        # macros/drinking.py keeps the character's own gap for those), and written only by the drinker's claim of the
        # character's potion before its key (`Run.ledger`, automation/ledger.py `PotionLedger.claim`)
        self.healer: PotionLedger | None = None
        with suppress(OSError):
            self.healer = PotionLedger(OSD_LEDGER)
        self.working = False  # a run is acting (the thread lives on a while to show its last card)
        self.routine = PREBUFF
        self.generation = 0
        self.warning: tuple[str, float] | None = None  # (text, the clock it was given at)
        self.standing = False  # the warning is the level run's stand by a valuable with no room (`_stand_by`)
        self.attack_mode = False  # the attack run is wanted, now or once the current step is done
        # The player's toggle turned the mode off and nothing of theirs has turned it on since: a press of
        # the teleport key whose goal is a fight leaves it off (read with the pursuit on only: `pursues`)
        self.attack_declined = False
        self.closed = False  # `close` was called: nothing starts any more
        # The Lower Kurast loop (KP_6, macros/loop.py): on, it is what follows every run that nothing else follows.
        self.loop = Loop(store=loop_items)
        self.loop.forget = self._forget_given_up  # the Gheed's swap's GHEED_STASH: the level run tries the charm again
        # the game whose stash view was logged, the shared page shown last (macros/visit.py `Remembered`)
        self.stash_memory = Remembered()
        self.where: tuple[float, float] | None = None  # where the character was at the last poll (`_place`)
        self.dead_mode: int | None = None  # the character's mode at the last poll (`_dead`)
        self.life_seen: tuple[int, int] | None = None  # (life, max life) at the last poll (`poll`: loop.py `beset`)
        self.valuable_left: Callable[[], str | None] = self._valuable_left  # (tests give their own)
        self.carried_now: Callable[[], Pack | None] = self._carried_now  # the inventory now, for `_gheeds_swap`
        # An item unit's stats, from the run's own memory (world.GameMemory.item_stats): a Gheed's Fortune's Magic Find
        self.item_stats: Callable[[int], dict[int, int]] | None = None
        # The valuables the loop has seen this game and not yet off the ground (macros/sightings.py), and the items the
        # ground census has said (game/memory.py `_census`), shared by every GameMemory the runner makes
        self.sightings = Sightings()
        self.ground_seen: set[tuple[int, int]] = set()
        # The appraisal of each item the identify watcher saw identified, by unit id (identify/service.py
        # `IdentifyWorker.verdicts_now`, set by the service): the loop's junk (macros/junk.py)
        self.verdicts: Callable[[], dict[int, str]] = dict
        # The verdicts of carried, identified items by unit id, read now (`IdentifyWorker.appraise`): the junk judged at
        # each look in the fortress (macros/junk.py `junk_of`)
        self.appraise: Callable[[list[int]], dict[int, str]] = lambda units: {}
        self.resuming = False  # the loop was on before the service restarted (`resume`): turned on at the next poll
        # The loop's pickup mode (macros/pickmode.py), switched by a double press of KP_6; the presses of KP_6 not
        # judged yet (`_loop_tap`) and the timer that judges them once their window is over
        self.pickup_mode = MODES[0]
        self.loop_taps: list[float] = []
        self.loop_timer: threading.Timer | None = None
        self.shut = threading.Event()  # set by `close`: a run's card wait ends with it
        self.trace = trace or Trace()  # how long each press takes (latency.py)
        # the requests whose run has not begun: a step's own key during it, a step during attack mode (waiting.py)
        self.queue = Waiting(PRIORITY, self.trace)
        self.deadline = math.inf  # the run working now is worth its input until then (EXPIRES)
        self.press: Press | None = None  # the press of the run working now
        self.hurry: Callable[[], None] | None = None  # the service reads the level now (teleport.card_for)
        # told the seconds of each look a run takes at the game (the service's load meter, appraisal/load.py)
        self.looked: Callable[[float], None] | None = None
        self.quiet_until = -math.inf  # attack mode resumes no sooner (TRAVEL_QUIET)
        # the combat recorder's `note` (takes/record.py): each request and each line said goes into the take
        self.noted: Callable[..., None] | None = None
        # The pad and the game's input mode, from the service (macros/pad.py): a run in controller mode plays by
        # the pad. None: every run plays by the keys and the mouse, as before.
        self.pad_play: PadPlay | None = None
        self.flips: list[float] = []  # when a run was made again after a flip of the input mode (`again`)
        self.settling = False  # the next run's start waits for a flip under way to be over (`play_by`)
        self.lock = threading.RLock()  # every transition: a request, a run's end and its successor, shutdown

    def request(self, requested_at: float, now: float, routine: str = PREBUFF, **notes: object) -> bool:
        """A player/API request; autonomous continuation uses the private dispatch path."""
        return self._dispatch(requested_at, now, routine, autonomous=False, **notes)

    def _dispatch(self, requested_at: float, now: float, routine: str, *, autonomous: bool, **notes: object) -> bool:
        """Start `routine` (PREBUFF or a step), or toggle attack mode (HUNT_ANY). While a run works, a
        request cancels it, except a step's own request during the step (one more step) and a step
        during attack mode (the mode pauses for it and resumes after; the pickup step waits for the
        fight); the macro request during attack mode ends the mode and runs the macro once it has stopped."""
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
                self.attack_declined = False  # for the game, not by the toggle: the next game's fights want it
                self._end_run('the macro request')
            if routine == HUNT_ELITES:
                self.attack_mode = True  # the mode follows the seek step
                self.attack_declined = False
            # Good until: the limit counts from the press, on the clock the queue reads.
            until = time.monotonic() + EXPIRES.get(routine, math.inf) - (now - requested_at)
            if routine == TELEPORT and self.working and self.routine == ATTACK and self.pursuit:
                # The pursuit (macros/pursuit.py): the press is posted to the mode, which goes for what
                # the key means at its next look. Nothing is cancelled, the sweep is not ended, and no
                # quiet follows: a press that resolves to "fight here" costs the fight nothing.
                assert self.hunter is not None
                self.hunter.hand_over = self._hand_over
                self.hunter.post(Pursuit(TELEPORT, time.monotonic() - (now - requested_at)))
                press.mark('accepted')
                self.trace.close(press, outcome='posted to attack mode')
                return True
            if routine == PICKUP and self.pursuit:
                # The pickup key with the pursuit on (macros/pursuit.py, the leash): one press runs the
                # route of this level to its end through attack mode's own loop, which it turns on as the key
                # always did (the player, 2026-10-13: "one press of KP_1, then it runs the whole level
                # automatically"; "KP_1 should enable auto-attack"). A step working now is followed by the
                # mode; a press during the run only renews it.
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
        """The sweep found something to pick up (hunting/sweep.py `gather`): the pickup step follows the mode's
        pause."""
        with self.lock:
            if not self.queue.entries and not self.closed:
                self.queue.put(PICKUP)

    @property
    def run_badge(self) -> str | None:
        """The HUD's words for the run mode (macros/runmode.py `badge`): shown for a full clear of the level the
        mode last looked at; and with the loop on, its pickup mode (`LOOP_WORDS`). None when neither shows."""
        words = (
            badge(self.hunter.mode) if self.hunter is not None else None,
            LOOP_WORDS[self.pickup_mode] if self.loop.on else None,
            self.loop.kind.name.upper() if self.loop.on and self.loop.kind.badge else None,
        )
        return ' '.join(word for word in words if word) or None

    @property
    def pursuit(self) -> bool:
        """Whether the pursuit loop is on (`BuildSettings.pursuit` of the build the last run played, the
        one the hunt plays), with a hunt to make it."""
        return self.hunter is not None and self.build is not None and self.build.settings.pursuit

    def _hand_over(self, routine: str = TELEPORT) -> None:
        """The key posted to the mode is the route's own step's after all (hunting/judging.py `defer`: a door, the
        loot, the leaving), or its own routine's: that routine (the teleport or the pickup step) follows
        the mode's pause."""
        with self.lock:
            if not self.queue.entries and not self.closed:
                self.queue.put(routine, time.monotonic() + EXPIRES.get(routine, EXPIRES[TELEPORT]))

    def _run_over(self, why: str) -> None:
        """A level run ended by the hunt itself (hunt.py `end_run`: what is left of the route is not the run's, the
        character died). With the loop on, the attack mode its chests' leg turned on ends with the run, and the loop's
        next leg follows (`_follow`); the mode went on sweeping before, until the player pressed KP_6
        (rca/2026-10-16/loop-chests-findings.md §2). From the run's thread."""
        with self.lock:
            if self.loop.on and self.loop.kind.agenda and why != 'the level was left':
                # A terror zone kind's level run ended by itself: its own level worked (macros/agenda.py `Agenda.ran`);
                # one that ended because the level was left worked nothing
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
        """The loop's chests leg: the KP_1 level run, as the pickup key starts it (`request`), followed by attack mode;
        its end is the leg's (`_run_over`). `rush`: past what does not attack (the chests, the Catacombs' stairs); not
        for Andariel's fight. `agenda`: a terror zone kind's run, its targets the agenda's (macros/goals-plan.md)."""
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
        """The way on (stairs, a door): at it, what lies there first, then the press through (a level run ends at a
        warp: going through takes a press, macros/pursuit.py `to_the_door`); else the level run to it. Not before what
        the run passed by on this level is taken: the level is not come back to (a Sol Rune left for 2 hostiles near
        it, then the stairs, 11:52:00 on 2026-10-18)."""
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
            # The item labels on before a level run: what lies on the ground is seen (routines.py `show_items_on`)
            world = run.world()
            name = world.player.name if world.player is not None else None
            show_items_on(run, show_items_key(self.saved_games, name) if name else None)

        agenda = self.loop.kind.agenda

        def level_run() -> None:
            if hunter is None:
                raise Abort('no level guide to hunt with')
            labels()  # the item labels on before a level run (the player's hard rule)
            if agenda:
                self._loop_level_run(hunter, rush=False, agenda=True)  # the terror zone kinds: the agenda's targets
            else:
                self._loop_level_run(hunter)

        def way_on() -> None:
            self._way_on(run, key_names, take_one, level_run)  # Andariel's Catacombs rushed; a zone's with the agenda

        def fight() -> None:
            if hunter is None:
                raise Abort('no level guide to hunt with')
            labels()
            self._loop_level_run(hunter, rush=False)

        def take_one() -> bool:
            level = hunter.level() if hunter is not None and hunter.level is not None else None
            # The loop's press holds a valuable it has no room for, a plain one too (macros/lootpolicy.py
            # `NO_ROOM_PLAIN`; the player, 2026-10-18 17:50: "we should stop and clear inventory with our designated
            # town routine"): its stop is cause 'room', and the room rules (`_loop_stopped`) make the room: the
            # cube, then a trip to town and back through the portal, and the next press takes it
            if pick_up(run, level, key_names, lambda: None, threat(run), looped=True):
                return True
            # Nothing to pick up here: a valuable seen this game and not picked up is gone back for, so none is
            # left behind (routes/lower-kurast-loop-plan.md §14: a Flawless Emerald seen in a flight, 08:58:34)
            return self._fetch(run, level, key_names)

        def inventory_key() -> str | None:
            world = run.world()
            return action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None

        def transmute_gems(full: frozenset[int]) -> tuple[int, int]:
            # A full stack's flawless gems, kept (never sold), three at a time into a perfect one by the cube (the
            # player, 2026-10-17: "for gems - we need to cube 3 flawless -> perfect"), standing at the stash; the
            # visit's stash stop takes the perfect gem next. What the inventory has no room for while the cube is
            # emptied is put down and picked up again after (the player, 09:53 on 2026-10-18: "drop on the ground
            # then pickup and move to cube"): 19 gems kept, no transmute had the room, a trade session every game
            # (09:22-09:45). How many were made, how many put down are still on the ground.
            key = inventory_key()
            if key is None:
                return 0, 0
            parked: list[int] = []

            def staying() -> frozenset[tuple[int, int, int]]:
                # the cube takes the inventory's loop items for the room to pick the parked ones up: not the full
                # stacks' runes and materials (for Jamella, put down)
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
                        stash(run, key, staying())  # the inventory's into the cube: room to pick them up
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
                # A kept gem still carried after the transmutes (a fourth of a kind: at 07:26 on 2026-10-19 it
                # stayed in the block, "short of the contract: block 2x4 taken") goes into the emptied cube, where
                # it waits for its next three; the stash stop leaves a full stack's gem there
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
        """A level run of the pickup key ends with attack mode (macros/pursuit.py, the leash): the mode
        off by the toggle or on its own, the macro request, the game left, shutdown."""
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
        """`loot` (the loop's pickup's drops) noted in the game's sightings (macros/sightings.py), the loop on and the
        character in Lower Kurast (the loop's town reads, a repair's gold, are no level of its pickup)."""
        if self.loop.on and memory.where_area in self.loop.kind.levels:
            self.sightings.update(loot, memory.where, memory.where_area, time.monotonic())
        return loot

    def _fetch(self, run: Run, level, key_names) -> bool:
        """A trip back to a valuable the loop saw and no press has picked up (macros/sightings.py `fetch`); whether
        one was made. `Abort` when one is not picked up after its trips back: the leg stops, and the guard
        (`_valuable_left`) keeps the game for the player."""
        player = run.world().player
        if player is None:
            return False
        trip = self.loop.trip
        if trip is not None and self.loop.returned == trip and self.loop.forgiven != (trip, self.loop.trips):
            # Back from a trip for room: its valuables' trips back begin again, at each trip's return (the player,
            # 2026-10-18 16:50: "one game can do several trips to the town")
            self.loop.forgiven = (trip, self.loop.trips)
            self.sightings.again()
        return self.sightings.fetch(
            (player.x, player.y),
            player.area,
            time.monotonic(),
            lambda found: self._go_back(run, found, level, key_names),
        )

    def _go_back(self, run: Run, found, level, key_names) -> None:
        """A trip back to `found`: brought within a click (`approach`, the whole way), its give-up by the pickup
        lifted so the press after tries it again, and, within a click but not at it, a move to it by the movement in
        hand, so the clicks come from another footing (15:53:05 on 2026-10-18: a set Ring 5 away under the pointer, 11
        clicks from one place took nothing and the character did not move; both trips back found it given up by the
        pickup, went nowhere in 0.2 s, and the loop stopped)."""
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
        """A press of KP_6 at `at` (the request's clock), judged with the presses around it once DOUBLE seconds pass
        with no other (`_judge_loop_taps`), as KP_1's run mode judges its double press (macros/runmode.py): one press
        turns the loop on or off, exactly two switch the pickup mode (the player, 2026-10-16), more switch nothing. A
        group whose window closed before this press is judged first. Under the lock."""
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
            # run we're going to run"), for a start in the Fortress or the lobby: elsewhere the character's place says
            kinds = list(loop_kinds().values())  # the terror zone kinds once promoted (macros/tzloop.py ENABLED)
            self.loop.kind = kinds[(kinds.index(self.loop.kind) + 1) % len(kinds)]
            self.loop.chosen = True  # by hand: no place overrides it
            self._say(f'Loop run: {self.loop.kind.name}')
        else:
            self._say(f'KP_6 pressed {count} times together: nothing switched')

    def _toggle_loop(self) -> None:
        """KP_6: the loop on, from where the character is (a run working now is followed by the loop's first
        leg), or off at once: the run working now is cancelled, the character stays where it is. Under the lock."""
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
        """A leg's stop: the loop leaves the game and goes on (macros/loop.py `recover`), or ends by itself, saying
        why; the rules are macros/stops.py's. Under the lock or from the run's thread."""
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
        """Whether the stop `why` is the Gheed's swap's (macros/charms.py; the player, 2026-10-18 13:39: "picking up
        another gheed ... put our own gheed into SHARED tab"): a unique Grand Charm left on the ground in the Andariel
        loop with the player's Gheed's Fortune carried, whatever the stop's words (at 13:36-13:39 it was a stand-by,
        "the character has not moved for 45 s", and the room rules made room, a trip to town and dropped an item for
        it): the swap is due, once a game; before every room rule. With no 1 x 3 free the cube is tried first (the
        stop is the swap's still: `make_room`), then the swap all the same (the player, 2026-10-18 16:50: "refused
        grand charm - should cause a trip"). With the player's already in the stash and the new one still not taken,
        theirs is fetched back first (`CHOOSE`)."""
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
                # Room first, in the cube (a block for the new one, and for the player's to come back to)
                loop.make_room, loop.room_tried = True, game
                LOG.info("Macro: charms: %s; %s lies on the ground, the player's Gheed's Fortune carried, and no %d x "
                         '%d free: room is made in the cube first', why, left, *ours.size)  # fmt: skip
                return True
            # The cube tried: the swap all the same, the trip to town it is (the player, 2026-10-18 16:50: "refused
            # grand charm - should cause a trip"; the room rules pass a refusal by, and the loop stood by the charm).
            # The player's goes onto a shared page and its own block takes the new one (macros/charms.py `choose`)
            LOG.info("Macro: charms: %s lies on the ground, the player's Gheed's Fortune carried, no %d x %d free and "
                     "the cube tried: the swap all the same, the player's block takes the new one", left,
                     *ours.size)  # fmt: skip
        loop.swap_due = True
        LOG.info("Macro: charms: %s; %s with the player's Gheed's Fortune carried at (%d, %d) and room for another: "
                 'the swap is due', why, left, ours.x, ours.y)  # fmt: skip
        return True

    def _carry_one(self, refused: Refused) -> bool:
        """A unique Grand Charm refused for the Gheed's Fortune carried (macros/pickup.py `Refused`) outside the loop's
        own routine (the level run's pickup, hunting/choice.py `carry_one_swap`; the pickup step attack mode asked for):
        whether the swap is due for it (`_gheeds_swap`, the same rules as a stop's); the run stops for it then. With the
        loop off, or no swap (once a game, no room), False: the run's own rules go on."""
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
        """The attack mode toggle: the mode on or off. On while a step works, it follows the step; off
        while it works, it is cancelled. Under the lock (`request`)."""
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
                    # only the stand-by by a valuable (hunting/choice.py `stay_by`), in a game: a candidate merely left
                    # on the ground (pickup.py's warning) warned on into the lobby and cancelled the next game's
                    # creation twice, the loop stopped (12:45:39 on 2026-10-17)
                    and self.standing
                    and game is not None
                    and now - warned[1] > MAKE_ROOM_AFTER
                    and self.loop.on
                    and self.loop.room_tried != game
                ):
                    # Stood by a valuable with no room (hunting/choice.py `stay_by`): made room for before the watchdog;
                    # the Gheed's swap first when it is one (`_gheeds_swap`)
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
                    # Hit standing outside a fight (a leg's wait or spin, attack mode off): the game is left at once
                    # (the player, 2026-10-19: "we stood still while under attack and almost died ... we must not die
                    # or we lose exp and our gear"; rca/2026-10-19/near-death-findings.md)
                    life = self.life_seen or (0, 0)
                    why, cause = f'the character is hit standing outside a fight (life {life[0]}/{life[1]})', 'beset'
                elif self.loop.on and game is not None and self.loop.still(self.where, now, game):
                    why, cause = f'the character has not moved for {STILL_SECONDS:.0f} s', 'stall'
                if why is not None:
                    # The loop is stuck (macros/loop.py GAME_SECONDS, STILL_SECONDS): the run is cancelled, the next
                    # leg leaves the game. The stand names its cause (`ROOM_CAUSES`: a lack of room, ruling pending)
                    self._loop_stopped(Abort(why, cause=cause))
                    self.attack_mode = False
                    if self.working:
                        self.cancelled.set()
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
        # The guard's "must not leave it" is the policy's (macros/lootpolicy.py `verdict`: every valuable but a
        # candidate for an identify, room or none, shunned or given up; the plain ones with no room by the ruling of
        # 2026-10-18 17:50, as before it)
        found = [
            drop
            for drop in loot.drops
            if verdict(
                drop, GUARD, room=has_room(loot.room, drop.size), shown=drop.unit_id in loot.shown, looped=True
            ).hold
        ]
        if found:
            return found[0].label
        # One seen this game and not read now (out of the client's reach, macros/sightings.py) lies there all the same
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
        """Outside the KP_6 loop (it makes its own room: `_loop_stopped`), the valuables the macro picked up itself
        (pickup.py TAKEN) into the cube; how many went. The player's items, keys, tomes and the cube stay."""
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
        """What a restart of the service carries over (appraisal/service.py `Restart`): the loop on or off, its pickup
        mode."""
        with self.lock:
            return {
                'loop': self.loop.on,
                'pickup_mode': self.pickup_mode,
                'loop_kind': self.loop.kind.key,
                'sightings': self.sightings.state(),  # the valuables seen and still on the ground (sightings.py)
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
                self.loop.chosen = True  # the service's before: kept
            if isinstance(state.get('sightings'), dict):
                self.sightings.restore(state['sightings'])
                # A restart is made for a fix: the valuables' trips back begin again (15:53:19 on 2026-10-18: a Ring
                # left after its 2 trips back would have stopped the restarted loop again at once)
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
        """Shutdown is final: the run is cancelled and nothing follows it (no pending step, no attack
        mode resumed, no queued repeat), and no request starts another."""
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
        """A warning that stays on the card (None takes it back): the next line said does not wipe it.
        user, 2026-10-12: "we should give an active warning that must be visible to the user"."""
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
        """The warning `text` of the level run standing by a valuable it has no room for (engine.Run `stand_by`): the
        watchdog makes room in the cube after MAKE_ROOM_AFTER (`poll`) while it stands."""
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
                # The pickup step attack mode asked for (or a teleport press's) met the carry-one refusal: the mode
                # and its level run end, and the loop's swap leg follows (`_follow`)
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
        """The game's input mode flipped under the run of `routine` (`stop`): the same request is made again, to be
        played in the new mode (`play_by`), and whether it was. Not when the run was cancelled meanwhile, a newer run
        owns the runner, attack mode was turned off, or the mode has flipped FLIPS_AGAIN times within FLIPS_WINDOW.
        Said once a flip (`Macro: input mode flipped …`). Under the lock."""
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
            # As a fresh press of the key: good for its own time from now, the flip's settling on top
            self.queue.put(routine, now + FLIP_SETTLE + EXPIRES.get(routine, math.inf))
        self._start(routine)
        return True

    def _follow(self, routine: str) -> bool:
        """The run of `routine` is over: start what follows it, if anything, and say whether something
        did. A step asked for during attack mode comes first, then the mode a step paused. Under the
        lock, in one piece with `working` going off: a request sees either the run or its successor."""
        self.working = False
        following = self.queue.first()
        if following is None and self.attack_mode and routine != ATTACK:
            following = ATTACK  # the step is done: the mode resumes
        if following is None and self.loop.on:
            following = LOOP  # its next leg, the level run's end among them
        if following is None or self.closed:
            return False
        if routine == TELEPORT and following == ATTACK and not self.pursuit:
            # Not with the pursuit on: a strike begun after the step is given up by the mode itself for
            # the next press's move (hunting/judging.py `key_asks`), so nothing has to be held back for it.
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
        if build.weapons is not None:
            # Every run knows the build's weapon sets, not only the prebuff and attack mode, which set
            # them themselves: the teleport step's "the staff is empty: the main weapons" (hunt.py
            # `empty_hop`, `afoot`) asked a run that held none, and did nothing in the game (12 s with
            # the empty staff in hand through 20 steps, 12:33 on 2026-10-13; the tests' runs had them).
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
        memory.ground_seen = self.ground_seen  # one census across runs: an item is said once (game/memory.py `_census`)
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
                actuator.noted = self.noted  # the pointer check's abort as an event of the take (actuator.py)
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
        """The run plays by the pad when the game is in controller mode (macros/pad.py `input_policy`: the game's
        mode followed, never changed; Abort with the reason when the routine cannot be played in it now). The
        keys' actuator is told the mode either way: it presses no mouse button while the game is in controller
        mode. The controller's own target stands for the unit under the pointer (`Run.hovered`)."""
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
        """With the pursuit on for the build this run plays: the teleport key's press made by one pass of
        the decision attack mode makes (hunting/moves.py `pursue_once`), and whether it was. No look at the game
        is made for it while no build has the pursuit on. A press whose goal is a fight wants the mode
        on after it, as the route's fight stage has it (macros/route.py), unless the player's own toggle
        turned it off: then it stays off, whatever is pressed (rca/2026-10-13/kp4-findings.md §1, §2.8)."""
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
        """Whether the route's stage on the character's level is its way on to another level (a door, stairs, a
        portal) and the character stands within DOOR_NEAR of its mark, where a level run ends (pursuit.py
        `to_the_door`)."""
        staged = route.staged(self.progress, player.area)
        card = self.target() if self.target is not None and staged is not None and staged[1].to else None
        if card is None or staged is None or card.area != player.area or card.label != staged[1].mark:
            return False
        return math.dist((player.x, player.y), spot_of(card)) <= DOOR_NEAR

    def _teleport_step(self, run: Run, key_names) -> None:
        """One press of the teleport key with no pursuit to make it: a step of the stage the level is at
        (`staged`), the plain step without one. Also the Andariel loop's press through the stairs."""
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

        # One step of the stage the level is at (macros/route.py); the plain step without one.
        self.staged(run, key_names, plain)

    def _identify_loot(self, run: Run, items: Sequence) -> None:
        # All at once at Deckard Cain (the player, 2026-10-17: "we need to perform mass identify at decard cain"), the
        # Tome of Identify the fallback for the inventory's (macros/cain.py, macros/junk.py)
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
                    # The route's bosses are dead: nothing is sought any more. The ground is the route's to
                    # call clean, and the press after that leaves the game, as the teleport key's does.
                    self.staged(run, key_names, lambda card: None)
                    return
                if player is not None and self.at_the_way_on(player):
                    # At the route's door (a level run ends there, U13): the press is the one that goes through
                    # (rca/2026-10-15/kp1-door-findings.md), as the teleport key's is.
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
                        # A key stack out of the 2 x 4 block first: the room is often there already, in pieces (a
                        # Unique Brandistock, 12:36 on 2026-10-18); then the loop's items into the cube
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
                # The game's window is not the focused one (the player at another window): nothing can be clicked, and
                # legs tried meanwhile only count up to a stop (01:30:39 on 2026-10-17); the loop waits for it
                LOG.info('Macro: loop: waiting for the game window to have the focus')
                self.loop.waiting = True  # the watchdogs (`poll`) count none of it (01:33:26 on 2026-10-17)
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
