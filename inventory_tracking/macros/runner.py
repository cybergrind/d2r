"""The macro runner inside the service: starts a run per request, cancels the one running, toggles attack mode.

Requests come from the compositor bindings (input/compositor.py) over the appraisal socket: `macro` (routines.py),
`teleport` (teleport.py), `hunt elites` (the seek step), `hunt any` (the active mode: attack or buff mode,
running/buffing.py), `pickup` (pickup.py), `loop` (KP_6).
A run works on its own thread with its own memory handle and X connection; the cancel rules are `_dispatch`'s. The
builds (macros/build.py) are handed in; a run plays the one that claims the character (`choosing`).
`MacroRunner` keeps its state, the requests and the runs' lifecycle; its other methods are module functions in
macros/running/, bound here as class attributes (as hunt.py's in macros/hunting/).
"""

import math
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from pathlib import Path

from inventory_tracking.automation.ledger import OSD_LEDGER, PotionLedger
from inventory_tracking.common import LOG
from inventory_tracking.game.frames import frame_feed
from inventory_tracking.game.kept import BeltKept, PutDown
from inventory_tracking.game.records import Pack
from inventory_tracking.game.stash import SNAPSHOT as STASH_SNAPSHOT, Stash
from inventory_tracking.input.focus import FocusTracker
from inventory_tracking.levels.model import Target
from inventory_tracking.macros import midgame
from inventory_tracking.macros.actuator import Abort, Cancelled, Flipped
from inventory_tracking.macros.buffmode import WORDS
from inventory_tracking.macros.build import Build
from inventory_tracking.macros.charms import Parked
from inventory_tracking.macros.guard import Guard
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.hunting.base import NO_WAY_TO
from inventory_tracking.macros.journey import Journey
from inventory_tracking.macros.kindpick import PICKER_TICK, KindPicker, entries
from inventory_tracking.macros.latency import Press, Trace
from inventory_tracking.macros.loop import ANDARIEL, RECOVERY_PAUSE, Kind, Loop, loop_kinds
from inventory_tracking.macros.merc import MercWatch
from inventory_tracking.macros.pad import PadPlay
from inventory_tracking.macros.pickmode import MODES, next_mode
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.pursuit import FULL, NOTHING_LEFT, Pursuit
from inventory_tracking.macros.runmode import DOUBLE, TERROR
from inventory_tracking.macros.running import (
    buffing,
    execution,
    guarding,
    jump,
    legs,
    merclost,
    recovery,
    room,
    valuables,
    watch,
)
from inventory_tracking.macros.running.base import (
    ATTACK,
    BUFF,
    CARD_SECONDS,
    DOOR_PRESS,
    EXPIRES,
    FLIP_SETTLE,
    FLIPS_AGAIN,
    FLIPS_WINDOW,
    HUNT_ANY,
    HUNT_ANY_PREFIX,
    HUNT_ELITES,
    HUNT_ELITES_PREFIX,
    KIND_PREFIX,
    LOOP,
    LOOP_PREFIX,
    ONWARD_PAUSE,
    PICK_WORDS,
    PICKUP,
    PICKUP_PREFIX,
    PREBUFF,
    PRIORITY,
    REQUEST_PREFIX,
    STEPS,
    TELEPORT,
    TELEPORT_PREFIX,
    THROTTLE,
    TRAVEL_QUIET,
    WARNING_SECONDS,
)
from inventory_tracking.macros.running.recovery import classify
from inventory_tracking.macros.sightings import Sightings
from inventory_tracking.macros.visit import Remembered
from inventory_tracking.macros.waiting import Waiting
from inventory_tracking.routes.progress import Progress


__all__ = [
    'HUNT_ANY',
    'HUNT_ANY_PREFIX',
    'HUNT_ELITES_PREFIX',
    'KIND_PREFIX',
    'LOOP_PREFIX',
    'PICKUP_PREFIX',
    'REQUEST_PREFIX',
    'TELEPORT_PREFIX',
    'MacroRunner',
    'classify',
]

# A run always hands the runner over (rca/2026-10-23/loop-no-legs.md). At 00:41:44 on 2026-10-23 the KP_6 timer's
# "Loop off" card and the cancelled leg's "Macro stopped: cancelled" card were published 2 ms apart: two writers of
# the HUD layer's one temporary file (reports.py `publish`), the second's replace raised FileNotFoundError inside
# `_guarded`'s stop handling, the thread died before `_follow`, and `working` stayed on with no thread. Every KP_6 on
# after it said "Loop on" and made no leg until the player restarted serve (00:43:36). True: the card is published
# one writer at a time and a failed write is logged, never raised into a run (`_show`); a run whose own end raises
# still hands the runner over (`_handed_over`); a request or a KP_6 on that finds `working` with its thread gone says
# so and takes the runner back (`_reclaim`). False: as before
HANDOVER = True
# KIND_ENDS_ZONE_WAIT (2026-10-25, the player ~12:10: "why andariel loop is not working?"): Moo Moo Farm turned at 12:04
# and the loop waited out the zone (tzloop.py `zone_wait`, `Loop.cooling` 1553 s); Andariel picked at 12:08:44 still
# waited "1292 s before the next leg (the next terror zone)", and the player restarted serve. True: a kind picked other
# than the current one keeps at most the recoveries' pause (loop.py RECOVERY_PAUSE). False: the wait stands.
KIND_ENDS_ZONE_WAIT = True


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
        self.card_lock = threading.Lock()  # one card write at a time (HANDOVER); never held while taking `lock`
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
        # The clock the poll or a stop last answered a stand at (watch.py `stood_after_cube` acts only on a later one),
        # and the stand (its warning's clock) whose room rule waits for no hostile near, said once
        self.stand_answered = -math.inf
        self.stand_held: float | None = None
        self.attack_mode = False  # the attack run is wanted, now or once the current step is done
        # The player's toggle turned the mode off: a teleport press whose goal is a fight leaves it off (`pursues`)
        self.attack_declined = False
        # The attack mode key's active mode (running/buffing.py, 2026-10-19): what one press turns on, ATTACK or BUFF;
        # buff mode wanted; the presses not judged yet, their timer, and the mode on before their group
        self.active = ATTACK
        self.buff_mode = False
        self.mode_taps: list[float] = []
        self.mode_timer: threading.Timer | None = None
        self.mode_was: str | None = None
        self.closed = False  # `close` was called: nothing starts any more
        # The KP_6 loop (macros/loop.py): on, it follows every run that nothing else follows.
        # Andariel first (the player, 2026-10-19: "switch loop to the andariel"); a place of another kind still tells
        # The stash's one record (game/stash.py), its snapshot next to the loop's items for the watch tools
        self.loop = Loop(
            store=loop_items,
            kind=ANDARIEL,
            stash=Stash(snapshot=loop_items.parent / STASH_SNAPSHOT if loop_items is not None else None),
        )
        self.loop.forget = self._forget_given_up  # GHEED_STASH: the level run tries the charm again
        # The stand guard (macros/guard.py, 2026-10-22): after a stop of the loop's own, the life and the hostiles
        # watched in the level, the fight in place when hit or a hostile comes near
        self.guard = Guard()
        # the game whose stash view was logged, the shared page shown last (macros/visit.py `Remembered`)
        self.stash_memory = Remembered()
        self.stash_polled = -math.inf  # the stash record's last refresh by the poll (running/watch.py `_stash_poll`)
        self.where: tuple[float, float] | None = None  # where the character was at the last poll (`_place`)
        self.dead_mode: int | None = None  # the character's mode at the last poll (`_dead`)
        self.life_seen: tuple[int, int] | None = None  # (life, max life) at the last poll (loop.py `beset`)
        self.valuable_left: Callable[[], str | None] = self._valuable_left  # (tests give their own)
        self.carried_now: Callable[[], Pack | None] = self._carried_now  # the inventory now, for `_gheeds_swap`
        self.attacker_near: Callable[[], bool] = self._attacker_near  # a hostile by the character, for `_beset_facts`
        # The merc's looks and the belt's, and the town trip they make due (macros/merc.py, running/merclost.py; the
        # player, 2026-10-21 ~19:00: "we have lost merc -> probably better retreat to the town and refill hp potions in
        # the belt"); the look itself (tests give their own)
        self.merc = MercWatch(book=self.loop.merc_trips)  # the trips counted in the loop's (its game's record)
        self.merc_read: Callable[[], merclost.Look | None] = self._merc_read
        # An item unit's stats from the run's memory (GameMemory.item_stats)
        self.item_stats: Callable[[int], dict[int, int]] | None = None
        # Valuables seen this game and still on the ground (sightings.py); the ground census's items (game/memory.py)
        self.sightings = Sightings()
        self.ground_seen: set[tuple[int, int]] = set()
        # The game memory's replayed read patterns by kind of pass, and their prepared calls, across runs
        # (game/memory.py `GameMemory.replay`, 2026-10-23); one run reads at a time
        self.read_patterns: dict[str, list[tuple[int, int]]] = {}
        self.read_prepared: dict = {}
        # The frame reader's feed (game/frames.py FRAMES, 2026-10-23): its process started by the first run, ended
        # with the runner; None: off
        self.frames = frame_feed(lambda text: LOG.info('Macro: frames (p50/p90/max): %s', text))
        # The identify watcher's appraisals by unit id (identify/service.py `verdicts_now`): the loop's junk
        self.verdicts: Callable[[], dict[int, str]] = dict
        # The verdicts of carried identified items, read now (`IdentifyWorker.appraise`, macros/junk.py `junk_of`)
        self.appraise: Callable[[list[int]], dict[int, str]] = lambda units: {}
        self.resuming = False  # the loop was on before the service restarted (`resume`): turned on at the next poll
        # A restart asked for at the loop's next safe point (`hold_restart`, macros/midgame.py): the state it brings
        self.restart_target: dict | None = None
        # The kind asked from the next game before a restart with the loop on: set once the resume turned it on (a
        # turn on takes a pending kind at once, `_toggle_loop`, and the game goes on in its own kind)
        self.resume_pending: Kind | None = None
        # The loop's pickup mode (macros/pickmode.py); the KP_6 presses not judged yet and their timer
        self.pickup_mode = MODES[0]
        self.loop_taps: list[float] = []
        self.loop_timer: threading.Timer | None = None
        # The KP_6 kind picker (macros/kindpick.py; the player, 2026-10-20: "pop some kind of dialogue to chose the mode
        # on 3 clicks"): open while not None, republished by its timer. The HUD layer's publisher and whether a canvas
        # shows it are the service's (appraisal/service.py); without either three presses cycle the kind as before.
        self.picker: KindPicker | None = None
        self.picker_timer: threading.Timer | None = None
        self.picker_publish: Callable[[list], None] | None = None
        self.hud_up: Callable[[], bool] = lambda: False
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
        # A trip for room an activity by hand asked for (running/room.py `Errand`): ROOM follows its run (`_follow`)
        self.errand: room.Errand | None = None
        # The teleport press is a jump to the next goal (running/jump.py; the player, 2026-10-19: "KP_4 - force jump to
        # the next goal"); off: one step a press, as before (the arena's recorded presses). The jump working now.
        self.jumps = True
        self.jumping: jump.Jump | None = None
        # The last jump ended on its own (not by the hand); the last teleport press, on the press's clock: a key held
        # on after the jump's end is that press, not the next (`_dispatch`)
        self.jump_over = False
        self.jump_pressed = -math.inf
        self.lock = threading.RLock()  # every transition: a request, a run's end and its successor, shutdown

    def request(self, requested_at: float, now: float, routine: str = PREBUFF, **notes: object) -> bool:
        """A player/API request; autonomous continuation uses the private dispatch path."""
        return self._dispatch(requested_at, now, routine, autonomous=False, **notes)

    def _dispatch(self, requested_at: float, now: float, routine: str, *, autonomous: bool, **notes: object) -> bool:
        """Start `routine` (PREBUFF or a step), or toggle attack mode (HUNT_ANY). A request cancels the run working,
        except a step's own key during the step (one more step) and a step during attack mode (the mode pauses; the
        pickup waits for the fight); the macro request ends the mode and runs once it has stopped."""
        with self.lock:
            self._reclaim()
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
                if not autonomous:
                    self._guard_disarm("the player's attack mode key")  # the mode is the player's from here
                self._mode_tap(now)  # one press toggles, a pair cycles the active mode (running/buffing.py)
                press.mark('accepted')
                outcome = 'attack mode on' if self.attack_mode else 'buff mode on' if self.buff_mode else 'mode off'
                self.trace.close(press, outcome=outcome)
                return True
            if routine == PREBUFF:
                self.attack_mode = False  # the macro request ends it
                self.attack_declined = False  # the next game's fights want it
                self._end_run('the macro request')
            if routine == HUNT_ELITES:
                self.attack_mode = True  # the mode follows the seek step
                self.attack_declined = False
            # The limit counts from the press, on the queue's clock.
            until = time.monotonic() + EXPIRES.get(routine, math.inf) - (now - requested_at)
            if routine == TELEPORT and self.jumps:
                held, self.jump_pressed = requested_at - self.jump_pressed <= jump.HELD, requested_at
                if held and self.jump_over and self.working and self.routine == ATTACK:
                    # The key held on at the jump's end: the mode fights there, not paused for a jump to where it is
                    press.mark('accepted')
                    self.trace.close(press, outcome='held after the jump: attack mode fights')
                    return True
            posting = routine == TELEPORT and self.working and self.routine == ATTACK and self.pursuit
            if posting and (not self.jumps or self._at_the_fight()):
                # The pursuit (macros/pursuit.py): the press is posted to the mode, nothing is cancelled and no quiet
                # follows, so a press that resolves to "fight here" costs the fight nothing. With the jump, only at the
                # mode's fight (running/jump.py `_at_the_fight`); elsewhere the mode pauses for the jump.
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
                elif self.routine == BUFF:
                    self.cancelled.set()  # buff mode yields to the run's attack mode and resumes after it (`_follow`)
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
                if routine == TELEPORT and self.routine == TELEPORT and self.jumping is not None:
                    self.jumping.extend()  # a press during the jump extends it and queues nothing (running/jump.py)
                    press.mark('accepted')
                    self.trace.close(press, outcome='the jump goes on')
                elif routine in STEPS and self.routine == routine:
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
                elif self.routine in (ATTACK, BUFF):
                    self.cancelled.set()  # the mode pauses for the step, or ends for the macro
                    self._wait(press, f'{"attack" if self.routine == ATTACK else "buff"} mode pauses for it', until)
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
        """The HUD's mode line, `<mode> PICK:<level> NEXT:<goal>` (the player, 2026-10-19): the loop's kind word with
        the loop on, else ATT in attack mode, BUFF in buff mode; the pickup level; the leg or goal working (a full
        clear: `clear`)."""
        running = self._mode_running()
        mode = self.loop.kind.word if self.loop.on else WORDS[running] if running else None
        goal = self._next_goal()
        words = (mode, f'PICK:{PICK_WORDS[self.pickup_mode]}', f'NEXT:{goal}' if goal else None)
        return ' '.join(word for word in words if word)

    def _next_goal(self) -> str | None:
        """The next planned activity: the loop's leg; else, while a run works, its run mode's full clear or its goal."""
        if self.loop.on:
            return self.loop.current
        if self.hunter is None or not self.working or self.routine == BUFF:
            return None  # buff mode has no goal: the hunt's last is stale
        if self.hunter.mode is not None and self.hunter.mode.clear:
            return 'clear'
        goal = self.hunter.pursued
        return goal.label if goal is not None else None

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
            if self.loop.on and self.loop.kind.agenda:
                self._zone_seen()
            if self.loop.on and self.loop.kind.agenda and why != 'the level was left':
                # A terror zone kind's run worked its level (macros/agenda.py `Agenda.ran`), unless it left it
                area = self.hunter.ended_area if self.hunter is not None else None
                self.loop.agenda.ran(area if area is not None else self.area_seen)
                midgame.keep(self.loop)  # the level run in the game's record at once
                # A level done whose run finds nothing more is no way on either: the Throne of Destruction's next level,
                # the Worldstone Chamber, opens only after Baal; its leg was made again every 0.3 s until the repeat
                # guard left the game (04:32:49-04:32:58 on 2026-10-20)
                ended = area if area is not None else self.area_seen
                if why.startswith(NO_WAY_TO):
                    self.loop.agenda.no_way_on(ended)
                elif ended in self.loop.agenda.finished and why.startswith(NOTHING_LEFT):
                    self.loop.agenda.nothing_left(ended)
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

    def _zone_seen(self) -> None:
        """What the run's end tells zone navigation (macros/zonenav.py `LevelState`): the level whose tour last found no
        room left, its rooms read (hunt.py `Hunter.toured`), is explored, whichever level the run ended on (a walk
        across a passage ends it on the next); the level it ended on had its map read when any of its rooms is
        explored (the tracker's `visited_rooms`). Read whatever the end: the zone's verdicts, not the agenda's runs."""
        hunter, agenda = self.hunter, self.loop.agenda
        if hunter is None:
            return
        toured = getattr(hunter, 'toured', None)
        if toured is not None and toured[1] > 0:
            agenda.mapped.add(toured[0])
            agenda.explored.add(toured[0])
        # Each level the run toured to its end, a level left across a passage too (hunt.py `tours_done`), read once
        done = getattr(hunter, 'tours_done', None)
        if isinstance(done, set):
            agenda.mapped |= done
            agenda.explored |= done
            done.clear()
        ended = getattr(hunter, 'ended_area', None)
        area = ended if ended is not None else self.area_seen
        explored = getattr(hunter, 'explored', None)
        if area is not None and explored is not None and explored(area):
            agenda.mapped.add(area)

    def _press(self, routine: str) -> None:
        """A press of the macro's own, as the player's key would make it (`request`)."""
        now = time.monotonic()
        self._dispatch(now, now, routine, autonomous=True)

    def _end_run(self, why: str) -> None:
        """End the pickup key's level run with attack mode (macros/pursuit.py, the leash)."""
        if self.hunter is not None:
            self.hunter.end_run(None, why)

    def _unwait(self) -> None:
        """The pickup step that waited for the fight is not wanted any more (hunting/sweep.py `asked_step`)."""
        with self.lock:
            self.queue.drop(PICKUP, 'not wanted any more')

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
        if self.picker is not None:
            self._picker_taps(count)  # the picker takes the presses while it is open; the loop stays as it is
            return
        if count == 1:
            self._toggle_loop()
        elif count == 2:
            # The pickup level of every loop and activity (macros/pickmode.py; the player, 2026-10-19: "KP_6 - loop
            # on/off, double - switch pickup mode, triple - switch loop type")
            self.pickup_mode = next_mode(self.pickup_mode)
            self._say(f'Pickup: {PICK_WORDS[self.pickup_mode]}')
        elif count == 3:
            # The run's kind (macros/loop.py KINDS; the player, 2026-10-18: "rebuild loop start to accept what type of
            # run we're going to run"), for a start in the Fortress or the lobby: chosen in the picker (2026-10-20)
            self._open_picker()
        else:
            self._say(f'KP_6 pressed {count} times together: nothing switched')

    def _switch_kind(self, kind: Kind, how: str) -> None:
        """The loop's kind chosen by the KP_6 presses, at once (the loop on or off). Under the lock."""
        self._end_zone_wait(kind)
        self.loop.kind = kind
        self.loop.chosen = True  # by hand: no place overrides it
        self.loop.pending = None  # the press wins over a request
        LOG.info('Macro: loop kind: %s (%s)', kind.name, how)
        self._say_kind(kind)

    def _end_zone_wait(self, kind: Kind) -> None:
        """KIND_ENDS_ZONE_WAIT: the next terror zone's wait belongs to the kind that set it (the player, 2026-10-25
        ~12:10: "why andariel loop is not working?": Andariel picked at 12:08:44 after the Moo Moo Farm turn, then
        "waiting 1292 s before the next leg (the next terror zone)"); `kind` other than the loop's keeps the
        recoveries' pause at most. Under the lock."""
        if KIND_ENDS_ZONE_WAIT and kind != self.loop.kind:
            self.loop.cooling = min(self.loop.cooling, time.monotonic() + RECOVERY_PAUSE)

    def _open_picker(self) -> None:
        """Three KP_6 presses: the kind picker on the HUD (macros/kindpick.py). With no canvas to show it, the next kind
        as the presses did before the picker. Under the lock."""
        if self.picker_publish is None or not self.hud_up():
            kinds = list(loop_kinds().values())  # the terror zone kinds once promoted (macros/tzloop.py ENABLED)
            here = kinds.index(self.loop.kind) if self.loop.kind in kinds else -1
            self._switch_kind(kinds[(here + 1) % len(kinds)], 'cycled: no HUD for the picker')
            return
        self.picker = KindPicker(entries(), self.loop.kind, time.monotonic(), pending=self.loop.pending)
        LOG.info('Macro: loop kind picker open: %s highlighted', self.picker.highlighted.name)
        self._picker_tick(self.picker)

    def _picker_taps(self, count: int) -> None:
        """A group of KP_6 presses while the picker is open: one moves the highlight, two choose the highlighted kind,
        three close it. Under the lock."""
        picker = self.picker
        assert picker is not None
        if count == 1:
            LOG.info('Macro: loop kind picker: %s highlighted', picker.move(time.monotonic()).name)
            self._show_picker(picker)
        elif count == 2:
            chosen = picker.highlighted
            self._close_picker(f'{chosen.name} chosen')
            if chosen.kind is not None:  # the coming entries are never highlighted (kindpick.py `_after`)
                self._switch_kind(chosen.kind, 'picked')
        elif count == 3:
            self._close_picker('closed by the key, nothing changed')
        else:
            picker.touch(time.monotonic())
            LOG.info('Macro: loop kind picker: KP_6 pressed %d times together, nothing changed', count)

    def _picker_tick(self, picker: KindPicker) -> None:
        """The open picker republished inside the HUD's lease, until no press for PICK_SECONDS closes it."""
        with self.lock:
            if self.picker is not picker or self.closed:
                return
            if picker.expired(time.monotonic()):
                self._close_picker('no press, nothing changed')
                return
            self._show_picker(picker)
            self.picker_timer = threading.Timer(PICKER_TICK, self._picker_tick, (picker,))
            self.picker_timer.daemon = True
            self.picker_timer.start()

    def _show_picker(self, picker: KindPicker | None) -> None:
        """Publish the picker's card (none: take it down); a failed write is the next tick's to retry."""
        if self.picker_publish is None:
            return
        try:
            self.picker_publish(picker.widgets(time.monotonic()) if picker is not None else [])
        except OSError as error:
            LOG.warning('Macro: loop kind picker not shown: %s', error)

    def _close_picker(self, why: str) -> None:
        """Under the lock."""
        if self.picker is None:
            return
        self.picker = None
        if self.picker_timer is not None:
            self.picker_timer.cancel()
            self.picker_timer = None
        self._show_picker(None)
        LOG.info('Macro: loop kind picker closed: %s', why)

    def choose_kind(self, requested_at: float, now: float, key: str) -> bool:
        """The `loop-kind` request (request.py; the player, 2026-10-19: "I want you to have the ability to dynamically
        switch loop type"): with the loop off the kind at once, with it on from the next game (`Loop.pending`)."""
        kinds = loop_kinds()
        with self.lock:
            if self.closed or not 0 <= now - requested_at <= 1 or key not in kinds:
                LOG.warning('Macro: loop kind %r refused', key)
                return False
            kind = kinds[key]
            self._close_picker('a kind was requested')
            self._end_zone_wait(kind)
            if not self.loop.on:
                self.loop.kind, self.loop.pending, self.loop.chosen = kind, None, True
                self._say_kind(kind)
            elif kind == self.loop.kind:
                self.loop.pending = None
                self._say_kind(kind)
            else:
                self.loop.pending = kind  # said as `Loop run: ` when it takes (loop.py `leg`)
                self._say(f'Loop run from the next game: {kind.name}')
            LOG.info('Macro: loop kind %s chosen by request (the loop %s)', kind.name, 'on' if self.loop.on else 'off')
            return True

    def _toggle_loop(self) -> None:
        """KP_6: the loop on from where the character is (a run working now is followed by its first leg), or off at
        once (the run cancelled, the character left where it is). Under the lock. The stand guard's watch is over
        either way (the player's pause wins; on, the loop's own watchdogs), its attack mode ending for the first leg."""
        guarded = self.guard.armed and self.guard.fighting and self.attack_mode
        self._guard_disarm('the loop toggled (KP_6, or the resume after a restart)')
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
        if self.loop.pending is not None:
            # A kind asked while on takes at the next start too: the player turned it on in a game of their own,
            # which never had the loop's next game leg (21:42:37 on 2026-10-19, River of Flame)
            self.loop.kind, self.loop.pending, self.loop.chosen = self.loop.pending, None, True
            self._say_kind(self.loop.kind)
        self._reclaim()  # HANDOVER: an on always leads to a leg, or the log says which run it waits for
        if not self.working:
            self._start(LOOP)
            return
        if HANDOVER:
            LOG.info('Macro: loop on: its first leg follows the %s run working now', self.routine)
        if self.routine == BUFF:
            self.cancelled.set()  # buff mode yields to the loop, its first leg follows (`_follow`)
        elif guarded and self.routine == ATTACK:
            self.cancelled.set()  # the guard's fight (its mode turned off above): the first leg follows (`_follow`)

    def _reclaim(self) -> None:
        """HANDOVER: `working` on with the run's thread gone (it died without handing over: `_handed_over` is the rule,
        this the backstop) is taken back, said. A runner whose run never had a thread (a test's own `working`) is left
        as it is. Under the lock."""
        thread = self.thread
        if not HANDOVER or not self.working or thread is None or thread.is_alive():
            return
        LOG.warning('Macro: the %s run ended without handing over (its thread gone): the runner is free', self.routine)
        self.working = False
        self.queue.drop(self.routine, 'its run ended without handing over')

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

    def resume_state(self) -> dict:
        """What a restart of the service carries over (appraisal/service.py `Restart`): the service's own settings. The
        game's state is its record's (macros/midgame.py RECORD, `attach_records`), never a copy here."""
        with self.lock:
            return {
                'loop': self.loop.on,
                'pickup_mode': self.pickup_mode,
                # The kind playing and the one asked from the next game: a restart mid-game (macros/midgame.py) goes
                # on in the kind it was (a lobby restart takes the asked one at its first leg: loop.py `leg`)
                'loop_kind': self.loop.kind.key,
                'loop_pending': self.loop.pending.key if self.loop.pending is not None else None,
                # The player's Gheed's Fortune on a shared page mid-swap (macros/charms.py): fetched back after it
                'gheeds': self.loop.parked.state() if self.loop.parked is not None else None,
            }

    def attach_records(self, records) -> None:
        """The games' records (terror/tracker.py `ZoneTracker.record`; None: none) the loop and the sightings keep the
        game's state in and take it up from (macros/midgame.py RECORD); an old restart blob's game written into them
        (`resume`, midgame.py LEGACY_BLOB). Before `resume`."""
        with self.lock:
            self.loop.records = records
            self.sightings.records = records

    def resume(self, state: dict) -> None:
        """Take up what the service before a restart left (`resume_state`): the pickup mode at once, the loop at the
        first poll that reads the game (`poll`)."""
        with self.lock:
            if state.get('pickup_mode') in MODES:
                self.pickup_mode = state['pickup_mode']
            if state.get('loop_kind') in loop_kinds():
                self.loop.kind = loop_kinds()[state['loop_kind']]
                self.loop.chosen = True  # kept from before the restart
            pending = loop_kinds().get(state.get('loop_pending') or '')
            self.resuming = bool(state.get('loop'))
            if self.resuming:
                self.resume_pending = pending  # after the resume's own turn on (watch.py `poll`): from the next game
            else:
                self.loop.pending = pending  # the player's next KP_6 on takes it (`_toggle_loop`)
            # A service before the game's record (midgame.py LEGACY_BLOB): its game into the record, once
            midgame.migrate(self.loop.records, state)
            parked = Parked.restore(state.get('gheeds'))
            if parked is not None:
                self.loop.parked = parked
                LOG.info("Macro: charms: the player's Gheed's Fortune (unit %d) is on shared page %s: fetched back "
                         'first', parked.unit_id, parked.page)  # fmt: skip
        LOG.info(
            'Macro: resumed after a restart: loop %s, pickup %s, run %s',
            'on' if self.resuming else 'off',
            self.pickup_mode,
            self.loop.kind.name,
        )

    def hold_restart(self, when: str, target: dict) -> None:
        """A restart asked for at the loop's next safe point (`when`: macros/midgame.py TOWN, SAFE; restart.py
        --when): the loop stands there and `restart_due` gives `target`, the state the next service takes up. With the
        loop off, due at once."""
        with self.lock:
            self.restart_target = dict(target)
            self.loop.restart_when, self.loop.unsafe_said = when, None
        LOG.info('Macro: loop: a restart waits for a safe point (%s)', when)

    def cancel_restart(self) -> None:
        """The restart's wait given up (restart.py past its --wait): the loop goes on, nothing held."""
        with self.lock:
            held = self.restart_target is not None
            self.restart_target = self.loop.restart_when = self.loop.unsafe_said = None
        if held:
            LOG.info('Macro: loop: the restart no longer waits for a safe point')

    def restart_due(self) -> dict | None:
        """The state to restart with (`hold_restart`) once due, None while not: the loop stands at a safe point, or
        it is off (the player's pause wins: the next service keeps it off)."""
        with self.lock:
            target = self.restart_target
            if target is None:
                return None
            if self.loop.on and self.loop.safe_point is None:
                return None
            if not self.loop.on:
                target = {**target, 'loop': False}
            self.restart_target = None
            return target

    def close(self) -> None:
        """Shutdown is final: the run is cancelled, nothing follows it, and no request starts another."""
        with self.lock:
            self.closed = True
            self.shut.set()
            self.attack_mode = self.buff_mode = False
            if self.loop_timer is not None:
                self.loop_timer.cancel()
            self._close_picker('the service closed')
            if self.mode_timer is not None:
                self.mode_timer.cancel()
            self.loop.stop()
            self._end_run('the service closed')
            self.queue.clear('the service closed')
            self.cancelled.set()
            thread = self.thread
        if thread is not None:
            thread.join(timeout=3)  # outside the lock: the run's end takes it
        if self.focus is not None:
            self.focus.close()
        if self.frames is not None:
            self.frames.close()

    def _show(self, lines: list[str]) -> None:
        """The card: the warning that stands, if any, above `lines`. A card with only the warning stays
        up when the lines are cleared."""
        warning = self.warning
        if warning is not None and time.monotonic() - warning[1] > WARNING_SECONDS:
            warning = self.warning = None
            self.standing = False
        card = ([f'Macro: {warning[0]}'] if warning is not None else []) + lines
        if not HANDOVER:
            self.display(card)
            return
        # The run's thread and the KP_6 timer's both write the card: one at a time (the layer's one temporary file),
        # and a write that fails is the card's loss, never the caller's (rca/2026-10-23/loop-no-legs.md)
        with self.card_lock:
            try:
                self.display(card)
            except OSError as error:
                LOG.warning('Macro: the card %s not shown: %s', card, error)

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

    def _say_kind(self, kind: Kind) -> None:
        self._say(f'Loop run: {kind.name}')  # tools/logwords.py KIND

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
        """The run's thread: `_guarded_run`, and (HANDOVER) whatever its own stop handling raised, the runner handed
        over all the same (`_handed_over`)."""
        if not HANDOVER:
            self._guarded_run(cancelled, routine, generation, until, press)
            return
        try:
            self._guarded_run(cancelled, routine, generation, until, press)
        except Exception as exc:
            LOG.exception('Macro: the %s run failed at its own end', routine)
            self._handed_over(routine, generation, exc)

    def _handed_over(self, routine: str, generation: int, exc: Exception) -> None:
        """The run of `routine` raised `exc` past its stop handling: unless a successor owns the runner or it was
        handed over before the raise, `working` goes off and what follows starts (`_follow`). A loop's leg stops the
        loop, said: a raise that repeats must not make leg after leg."""
        with self.lock:
            if self.generation != generation or not self.working:
                return
            self.queue.drop(routine, 'the step before it failed')
            if routine == LOOP and self.loop.on:
                self._stop_loop(f'the leg failed at its own end ({exc})')
            if not self._follow(routine):
                LOG.info('Macro: the %s run failed at its own end; nothing follows it', routine)

    def _guarded_run(
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
            elif routine == BUFF:
                self._say('Buff mode paused' if self.buff_mode else 'Buff mode off')
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
            elif routine == PICKUP and stop.cause == 'room':
                with self.lock:
                    self._room_after_press(stop, routine)  # the shared no-room routine follows (`_follow`)
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
                if failed and routine == BUFF:
                    self.buff_mode = False  # a death, or its own stop
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
        if (routine == ATTACK and not self.attack_mode) or (routine == BUFF and not self.buff_mode):
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
        if routine not in (ATTACK, BUFF):
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
        errand = self.errand
        if routine == room.ROOM:
            self.errand = None
            if errand is not None and errand.done and not self.loop.on and following is None:
                self._resume_errand(errand)  # the activity goes on as the player left it
        elif errand is not None and (following is not None or self.loop.on or self.closed):
            # A press or the loop came first: no trip over them (the player's hand wins); the activity as it was
            self.errand = None
            LOG.info('Macro: room: the trip for %s dropped: %s came first', errand.label, following or 'the loop')
            self._resume_errand(errand)
        elif errand is not None:
            following = room.ROOM  # a trip for room (running/room.py), before the mode resumes
        if following is None and self.attack_mode and routine != ATTACK:
            following = ATTACK  # the step is done: the mode resumes
        if following is None and self.buff_mode and not self.loop.on and routine != BUFF:
            following = BUFF  # after a step or attack mode; not under the loop (2026-10-19)
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

    # buffing.py
    _mode_running = buffing._mode_running
    _mode_tap = buffing._mode_tap
    _mode_window = buffing._mode_window
    _judge_mode_taps = buffing._judge_mode_taps
    _toggle_mode = buffing._toggle_mode
    _mode_on = buffing._mode_on
    _mode_off = buffing._mode_off
    _keep_buffs = buffing._keep_buffs
    _buff_cast = buffing._buff_cast
    _swap_back = buffing._swap_back
    _buff_flipped = buffing._buff_flipped

    # execution.py
    _execute = execution._execute
    play_by = execution.play_by
    perform = execution.perform
    pursues = execution.pursues
    staged = execution.staged
    at_the_way_on = execution.at_the_way_on
    _teleport_step = execution._teleport_step
    choosing = execution.choosing
    wear = execution.wear
    ground = execution.ground

    # legs.py
    _loop_level_run = legs._loop_level_run
    _agenda_policy = legs._agenda_policy
    _way_on = legs._way_on
    _loop_hands = legs._loop_hands
    _identify_loot = legs._identify_loot
    _shared_town_visit = legs._shared_town_visit

    # recovery.py
    _loop_stopped = recovery._loop_stopped
    _stop_loop = recovery._stop_loop
    _field_trip = recovery._field_trip
    _gheeds_swap = recovery._gheeds_swap
    _carry_one = recovery._carry_one
    _forget_given_up = recovery._forget_given_up
    _beset_facts = recovery._beset_facts
    _attacker_near = recovery._attacker_near
    _carried_now = recovery._carried_now

    # valuables.py
    _picked = valuables._picked
    _sighted = valuables._sighted
    _valuable_left = valuables._valuable_left
    _fetch = valuables._fetch
    _go_back = valuables._go_back

    # jump.py
    _jump = jump._jump
    _leap = jump._leap
    _jump_look = jump._jump_look
    _jump_life = jump._jump_life
    _jump_drop = jump._jump_drop
    _jump_dead = jump._jump_dead
    _at_the_fight = jump._at_the_fight

    # room.py
    _room_in_cube = room._room_in_cube
    _room_trip_due = room._room_trip_due
    _room_trip_possible = room._room_trip_possible
    _room_after_press = room._room_after_press
    _room_errand = room._room_errand
    _resume_errand = room._resume_errand

    # merclost.py
    _merc_poll = merclost._merc_poll
    _merc_read = merclost._merc_read

    # guarding.py
    _guard_arm = guarding._guard_arm
    _guard_disarm = guarding._guard_disarm
    _guard_poll = guarding._guard_poll
    guard_look_of = guarding.guard_look_of
    guard_watch = guarding.guard_watch

    # watch.py
    poll = watch.poll
    _place = watch._place
    _dead = watch._dead
    _staff_in_hand = watch._staff_in_hand
