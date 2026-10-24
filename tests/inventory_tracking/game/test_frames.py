"""The game read once a tick by a process of its own (game/frames.py, 2026-10-23): the frame the reader publishes is
the look the run would have made, field for field, and the feed gives it only while it is fresh."""

import dataclasses
import multiprocessing
import os
import pickle
import time

import pytest

from inventory_tracking.game import frames, memory as game_memory
from inventory_tracking.game.frames import FrameFeed, Game, Reader, look_at
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Player, World
from inventory_tracking.native.frames import FAILED, Board
from inventory_tracking.native.memory import ProcessMemory
from tests.inventory_tracking.game import scene
from tests.inventory_tracking.game.test_memory import make_game, replayed


def every_field(value):
    """`value` with every dataclass field, compare=False ones too (`==` leaves those out): what pickling must keep."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__name__,
            *((f.name, every_field(getattr(value, f.name))) for f in dataclasses.fields(value)),
        )
    if isinstance(value, (tuple, list)):
        return tuple(every_field(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(every_field(item) for item in value)
    return value


class Source:
    """A game for the reader: its tick (None: unread) and a world numbered by its read."""

    def __init__(self) -> None:
        self.tick: int | None = 40
        self.reads = 0
        self.fails: Exception | None = None
        self.ticks_during: int | None = None  # the tick the game makes during the next read

    def tick_ms(self):
        return None if self.tick is None else (self.tick, self.tick + 5)

    def raw_world(self, light: bool = False) -> World:
        self.reads += 1
        if self.fails is not None:
            raise self.fails
        if self.ticks_during is not None:
            self.tick, self.ticks_during = self.ticks_during, None
        player = Player(1, 'CybergrindAA', 1, 108, float(self.reads), 5000.0, None)
        return World(True, (), 'cyber9', (), player=player)

    def close(self) -> None:
        pass


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def board():
    made = Board.create(slots=3, slot_bytes=1 << 16)
    yield made
    made.close()


def published(board: Board) -> World:
    frame = board.newest()
    assert frame is not None
    return pickle.loads(frame.payload)


def test_a_frame_is_published_once_a_tick_and_quiet_after_its_read(board):
    source, clock = Source(), Clock()
    reader = Reader(board, source, clock=clock)

    assert reader.step()
    assert not reader.step()  # the same tick: nothing read
    source.tick = 80
    assert reader.step()
    clock.now += frames.QUIET_SECONDS + 0.001
    assert reader.step()  # the same tick QUIET later: read again (the client's panels change between ticks)

    assert source.reads == 3
    assert board.latest() == 3
    player = published(board).player
    assert player is not None
    assert player.x == 3.0
    assert board.newest().tick == 80


def test_with_the_tick_unread_a_frame_is_read_every_quiet_period(board):
    source, clock = Source(), Clock()
    source.tick = None
    reader = Reader(board, source, clock=clock, quiet=0.04)

    assert reader.step()
    clock.now += 0.02
    assert not reader.step()
    clock.now += 0.03
    assert reader.step()
    assert board.newest().tick == 0


def test_a_read_a_tick_went_by_during_is_read_again_as_the_new_tick(board):
    source, clock = Source(), Clock()
    source.ticks_during = 80
    reader = Reader(board, source, clock=clock)

    assert reader.step()

    assert (source.reads, reader.torn) == (2, 1)
    assert board.newest().tick == 80
    assert not reader.step()  # tick 80 is published


def test_a_failed_read_is_said_on_the_board_and_tried_at_the_next_tick(board):
    source, clock = Source(), Clock()
    source.fails = ValueError('short read')
    reader = Reader(board, source, clock=clock)

    assert not reader.step()
    assert not reader.step()  # the same tick: not tried again

    assert source.reads == 1
    assert board.health().error == 'read failed: short read'
    source.fails, source.tick = None, 80
    assert reader.step()


def test_a_failed_read_with_the_game_gone_ends_the_reader(board):
    source = Source()
    source.fails = OSError('No such process')
    reader = Reader(board, source, clock=Clock(), gone=lambda: True)

    with pytest.raises(OSError, match='No such process'):
        reader.step()


@pytest.fixture
def unbound(monkeypatch):
    monkeypatch.setattr(game_memory, 'ProcessMemory', lambda pid: ProcessMemory())


def test_the_frame_of_the_fake_game_is_the_look_field_for_field(board, unbound):
    play = make_game()
    memory, _ = replayed(play)
    reader = Reader(board, memory, clock=Clock())  # its tick unread: a frame at once
    direct, _ = replayed(play)
    direct.world()  # its batch's pattern, as the run's would have

    assert reader.step()
    assert reader.step() is False  # within QUIET
    taken = published(board)

    assert taken.player is not None
    assert every_field(taken) == every_field(direct.raw_world())
    assert taken == direct.world()  # no door to mark here


class Doors:
    """`look_at`'s memory: its own look, and the doors passed marking a world."""

    def __init__(self, world: World) -> None:
        self.own, self.looks, self.marked = world, [], []

    def world(self, light: bool = False) -> World:
        self.looks.append(light)
        return self.own

    def passed_doors(self, world: World) -> World:
        self.marked.append(world)
        return dataclasses.replace(world, game_name='marked')


class Feed:
    def __init__(self, world: World | None) -> None:
        self.given, self.asked = world, []

    def world(self, *, light: bool = False) -> World | None:
        self.asked.append(light)
        return self.given


def test_a_look_takes_the_fresh_frame_with_the_doors_marked_by_the_run():
    frame, own = World(True, (), 'frame', ()), World(True, (), 'own', ())
    memory, feed = Doors(own), Feed(frame)

    world = look_at(memory, feed, light=True)  # pyrefly: ignore[bad-argument-type]  # a fake feed

    assert world.game_name == 'marked'
    assert (feed.asked, memory.looks, memory.marked) == ([True], [], [frame])


def test_with_no_fresh_frame_or_no_feed_the_look_reads_the_game():
    own = World(True, (), 'own', ())
    memory = Doors(own)

    assert look_at(memory, Feed(None), light=False) is own  # pyrefly: ignore[bad-argument-type]  # a fake feed
    assert look_at(memory, None, light=True) is own
    assert memory.looks == [False, True]
    assert memory.marked == []


def test_the_feed_is_made_only_with_the_switch_on(monkeypatch):
    monkeypatch.setattr(frames, 'FRAMES', False)
    assert frames.frame_feed() is None
    monkeypatch.setattr(frames, 'FRAMES', True)
    feed = frames.frame_feed(print)
    assert feed is not None
    assert feed.process is None  # nothing started before a run attaches it
    assert feed.said is print


# The feed's side with a board written here (no process)


def fed(clock: Clock) -> tuple[FrameFeed, Board]:
    feed = FrameFeed(clock=clock)
    board = Board.create(slots=3, slot_bytes=1 << 16)
    feed.board = board
    return feed, board


def test_the_feed_gives_the_newest_frame_while_fresh_unpickled_once_a_frame():
    clock = Clock()
    feed, board = fed(clock)
    try:
        assert feed.world() is None  # none published
        world = Source().raw_world()
        board.publish(pickle.dumps(world), tick=40, seen_at=clock.now)

        first, again = feed.world(), feed.world()
        light = feed.world(light=True)

        assert first == world
        assert again is first  # the same frame: not unpickled again
        assert light is not None
        assert (light.monsters, light.doors, light.player) == ((), (), world.player)
        assert feed.world(light=True) is light
        assert feed.tally.frames == 1

        clock.now += frames.FRESH_SECONDS + 0.01
        assert feed.world() is None  # stale: the run reads the game itself
        assert feed.tally.missed == 2  # and the first, with none published
    finally:
        feed.close()


def test_the_feed_says_its_line_once_a_minute():
    clock, lines = Clock(), []
    feed, board = fed(clock)
    feed.said = lines.append
    try:
        board.publish(pickle.dumps(Source().raw_world()), seen_at=clock.now)
        feed.world()
        clock.now += 0.002
        board.publish(pickle.dumps(Source().raw_world()), seen_at=clock.now)
        feed.world()
        clock.now += frames.SAID_EVERY
        feed.world()  # stale by now: counted as none fresh
    finally:
        feed.close()

    assert len(lines) == 1
    assert lines[0].startswith('2 takes, 0.0 frames/s published, 0.0/s unpickled; age at take 0.0/0.0/0.0 ms;')
    assert lines[0].endswith('; 1 with none fresh (the game read directly)')


# A reader process over a stand-in game process (tests/inventory_tracking/game/scene.py): real /proc reads, real
# shared memory, the default opener (the macro's GameMemory)


@pytest.fixture
def game_process():
    context = multiprocessing.get_context('spawn')
    ours, theirs = context.Pipe()
    child = context.Process(target=scene.run_scene, args=(theirs, False), daemon=True)
    child.start()
    try:
        assert ours.poll(30), 'the stand-in game did not start'
        pid, base, table = ours.recv()
        try:
            GameMemory(pid, base, table).close()
        except OSError as exc:
            pytest.skip(f'this sandbox cannot read another process: {exc}')
        yield pid, base, table
    finally:
        ours.send('stop')
        child.join(timeout=5)
        if child.is_alive():
            child.kill()


def first_world(feed: FrameFeed, *, light: bool = False, seconds: float = 30.0) -> World:
    ends = time.monotonic() + seconds
    while time.monotonic() < ends:
        found = feed.world(light=light)
        if found is not None:
            return found
        time.sleep(0.02)
    health = feed.board.health() if feed.board is not None else None
    raise AssertionError(f'no frame from the reader in {seconds} s: {health}')


def test_the_reader_process_publishes_the_look_the_run_would_make(game_process):
    pid, base, table = game_process
    feed = FrameFeed()
    try:
        feed.attach(pid, base, table)
        taken, light = first_world(feed), first_world(feed, light=True)
        direct = GameMemory(pid, base, table)
        try:
            assert taken.player is not None
            assert len(taken.monsters) == 56  # 60, less the 6 in a dead mode
            assert every_field(taken) == every_field(direct.raw_world())
            assert every_field(light) == every_field(direct.raw_world(light=True))
            assert look_at(direct, feed, light=False) == direct.world()  # the doors marked by the run's memory
        finally:
            direct.close()
        frame = feed.frame()
        assert frame is not None
        assert frame.tick > 0  # read on the game's ticks
        assert frame.read_began >= frame.seen_at
        assert feed.board is not None
        assert feed.board.health().said == 'running'
    finally:
        feed.close()


def test_a_reader_that_died_is_started_again_at_the_next_attach_and_given_up_after_its_restarts(game_process):
    pid, base, table = game_process
    feed = FrameFeed()
    try:
        feed.attach(pid, base, table)
        first_world(feed)
        first = feed.process
        feed.attach(pid, base, table)
        assert feed.process is first  # running: kept
        for _ in range(frames.RESTARTS - 1):
            os.kill(feed.process.pid, 9)
            feed.process.join(timeout=5)
            feed.attach(pid, base, table)
            assert feed.process is not first
            first = feed.process
            first_world(feed)
        os.kill(feed.process.pid, 9)
        feed.process.join(timeout=5)
        feed.attach(pid, base, table)  # RESTARTS made within the window: the runs read the game themselves
        assert feed.process is first
        assert not first.is_alive()
    finally:
        feed.close()


def test_a_reader_whose_game_is_gone_says_so_and_ends():
    feed = FrameFeed()
    try:
        feed.attach(2**22 + 12345, 0x10000000, 0x100000)  # no such process
        process = feed.process
        process.join(timeout=30)
        assert process.exitcode not in (None, 0)
        assert feed.board is not None
        assert feed.board.health().state == FAILED
        assert feed.board.health().error
        assert feed.world() is None
    finally:
        feed.close()


def test_the_game_given_the_reader_is_the_runs():
    assert Game(1, 2, 3) == Game(1, 2, 3)
    assert pickle.loads(pickle.dumps(Game(1, 2, 3))) == Game(1, 2, 3)
