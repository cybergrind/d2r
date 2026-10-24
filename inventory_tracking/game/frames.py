"""The game read once a game tick by a process of its own, for every reader in the service (2026-10-23).

The player, ~19:05: "we're still lagging a lot and thus all our actions are lagging behind the actual scene / you need
to find real-time mechanism to read memory" (rca/2026-10-23/realtime-reads-findings.md). The service is one Python
process near one core (its `load` events: CPU p50 81 %, p90 102 %): every read the macro makes waits for the GIL behind
the main loop, the recorder and the macro's own pricing, and a look's age is whatever the macro thread could spare.

The frame reader is a process: its own interpreter, so its own GIL. It looks at the game's tick (the clock object's
last whole tick, `GameMemory.tick_ms`) every POLL_SECONDS and, as soon as the game has made a new tick, reads the
world (`GameMemory.raw_world`, the look's batched read: one process_vm_readv) and publishes it pickled into shared
memory (native/frames.py `Board`); and again QUIET_SECONDS after a read within a tick (the client's panels and buttons
change between ticks), as out of a game or with the tick unread.

`FrameFeed` is the service's side: `attach` starts the reader for the game the run reads (a new one for another
process), `world` gives the newest frame's world, unpickled once per frame, in microseconds and with no syscall; None
when there is none fresh (FRESH_SECONDS), so the caller reads the game itself as before. The doors passed are marked by
the caller (`GameMemory.passed_doors`): that memory is the service's.

Switch: FRAMES (off). The reader is started only with it on, by the macro runner (running/execution.py `_execute`).
"""

import math
import os
import pickle
import signal
import statistics
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from multiprocessing import get_context
from typing import Any, Protocol

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.native.frames import FAILED, RUNNING, STOPPED, Board, Frame


# 2026-10-23: run.world() takes the frame reader's newest frame (a process reading the game each tick); off: the run
# reads the game itself on its own thread, as before. On only with a restart (the reader starts with the first run)
FRAMES = True  # on 2026-10-23 ~20:00 (the player: "you need to find real-time mechanism to read memory")
POLL_SECONDS = 0.001  # the reader's look at the game's tick (two 8-byte reads)
# A frame at least this often whatever the tick (none read: a menu, loading): what the client changes between ticks
# (its panels, the skill on a button) is in a frame within this
QUIET_SECONDS = 0.02
FRESH_SECONDS = 0.12  # a frame read longer ago than this (three ticks) is not taken: the run reads the game itself
ALIVE_SECONDS = 1.0  # the reader's heartbeat older than this: it is taken for gone
START_SECONDS = 15.0  # a reader not beating this long after its start is given up
RESTARTS = 3  # starts of a reader for one game within RESTART_WINDOW, at most
RESTART_WINDOW = 300.0
SAID_EVERY = 60.0  # the feed's `frames` line (`FrameFeed.report`), seconds
KEPT = 2048  # takes kept for the line
GONE_EVERY = 1.0  # seconds between the reader's checks that the game's process is still there after a failed read


class Source(Protocol):
    """What the reader reads: the game's memory (`GameMemory`) or a test's fake."""

    def raw_world(self, light: bool = False) -> World: ...

    def tick_ms(self) -> tuple[int, int] | None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class Game:
    """The game a reader reads: the process and the image base and unit table the service attached to."""

    pid: int
    base: int
    table: int


def open_game(game: Game) -> Source:
    """The game's memory as the macro reads it (game/memory.py), opened in the reader's process."""
    from inventory_tracking.game.memory import GameMemory

    return GameMemory(game.pid, game.base, game.table)


# The reader's side (its own process)


class Reader:
    """The loop of the reader's process: a frame per game tick onto `board` from `source`."""

    def __init__(
        self,
        board: Board,
        source: Source,
        *,
        gone: Callable[[], bool] = lambda: False,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll: float = POLL_SECONDS,
        quiet: float = QUIET_SECONDS,
    ) -> None:
        self.board, self.source, self.gone = board, source, gone
        self.clock, self.sleep, self.poll, self.quiet = clock, sleep, poll, quiet
        self.pid = os.getpid()
        self.tick: int | None = None  # the tick of the last frame
        self.read_at = -math.inf  # when the last frame's read ended
        self.failed_at = -math.inf  # the last failed read's time (the `gone` check's pace)
        self.torn = 0  # reads a tick went by during, read again

    def step(self) -> bool:
        """One look at the game's tick, and a frame when it is new or QUIET has gone by since the last one. Whether a
        frame was published."""
        now = self.clock()
        self.board.beat(self.pid, RUNNING, now)
        ticks = self.source.tick_ms()
        tick = ticks[0] if ticks is not None else None
        if (tick is None or tick == self.tick) and now - self.read_at < self.quiet:
            return False
        seen = began = self.clock()
        try:
            world = self.source.raw_world(False)
            after = self.source.tick_ms()
            if tick is not None and after is not None and after[0] != tick:
                # A tick went by during the read: the world may hold two ticks' units; read again, of the new one
                self.torn += 1
                tick, seen = after[0], self.clock()
                began = seen
                world = self.source.raw_world(False)
        except (OSError, ValueError) as exc:
            if now - self.failed_at >= GONE_EVERY:
                self.failed_at = now
                self.board.fail(f'read failed: {exc}')
                if self.gone():
                    raise
            self.tick, self.read_at = tick, now  # tried again at the next tick (or after QUIET with none read)
            return False
        ended = self.clock()
        payload = pickle.dumps(world, protocol=pickle.HIGHEST_PROTOCOL)
        self.board.publish(payload, tick=tick or 0, seen_at=seen, read_began=began, read_ended=ended)
        self.tick, self.read_at = tick, ended
        return True

    def run(self, stopped: Callable[[], bool]) -> None:
        while not stopped():
            if not self.step():
                self.sleep(self.poll)


def serve(
    name: str,
    game: Game,
    opener: Callable[[Game], Source] = open_game,
    parent: int | None = None,
    poll: float = POLL_SECONDS,
    quiet: float = QUIET_SECONDS,
) -> None:
    """The reader process's body: frames of `game` onto the board `name` until the service (`parent`) or the game is
    gone, or SIGTERM. Its failure is written on the board (`Board.fail`) for the feed to say. No PR_SET_PDEATHSIG: it
    fires when the thread that started the process ends (a run's), not the service; the parent's pid is watched."""
    board = Board.attach(name)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    source = None
    try:
        source = opener(game)
        reader = Reader(
            board, source, gone=lambda: game.pid > 0 and not os.path.exists(f'/proc/{game.pid}'), poll=poll, quiet=quiet
        )

        def stopped() -> bool:
            return stop.is_set() or (parent is not None and os.getppid() != parent)

        reader.run(stopped)
        board.beat(os.getpid(), STOPPED, time.monotonic())
    except BaseException as exc:
        board.fail(f'{type(exc).__name__}: {exc}')
        board.beat(os.getpid(), FAILED, time.monotonic())
        raise
    finally:
        if source is not None:
            source.close()
        board.close()


# The service's side


@dataclass
class Taken:
    """The feed's takes since the last report: the newest frame's age at the take (now less when the reader saw its
    tick), the take's own time, and the takes it had none fresh for."""

    ages: deque[float]
    costs: deque[float]
    frames: int = 0  # frames unpickled
    missed: int = 0  # takes with none fresh: the run read the game itself
    first: int | None = None  # the first and last frame numbers seen (frames published in between)
    last: int | None = None


def taken() -> Taken:
    return Taken(deque(maxlen=KEPT), deque(maxlen=KEPT))


class FrameFeed:
    """The newest frame of the reader's process (`attach` starts it), for any thread of the service."""

    def __init__(
        self,
        *,
        opener: Callable[[Game], Source] = open_game,
        clock: Callable[[], float] = time.monotonic,
        context: Any = None,
        poll: float = POLL_SECONDS,
        quiet: float = QUIET_SECONDS,
    ) -> None:
        self.opener, self.clock, self.poll, self.quiet = opener, clock, poll, quiet
        # A clean interpreter (fork would copy the service's threads' state). Spawn imports the parent's main module
        # again unless it is a package's __main__: the service runs as `python -m inventory_tracking.appraisal`
        self.context = context if context is not None else get_context('spawn')
        self.lock = threading.Lock()
        self.game: Game | None = None
        self.board: Board | None = None
        self.process: Any = None
        self.started_at = -math.inf
        self.starts: deque[float] = deque()
        # (frame number, its world, its light world once made, when the reader saw its tick)
        self.cached: tuple[int, World, World | None, float] | None = None
        self.tally = taken()
        self.said_at: float | None = None
        self.said: Callable[[str], None] | None = None  # the once-a-minute line (`report`)
        self.failure: str | None = None  # the last failure said (said once)

    def attach(self, pid: int, base: int, table: int) -> None:
        """The reader for this game running: started when none is, or when it reads another game or has gone
        (at most RESTARTS starts in RESTART_WINDOW). Returns at once: the first frames come once it has started."""
        game = Game(pid, base, table)
        with self.lock:
            if self.game == game and self._running():
                return
            now = self.clock()
            while self.starts and now - self.starts[0] > RESTART_WINDOW:
                self.starts.popleft()
            if self.game == game and len(self.starts) >= RESTARTS:
                return  # given up for this game: the runs read the game themselves
            if self.game != game:
                self.starts.clear()
            self._stop()
            self.game = game
            self.board = Board.create()
            self.process = self.context.Process(
                target=serve,
                args=(self.board.name, game, self.opener, os.getpid(), self.poll, self.quiet),
                name='d2r-frames',
                daemon=True,
            )
            self.process.start()
            self.started_at = now
            self.starts.append(now)
            self.cached = None
            LOG.info('Frames: the reader started for game %d (process %d)', pid, self.process.pid)

    def _running(self) -> bool:
        process, board = self.process, self.board
        if process is None or board is None or not process.is_alive():
            return False
        health = board.health()
        if health.state == FAILED:
            return False
        if health.alive_at <= 0:  # not beating yet
            return self.clock() - self.started_at < START_SECONDS
        return self.clock() - health.alive_at < ALIVE_SECONDS

    def frame(self) -> Frame | None:
        """The newest frame published, whatever its age; None with no reader or before its first."""
        board = self.board
        return board.newest() if board is not None else None

    def world(self, *, light: bool = False) -> World | None:
        """The newest frame's world (`light`: without the monsters, the doors and the dead, as a light look), when its
        tick was seen under FRESH_SECONDS ago; None otherwise (no reader, not started yet, stalled, gone)."""
        began = self.clock()
        with self.lock:
            board = self.board
            if board is None:
                return None
            found = self._fresh(board, began)
            if found is None:
                self.tally.missed += 1
                self._report(began)
                return None
            seq, world, light_world, seen_at = found
            if light:
                if light_world is None:
                    light_world = replace(world, monsters=(), doors=(), dead=frozenset())
                    self.cached = (seq, world, light_world, seen_at)
                world = light_world
            now = self.clock()
            self.tally.ages.append(now - seen_at)
            self.tally.costs.append(now - began)
            self._report(now)
            return world

    def _fresh(self, board: Board, now: float) -> tuple[int, World, World | None, float] | None:
        """(frame number, world, light world if made, when its tick was seen) of the newest frame, unpickled once a
        frame: a take of the frame already unpickled reads one word of the board."""
        cached = self.cached
        latest = board.latest()
        if latest == 0:
            return None
        if cached is None or cached[0] != latest:
            frame = board.newest()
            if frame is None:
                return None
            if cached is None or cached[0] != frame.seq:
                cached = self.cached = (frame.seq, pickle.loads(frame.payload), None, frame.seen_at)
                self.tally.frames += 1
                if self.tally.first is None:
                    self.tally.first = frame.seq
                self.tally.last = frame.seq
        if now - cached[3] > FRESH_SECONDS:
            self._failed(board)
            return None
        return cached

    def _failed(self, board: Board) -> None:
        """Say once what the reader wrote of its failure, if it did."""
        error = board.health().error
        if error and error != self.failure:
            self.failure = error
            LOG.info('Frames: the reader says: %s', error)

    def _report(self, now: float) -> None:
        if self.said is None:
            return
        if self.said_at is None:
            self.said_at = now
            return
        if now - self.said_at < SAID_EVERY:
            return
        seconds, self.said_at = now - self.said_at, now
        tally, self.tally = self.tally, taken()
        self.said(report(tally, seconds))

    def close(self) -> None:
        with self.lock:
            self._stop()
            self.game = None

    def _stop(self) -> None:
        process, board = self.process, self.board
        self.process = self.board = None
        self.cached = None
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
        if board is not None:
            board.close()


def report(tally: Taken, seconds: float) -> str:
    """The `frames` line's text: takes, frames published and unpickled a second, age at take and take time p50/p90/max
    (ms), and the takes with none fresh."""

    def spread(values: deque[float]) -> str:
        if not values:
            return '-'
        ordered = sorted(values)
        p90 = ordered[int(0.9 * (len(ordered) - 1))]
        return f'{1000 * statistics.median(ordered):.1f}/{1000 * p90:.1f}/{1000 * ordered[-1]:.1f}'

    published = (tally.last - tally.first + 1) if tally.first is not None and tally.last is not None else 0
    takes = len(tally.costs)
    return (
        f'{takes} takes, {published / max(seconds, 1e-9):.1f} frames/s published, '
        f'{tally.frames / max(seconds, 1e-9):.1f}/s unpickled; age at take {spread(tally.ages)} ms; '
        f'take {spread(tally.costs)} ms; {tally.missed} with none fresh (the game read directly)'
    )


def frame_feed(said: Callable[[str], None] | None = None) -> FrameFeed | None:
    """The service's feed with FRAMES on (no reader runs until a run attaches it), else None; `said` takes its
    once-a-minute line."""
    if not FRAMES:
        return None
    found = FrameFeed()
    found.said = said
    return found


class Looks(Protocol):
    def world(self, light: bool = False) -> World: ...

    def passed_doors(self, world: World) -> World: ...


def look_at(memory: Looks, frames: FrameFeed | None, *, light: bool) -> World:
    """A run's look: the newest frame's world with the doors passed marked by `memory` (the service's door memory),
    or, with no fresh frame (or no feed), the game read now by `memory`."""
    seen = frames.world(light=light) if frames is not None else None
    return memory.world(light=light) if seen is None else memory.passed_doors(seen)
