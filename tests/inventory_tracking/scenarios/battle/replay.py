"""One recorded battle, played back to the macro as it was played to it in the game.

The game side is the record, open loop: at every look the macro gets the take's frame of that moment
(the character, the monsters with their life, the doors), the drops and the belt the log tells of,
and the unit the game showed under the pointer. The macro side is production, closed loop: the
runner (macros/runner.py) with its queue, attack mode with its sweep and rotation (hunt.py,
rotation.py), the pickup step (pickup.py), each on the take's clock, which moves only when the
macro sleeps. The player's key presses come at their recorded times.

So the replay answers one question: shown what it was shown, does the macro do what it did? Where it
does something else, the record no longer follows (the character stands where it stood in the game,
not where the replay would have put it), and everything after that moment is not a reproduction any
more: `Replay.run` returns the macro's own log, stamped with the take's clock, to be held against
the recorded log line by line (evidence.py).

Not in a take, and so taken from the log or assumed (each named where it is set): the drops and when
they fell, the belt, the staff, the skill keys, the unit under the pointer during the pickup.

What a take's 25 frames a second do not say, and how it is made up for (each with its evidence where
it is done): a frame is stamped a little after it was read (FRAME_LATE); the character's mode at a
skill key is the one the macro's own log names (`Script.modes`), and the instants between two casts
that it waited through without pressing were not among its looks (`Script.busy`); a look costs time
(`Script.read_seconds`); and the macro's own key and button presses fall where the take has them
(`hold_to`: the pace's random pauses are not the game's). The clock is held to nothing else: not to
the log's lines.
"""

import bisect
import gzip
import importlib
import json
import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.builds import pursuing
from inventory_tracking.common import LOG
from inventory_tracking.game.records import Loot, Monster, Player, Teleport, World
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Level, Room, Walkable
from inventory_tracking.macros.actuator import Actuator
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter, threat
from inventory_tracking.macros.pickup import LOOKED, pick_up
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.runner import ATTACK, PICKUP, TELEPORT, MacroRunner
from inventory_tracking.macros.timing import Pace
from inventory_tracking.takes.takes import PlayerRow, Take, monsters_of, player_of
from tests.inventory_tracking.macros.fakes import BUILD, Clock, FakeConnection, set_runner


@dataclass
class Said:
    """One line of the macro's log, at the take's clock."""

    at: float
    text: str


@dataclass
class Script:
    """What a take does not hold. `loot(seconds, frame)` gives the drops, belt and room at a moment;
    `hovered(seconds, pointer)` the unit under the pointer; `presses` the player's keys as (seconds,
    routine); `keys` the key or button of each skill; `slots` the skills on keys."""

    presses: list[tuple[float, str]]
    keys: dict[int, str]
    slots: tuple[int | None, ...]
    loot: Callable[[float, dict], Loot]
    hovered: Callable[[float, tuple[int, int]], tuple[int, int] | None] = lambda seconds, pointer: None
    on_input: Callable[[float, tuple], None] = lambda seconds, event: None  # the game's answer to a key or click
    prepare: Callable[[Hunter], None] = lambda hunter: None  # what the hunt remembered when the take began
    # (seconds, mode): the character's mode as the macro itself read it (its log says so at a key).
    modes: list[tuple[float, int]] = field(default_factory=list)
    # (from, to): seconds in which the macro, waiting to press a key, did not see the character free
    # (it pressed at `to`): a free instant a frame shows in between was not one of its looks.
    busy: list[tuple[float, float]] = field(default_factory=list)
    # (from, to, x, y): seconds between which the character is read at (x, y) instead of the frame's place.
    places: list[tuple[float, float, float, float]] = field(default_factory=list)
    staff: Teleport | None = None
    hands: tuple[str, ...] = ()
    hold_inputs: bool = True
    read_seconds: float = 0.008  # what one look at the game costs on the clock
    start: float = 0.0  # seconds into the take at which the first press comes
    seed: int = 1
    patches: dict[str, object] = field(default_factory=dict)  # 'module.NAME' -> value, for rules as they were


MODE_BEFORE, MODE_AFTER = 0.045, 0.15  # seconds around a logged read of the character's mode (a look every 0.03 s)
LOOK_BACK, LOOK_AHEAD = 0.25, 3
FRAME_LATE = 0.02
GAP_FRAMES = 2
CASTING = 10  # the character's mode while it casts
LOOK_EARLY = 0.15  # seconds the replay may be ahead of the record's look and still be shown what that look saw
# X key codes of the keys a take's `keys` events name (a US layout, as the host's).
X_KEYCODES = {
    'a': 38,
    's': 39,
    'd': 40,
    'g': 42,
    'q': 24,
    'r': 27,
    't': 28,
    'c': 54,
    '1': 10,
    '2': 11,
    '3': 12,
    '4': 13,
    '6': 15,
}
SYNC_WINDOW = 0.35  # seconds a press of the replay may be from the take's and still be that press
# The takes (2026-10-11 and 12) predate the pursuit loop (2026-10-13): replayed with it off, as recorded (the default
# is on since 2026-10-19, batch E).
RECORDED = pursuing(BUILD, False)


class Capture(logging.Handler):
    """The macro's log on the take's clock."""

    def __init__(self, clock: Clock) -> None:
        super().__init__(logging.INFO)
        self.clock, self.said = clock, []

    def emit(self, record: logging.LogRecord) -> None:
        self.said.append(Said(self.clock.now, record.getMessage()))


def character(frame: dict) -> PlayerRow:
    """The character's row of a frame that has one (a replay keeps only those)."""
    row = player_of(frame)
    assert row is not None
    return row


class Replay:
    def __init__(self, fixture: Path, script: Script) -> None:
        self.take = Take.load(fixture)
        with gzip.open(fixture / 'level.json.gz', 'rt', encoding='utf-8') as handle:
            level = json.load(handle)
        self.frames = [frame for frame in self.take.frames if frame.get('p')]
        self.times = [frame['t'] - self.frames[0]['t'] for frame in self.frames]
        area = character(self.frames[0]).area
        rooms = tuple(Room(r['preset'], r['x'], r['y'], r['width'], r['height']) for r in level['rooms'])
        self.level = Level(area, rooms, tuple(Walkable(**grid) for grid in level.get('ground', ())))
        self.script = script
        self.clock = Clock()
        self.keys = FakeConnection()
        self.inputs: list[tuple[float, tuple]] = []  # (seconds, the fake connection's event)
        self.keys.on_event = self.input
        # The record's own key and button presses, as (seconds, 'key' or 'button', code), in order:
        # the clock is held to them as to the log's lines (`Capture`), when the macro presses the same.
        start = self.frames[0]['t']
        self.pressed = [
            (event['t'] - start, 'key', code)
            for event in self.take.events
            if event.get('event') == 'keys'
            for code in event.get('down', ())
        ] + [
            (event['t'] - start, 'button', event['button'])
            for event in self.take.events
            if event.get('event') == 'button' and event.get('down')
        ]
        self.pressed.sort()
        press, clicked = self.keys.press, self.keys.button

        def pressing(key: int) -> bool:
            name = next((name for name, value in self.keys.names.items() if value == key), None)
            self.hold_to('key', X_KEYCODES.get(name or ''))
            return press(key)

        def clicking(button: int, down: bool) -> bool:
            if down:
                self.hold_to('button', button)
            return clicked(button, down)

        self.keys.press, self.keys.button = pressing, clicking
        self.pending = sorted(script.presses)
        self.runner: MacroRunner | None = None
        self.hunter = Hunter(lambda: self.level, None, None, build=RECORDED)
        script.prepare(self.hunter)
        self.failed: list[BaseException] = []

    def hold_to(self, kind: str, code: int | None) -> None:
        """The clock set to the record's press of the same key or button, if one lies within SYNC_WINDOW."""
        if not self.script.hold_inputs:
            return
        now = self.clock.now
        for index, (at, what, which) in enumerate(self.pressed):
            if at > now + SYNC_WINDOW:
                break
            if what == kind and which == code and abs(at - now) <= SYNC_WINDOW:
                del self.pressed[: index + 1]
                self.clock.now = at
                return

    def input(self, event: tuple) -> None:
        self.inputs.append((self.clock.now, event))
        self.script.on_input(self.clock.now, event)

    # -- the game, from the record -----------------------------------------------------------------

    def frame(self) -> dict:
        """The take's frame nearest the clock: a look sees the game as it is, and the frame after is as
        near to that as the frame before (2.93 s into Tower Cellar 5 the macro read the character
        standing where the frame of 2.94 s has it, not running as in that of 2.90 s)."""
        now = self.clock.now
        # A frame is stamped after it was read: what the macro saw at a moment is in the frame stamped
        # FRAME_LATE later. Three things in Tower Cellar 5 agree on it: the character stands at 2.93 s
        # where the frame of 2.94 s has it; the last monster is out of reach for the look before
        # 12.76 s and in the frames only from 12.79 s; Blade Warp's key, pressed at 1.559 s, is down
        # first in the frame of 1.573 s.
        now += FRAME_LATE
        after = bisect.bisect_right(self.times, now)
        if after == 0 or after == len(self.times):
            return self.frames[max(0, after - 1)]
        nearer_after = self.times[after] - now < now - self.times[after - 1]
        return self.frames[after if nearer_after else after - 1]

    def world(self) -> World:
        # A look takes time in the game and none here: every monster is read (a teleport step's six
        # looks took 54 to 96 ms, latency trace of 2026-10-11). Without it a wait that looks every
        # 30 ms runs out sooner than it did: the walk of 2.93 s was given up 12 ms before the key
        # that, in the game, came first.
        self.clock.now += self.script.read_seconds
        frame = self.frame()
        row = character(frame)
        rows = monsters_of(frame)
        mode, read_at = self.read_mode(row.mode)
        left, right = row.left_skill, row.right_skill
        if read_at is not None:
            # What the macro read before its key: the skills on the buttons are those of the frame
            # before that look, not of one that already shows the key's own cast.
            before = character(self.frames[max(0, bisect.bisect_right(self.times, read_at) - 1)])
            left, right = before.left_skill, before.right_skill
        x, y = next(((x, y) for since, to, x, y in self.script.places if since <= self.clock.now <= to), (row.x, row.y))
        # Buffs are not in a take: both taken as on (no Hex: Purge or Consume was cast in the fight).
        player = Player(
            row.unit, 'CybergrindAA', mode, row.area, x, y, True,
            left_skill=left, right_skill=right, hex_purge=True,
        )  # fmt: skip
        monsters = tuple(
            Monster(m.unit, m.txt, m.mode, m.x, m.y, m.owner, m.flags, bool(m.ally), m.life, m.max_life)
            for m in rows
            if m.alive
        )
        doors = tuple(Door(d[0], d[1], d[2], float(d[3]), float(d[4])) for d in frame.get('d', ()))
        dead = frozenset(m.unit for m in rows if not m.alive)
        return World(
            True, tuple(frame.get('panels', ())), 'recorded', self.script.slots,
            player=player, monsters=monsters, doors=doors, dead=dead,
        )  # fmt: skip

    def read_mode(self, framed: int) -> tuple[int, float | None]:
        """The character's mode now. A take has 25 frames a second and the macro looks more often: under
        a held strike the character is free for an instant between two casts, which a frame can miss
        (the cast of 6.7 s is one of 2.3 s in the take, and the log has "Sigil: Lethargy on Button9,
        player mode 1" 1.1 s into it). Where the log says what the macro read, that is what it reads
        here, from MODE_BEFORE before the line's time to MODE_AFTER after it."""
        now = self.clock.now
        for at, mode in self.script.modes:
            if at - MODE_BEFORE <= now <= at + MODE_AFTER:
                return mode, at
        if framed not in ACTING and any(since <= now < to for since, to in self.script.busy) and self.brief_gap():
            return CASTING, None
        return framed, None

    def brief_gap(self) -> bool:
        """Whether the frame shown now is a free instant between two casts: GAP_FRAMES frames at most
        with a cast before and after. Under a held strike the character is free for less than a frame
        between two casts; a look every 0.03 s catches one in three or four (the Engorge of 10.2 s
        went down at the fourth such instant after its wait began, 1.4 s on)."""
        index = self.frames.index(self.frame())
        first = last = index
        while first > 0 and self.frames[first - 1]['p'][1] not in ACTING:
            first -= 1
        while last < len(self.frames) - 1 and self.frames[last + 1]['p'][1] not in ACTING:
            last += 1
        return first > 0 and last < len(self.frames) - 1 and last - first + 1 <= GAP_FRAMES

    def corpses(self) -> tuple[tuple[int, float, float], ...]:
        return tuple((m.unit, m.x, m.y) for m in monsters_of(self.frame()) if m.mode == 12)

    def sleep(self, seconds: float) -> None:
        """The take's clock moves; the player's presses that fall due come on the way, as from the
        service's hotkey thread."""
        until = self.clock.now + seconds
        while self.pending and self.pending[0][0] <= until:
            at, routine = self.pending.pop(0)
            self.clock.now = max(self.clock.now, at)
            if routine == 'end':
                self.end()
            else:
                self.press(routine)
        self.clock.now = max(self.clock.now, until)

    def end(self) -> None:
        """The replay is over: the run working now stops and nothing follows it."""
        assert self.runner is not None
        with self.runner.lock:
            self.runner.attack_mode = False
            self.runner.queue.clear('the replay ended')
            self.runner.cancelled.set()
        self.pending.clear()

    def press(self, routine: str) -> None:
        assert self.runner is not None
        now = time.monotonic()
        self.runner.request(now, now, routine)

    # -- the macro, production -----------------------------------------------------------------------

    def key_names(self, world: World, skills=()) -> dict[int, str]:
        return dict(self.script.keys)

    def run_for(self, cancelled: threading.Event) -> Run:
        pace = Pace(random.Random(self.script.seed), self.sleep)
        actuator = Actuator(self.keys, lambda: True, pace)
        actuator.cancelled = cancelled
        run = Run(
            self.world,
            actuator,
            pace,
            clock=self.clock,
            cancelled=cancelled,
            say=lambda text: LOG.info('Macro: %s', text),
            hands=lambda: self.script.hands,
            teleport=lambda: self.script.staff,
            loot=lambda: self.script.loot(self.clock.now, self.frame()),
            build=RECORDED,  # the take's character is the fakes': the Echoing Strike Warlock with its weapon sets
        )
        run.hovered = lambda: self.script.hovered(self.clock.now, self.keys.pointer())
        run.hover_note = lambda: 'replayed'
        run.corpses = self.corpses
        run.keys = dict(self.script.keys)
        return run

    def execute(self, cancelled: threading.Event, routine: str) -> None:
        """As MacroRunner._execute, without the process, the window and the memory."""
        assert self.runner is not None
        run = self.run_for(cancelled)
        if routine == ATTACK:
            run.actuator.drift, run.actuator.steady = 10**6, False
            self.hunter.pick = self.runner._pick
            self.hunter.attack_mode(run, self.key_names)
        elif routine == PICKUP:
            if not pick_up(run, self.level, self.key_names, lambda: self.hunter.step(run, self.key_names), threat(run)):
                self.runner.attack_mode = True
        elif routine == TELEPORT:
            LOG.info('Macro: (replay) the teleport step would run here')
        else:
            raise AssertionError(f'the replay has no routine {routine}')

    def guarded(self, cancelled: threading.Event, routine: str) -> None:
        try:
            self.execute(cancelled, routine)
        except AssertionError as failure:
            self.failed.append(failure)
            raise

    def run(self, until: float) -> list[Said]:
        """Play the battle to `until` seconds into the take; the macro's log lines on the take's clock."""
        capture = Capture(self.clock)
        self.capture = capture
        level = LOG.level
        LOG.addHandler(capture)
        LOG.setLevel(logging.INFO)
        restore = set_runner(CARD_SECONDS=0, TRAVEL_QUIET=0)  # the runner and its parts (macros/running/)
        LOOKED.clear()  # the pickup's aims of a play before (pickup.py): each replay as the first
        patched = []
        for path, value in self.script.patches.items():
            module, name = path.rsplit('.', 1)
            try:
                owner = importlib.import_module(module)
            except ModuleNotFoundError:  # a class's attribute: 'package.module.Class.name'
                outer, inner = module.rsplit('.', 1)
                owner = getattr(importlib.import_module(outer), inner)
            patched.append((owner, name, getattr(owner, name)))
            setattr(owner, name, value)
        try:
            self.runner = MacroRunner(
                None,
                capture_lock=threading.Lock(),
                saved_games=Path(),
                display=lambda lines: None,
                execute=self.guarded,
            )
            self.runner.hunter = self.hunter
            self.clock.now = self.script.start
            deadline = time.monotonic() + 120
            self.pending = sorted([*self.pending, (until, 'end')])
            while time.monotonic() < deadline:
                thread = self.runner.thread
                if thread is not None and thread.is_alive():
                    thread.join(0.01)
                    continue
                if self.runner.working:
                    continue  # the handover between two runs
                if not self.pending:
                    break
                at, routine = self.pending.pop(0)  # nothing runs: the clock is the next press's
                self.clock.now = max(self.clock.now, at)
                if routine == 'end':
                    break
                self.press(routine)
            self.runner.close()
        finally:
            restore()
            for owner, name, value in patched:
                setattr(owner, name, value)
            LOG.removeHandler(capture)
            LOG.setLevel(level)
        if self.failed:
            raise self.failed[0]
        return capture.said
