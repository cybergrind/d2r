"""The combat recorder in its own process (RECORDER_PROCESS, 2026-10-23, rca/2026-10-23/realtime-3-findings.md).

The recorder (record.py `CombatRecorder`) reads and writes a whole frame 25 times a second on its own thread: every
monster with its path and record, the missiles, the states, and the frame's JSON. Each frame is ~6 ms of Python, so
~15 % of a core holds the service's one GIL against the macro's looks and decisions. Here the same `Recorder` and
`LiveSampler` run in a child process (spawn) with their own memory handle, display connection and GIL. The service
keeps only a feed:

- `Feed` stands where `Recorder` stood for the service. `note` (the macro's lines, requests, `load` windows), `sent`
  (every input, stamped with its thread and routine here, as `Recorder.sent` does) and `decided` (takes/decisions.py)
  are deque appends on the caller's thread.
- The feed's thread (`recorder-feed`) sends:
  - every FEED_SECONDS, what was appended, with `macro_working()`;
  - every SLOW_SECONDS, the macro's state snapshot, the pickup's loot wishes and the input mode;
  - every LEVEL_SECONDS, the guide's level when it says more;
  - at a change, the game to read (`poll` binds it as `CombatRecorder.poll` does).
  It also logs what the child logs ("Combat take ... opened"), and restarts a child that died (RESTARTS in
  RESTART_WINDOW at most).
- The child (`serve`) applies each message (`apply`) and records exactly as the thread did. It stops on 'stop',
  SIGTERM, or when the service is gone (its parent pid changes).

The pickup's loot read (`loot=lambda memory: memory.loot(**wanted())` in appraisal/service.py) runs in the child: its
wishes are taken by calling it once a state tick with a stand-in memory that keeps the arguments (`Wishes`).
"""

import logging
import math
import os
import pickle
import signal
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.input import sent
from inventory_tracking.levels.model import Level
from inventory_tracking.native.memory import one_unit_table
from inventory_tracking.takes import decisions
from inventory_tracking.takes.record import (
    AREAS,
    FRAME_RATE,
    LEVEL_SECONDS,
    SLOW_SECONDS,
    LiveSampler,
    MacroLines,
    Recorder,
)


# 2026-10-23: True: the take is recorded in a child process (`RecorderProcess`). On 2026-10-24 ~12:30.
RECORDER_PROCESS = True
FEED_SECONDS = 0.02  # between the feed's batches (a frame is 0.04 s: each frame gets what came before it)
RESTARTS = 3  # starts of the child within RESTART_WINDOW, at most
RESTART_WINDOW = 300.0
JOIN_SECONDS = 3.0
CLOSE_SECONDS = 30.0  # the child's last take closed and packed (takes/retain.py) before it is killed
KEPT = 20000  # appended items held for the child at most (a child that does not take them loses the oldest)


@dataclass(frozen=True)
class Config:
    """What the child is made with (pickled to it)."""

    output: Path
    areas: frozenset[int] | None = AREAS
    rate: float = FRAME_RATE
    keep: int | None = None
    town: bool = False
    paths: bool = False
    loot: bool = False  # the pickup's loot read is wanted (its wishes come with the state)
    code: dict[str, Any] = field(default_factory=dict)
    switch_interval: float = 0.005  # the service's (the manifest's `switch_interval`)
    # Tests: 'module:function' making the child's sampler from its `Fed` (None: a LiveSampler of the game)
    sampler: str | None = None


@dataclass
class Fed:
    """The service's side as the child last heard it."""

    working: bool = False
    macro_state: dict[str, Any] | None = None
    wishes: dict[str, Any] | None = None  # the pickup's loot read's arguments; None: not heard yet
    level: Level | None = None
    input_mode: str | None = None
    game: tuple[int, int, int] | None = None


class Wishes:
    """A stand-in memory whose `loot` gives back its arguments: the service's loot read's wishes, without a read."""

    def loot(self, **kwargs: Any) -> dict[str, Any]:
        return kwargs


def wishes_of(loot: Callable[[Any], Any] | None) -> dict[str, Any] | None:
    if loot is None:
        return None
    try:
        found = loot(Wishes())
    except Exception as exc:
        LOG.debug('Combat recorder: the loot wishes unread (%s)', exc)
        return None
    return found if isinstance(found, dict) else None


# The child's side


def apply(message: tuple, recorder: Recorder, sampler: Any, fed: Fed, stop: threading.Event) -> None:
    """One message of the feed's, applied to the child's recorder and sampler."""
    kind = message[0]
    if kind == 'batch':
        _, items, working = message
        fed.working = working
        notes = [item[1:] for item in items if item[0] == 'note']
        if notes:
            with recorder.noting:
                recorder.noted.extend(notes)
        for item in items:
            if item[0] == 'sent':
                recorder.inputs.append(item[1:])
    elif kind == 'state':
        _, fed.macro_state, fed.wishes, fed.input_mode = message
    elif kind == 'level':
        fed.level = message[1]
    elif kind == 'attach':
        fed.game = message[1]
        attach = getattr(sampler, 'attach', None)
        if attach is not None:
            attach(*message[1])
    elif kind == 'detach':
        fed.game = None
        detach = getattr(sampler, 'detach', None)
        if detach is not None:
            detach()
    elif kind == 'stop':
        stop.set()


class Said(logging.Handler):
    """The child's log records sent to the service, which logs them (the child has no log of its own)."""

    def __init__(self, send: Callable[[tuple], None]) -> None:
        super().__init__(logging.INFO)
        self.send = send

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.send(('log', record.levelno, record.getMessage()))
        except Exception:  # a line that cannot be sent is lost, never the frame
            return


def made_sampler(config: Config, fed: Fed) -> Any:
    if config.sampler is not None:
        module, _, name = config.sampler.partition(':')
        return getattr(__import__(module, fromlist=[name]), name)(fed)
    loot = (lambda memory: memory.loot(**fed.wishes) if fed.wishes is not None else None) if config.loot else None
    return LiveSampler(lambda: fed.working, paths=config.paths, loot=loot, macro_state=lambda: fed.macro_state)


def serve(conn: Any, config: Config, parent: int | None = None) -> None:
    """The child's body: records until 'stop', SIGTERM, or the service (`parent`) is gone."""
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    sending = threading.Lock()

    def send(message: tuple) -> None:
        with sending:
            conn.send(message)

    LOG.setLevel(logging.INFO)
    LOG.addHandler(Said(send))
    fed = Fed()
    sampler = made_sampler(config, fed)
    recorder = Recorder(
        sampler, output=config.output, areas=config.areas, rate=config.rate, level=lambda: fed.level,
        stats=getattr(sampler, 'stats', lambda stats_at: {}),
        manifest=lambda: {
            'keys': {str(key): name for key, name in getattr(sampler, 'name_keys', dict)().items()},
            'code': config.code,
            'input_mode': fed.input_mode,
            'switch_interval': config.switch_interval,
            'recorder': 'process',
        },
        keep=config.keep, town=config.town, server_frame=getattr(sampler, 'server_frame', None),
    )  # fmt: skip

    def receive() -> None:
        while not stop.is_set():
            if parent is not None and os.getppid() != parent:
                stop.set()
                return
            try:
                if not conn.poll(0.1):
                    continue
                message = conn.recv()
            except EOFError, OSError:
                stop.set()  # the service is gone
                return
            try:
                apply(message, recorder, sampler, fed, stop)
            except Exception:
                LOG.exception('Combat recorder: a message failed')

    receiver = threading.Thread(target=receive, name='recorder-receive', daemon=True)
    receiver.start()
    try:
        with ExitStack() as stack:
            if config.sampler is None:
                from inventory_tracking.input.keyboard import X11Keyboard

                try:
                    sampler.keys = stack.enter_context(X11Keyboard().connect(exclusive=False))
                except Exception as exc:  # no display: the frames are written without the pointer and the keys
                    LOG.info('Combat recorder: no display for the pointer and the keys (%s)', exc)
            recorder.run(stop)
    finally:
        stop.set()
        receiver.join(timeout=1)
        if recorder.tidying is not None:
            recorder.tidying.join(timeout=CLOSE_SECONDS - 5)  # the last take packed: a daemon thread dies with us
        detach = getattr(sampler, 'detach', None)
        if detach is not None:
            detach()
        with suppress(OSError, ValueError):
            send(('stopped',))


# The service's side


class Feed:
    """What the service hands its events to (where `Recorder` stood): appends, taken by the feed's thread."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.items: deque[tuple] = deque(maxlen=KEPT)
        self.routine: Callable[[], str | None] | None = None  # the macro run's routine (the service sets it)

    def note(self, kind: str, **fields: Any) -> None:
        self.items.append(('note', self.clock(), kind, fields))

    def sent(self, kind: str, what: tuple[int, ...]) -> None:
        """As `Recorder.sent`: stamped with the sending thread and the macro's routine, here where they are."""
        by = threading.current_thread().name
        routine = self.routine() if by == 'macro' and self.routine is not None else None
        self.items.append(('sent', self.clock(), kind, what, by, routine))

    def decided(self, decision: dict[str, Any]) -> None:
        self.items.append(('note', self.clock(), 'decision', decision))

    def taken(self) -> list[tuple]:
        """What was appended since the last take (only the feed's thread takes from the left)."""
        return [self.items.popleft() for _ in range(len(self.items))]


class RecorderProcess:
    """`CombatRecorder`'s handle with the recording in a child process: `poll` binds the game, `close` ends it."""

    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        output: Path,
        areas: frozenset[int] | None = AREAS,
        rate: float = FRAME_RATE,
        level: Callable[[], Level | None] | None = None,
        macro_working: Callable[[], bool] = lambda: False,
        poll_interval: float = 1.0,
        paths: bool = False,
        keep: int | None = None,
        town: bool = False,
        loot: Callable[[Any], Any] | None = None,
        macro_state: Callable[[], dict[str, Any]] | None = None,
        code: dict[str, Any] | None = None,
        context: Any = None,
        sampler: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.source, self.capture_lock = source, capture_lock
        self.level, self.macro_working, self.loot, self.macro_state = level, macro_working, loot, macro_state
        self.clock = clock
        self.config = Config(
            output=output, areas=areas, rate=rate, keep=keep, town=town, paths=paths, loot=loot is not None,
            code=code or {}, switch_interval=sys.getswitchinterval(), sampler=sampler,
        )  # fmt: skip
        self.context = context if context is not None else get_context('spawn')
        self.recorder = Feed(clock)
        self.input_mode: Callable[[], str | None] | None = None  # as CombatRecorder's (the service sets it)
        self.listener = MacroLines(self.recorder.note)
        LOG.addHandler(self.listener)
        sent.listen(self.recorder.sent)
        decisions.listen(self.recorder.decided)
        self.game: tuple[int, int, int] | None = None  # what `poll` bound; None: detached
        self.sent_game: tuple[int, int, int] | None = None  # what the child was told
        self.level_said: tuple[int, int] | None = None  # (area, grids) of the level sent last
        self.last_poll = -math.inf
        self.poll_interval = poll_interval
        self.warned = False
        self.starts: deque[float] = deque()
        self.unpicklable: set[str] = set()  # the kinds of events said to be dropped
        self.process: Any = None
        self.conn: Any = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._feed, name='recorder-feed', daemon=True)
        self._start()
        self.thread.start()

    # the child

    def _start(self) -> bool:
        now = self.clock()
        while self.starts and now - self.starts[0] > RESTART_WINDOW:
            self.starts.popleft()
        if len(self.starts) >= RESTARTS:
            return False
        ours, theirs = self.context.Pipe()
        self.process = self.context.Process(
            target=serve, args=(theirs, self.config, os.getpid()), name='d2r-recorder', daemon=True
        )
        self.process.start()
        theirs.close()
        self.conn = ours
        self.starts.append(now)
        self.sent_game = self.level_said = None  # the new child is told again
        LOG.info('Combat recorder: the recording process started (process %d)', self.process.pid)
        return True

    def _alive(self) -> bool:
        return self.process is not None and self.process.is_alive()

    # the feed's thread

    def _feed(self) -> None:
        state_at = level_at = -math.inf
        while not self.stop.wait(FEED_SECONDS):
            try:
                if not self._alive() and not self._start():
                    continue  # given up: the events are kept (KEPT) and lost oldest first
                now = self.clock()
                self._said()
                if self.game != self.sent_game:
                    self.conn.send(('attach', self.game) if self.game is not None else ('detach',))
                    self.sent_game = self.game
                if now - state_at >= SLOW_SECONDS:
                    state_at = now
                    state = self.macro_state() if self.macro_state is not None else None
                    mode = self.input_mode() if self.input_mode is not None else None
                    self.conn.send(('state', state, wishes_of(self.loot), mode))
                if now - level_at >= LEVEL_SECONDS:
                    level_at = now
                    self._level()
                self._batch(self.recorder.taken(), bool(self.macro_working()))
            except (BrokenPipeError, EOFError, OSError) as exc:
                LOG.info('Combat recorder: the recording process is gone (%s)', exc)
                self._kill()
            except Exception:
                LOG.exception('Combat recorder: the feed failed')
        self._said()

    def _batch(self, items: list[tuple], working: bool) -> None:
        """The batch sent; one that cannot be pickled is sent item by item, those that cannot be pickled dropped (said
        once a kind)."""
        try:
            payload = pickle.dumps(('batch', items, working))
        except Exception:
            kept = []
            for item in items:
                try:
                    pickle.dumps(item)
                except Exception as exc:
                    name = str(item[2] if item[0] == 'note' else item[0])
                    if name not in self.unpicklable:
                        self.unpicklable.add(name)
                        LOG.info('Combat recorder: a %s event cannot go to the recording process (%s)', name, exc)
                    continue
                kept.append(item)
            payload = pickle.dumps(('batch', kept, working))
        self.conn.send_bytes(payload)

    def _level(self) -> None:
        level = self.level() if self.level is not None else None
        if level is None:
            return
        said = (level.area, len(level.ground))
        if said != self.level_said:
            self.conn.send(('level', level))
            self.level_said = said

    def _said(self) -> None:
        """The child's log lines logged here."""
        conn = self.conn
        if conn is None:
            return
        try:
            while conn.poll(0):
                message = conn.recv()
                if message[0] == 'log':
                    LOG.log(message[1], '%s', message[2])
        except EOFError, OSError:
            return

    def _kill(self) -> None:
        process, self.process = self.process, None
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=JOIN_SECONDS)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)

    # the service's calls

    def poll(self, now: float) -> None:
        """As `CombatRecorder.poll`: the game bound (the feed tells the child)."""
        if now - self.last_poll < self.poll_interval or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            self.source.ensure_connected()
            table = one_unit_table(self.source.capture)
            if table is None:
                raise ValueError('the game is not attached')
            self.game = (self.source.pid, self.source.images['candidate_base'], table)
            self.warned = False
        except Exception as exc:
            self.game = None
            if not self.warned:
                LOG.info('Combat recorder: waiting for the game (%s)', exc)
                self.warned = True
        finally:
            self.capture_lock.release()

    def close(self) -> None:
        LOG.removeHandler(self.listener)
        if sent.listener == self.recorder.sent:
            sent.listen(None)
        if decisions.listener == self.recorder.decided:
            decisions.listen(None)
        self.stop.set()
        self.thread.join(timeout=JOIN_SECONDS)
        conn, process = self.conn, self.process
        if conn is not None and process is not None and process.is_alive():
            try:
                conn.send(('batch', self.recorder.taken(), False))
                conn.send(('stop',))
            except OSError:
                pass
            process.join(timeout=CLOSE_SECONDS)  # the child closes its take ('stopped') and packs it
            self._said()
        self._kill()


def combat_recorder(source, **kwargs: Any) -> Any:
    """The service's recorder: in a child process with RECORDER_PROCESS on, on a thread (`CombatRecorder`) off."""
    if RECORDER_PROCESS:
        return RecorderProcess(source, **kwargs)
    from inventory_tracking.takes.record import CombatRecorder

    return CombatRecorder(source, **kwargs)
