"""Frames shared between processes (native/frames.py `Board`, 2026-10-23): a frame is taken whole or not at all."""

import os
import struct
from multiprocessing import get_context

import pytest

from inventory_tracking.native import frames
from inventory_tracking.native.frames import FAILED, RUNNING, Board


@pytest.fixture
def board():
    made = Board.create(slots=3, slot_bytes=4096)
    yield made
    made.close()


def test_before_any_frame_there_is_none(board):
    assert board.latest() == 0
    assert board.newest() is None
    assert board.frame(1) is None


def test_the_newest_frame_is_taken_whole_with_its_times(board):
    board.publish(b'first', tick=40, seen_at=1.0, read_began=1.001, read_ended=1.002, clock=lambda: 1.003)
    board.publish(b'second', tick=80, seen_at=2.0, read_began=2.001, read_ended=2.002, clock=lambda: 2.003)

    found = board.newest()

    assert found is not None
    assert (found.seq, found.payload, found.tick) == (2, b'second', 80)
    assert (found.seen_at, found.read_began, found.read_ended, found.published_at) == (2.0, 2.001, 2.002, 2.003)
    assert board.frame(1) is not None  # still in its slot
    assert board.frame(1).payload == b'first'


def test_a_slot_the_writer_came_back_to_no_longer_gives_the_old_frame(board):
    for index in range(4):  # frame 4 goes into frame 1's slot
        board.publish(f'frame {index + 1}'.encode())

    assert board.frame(1) is None
    assert board.frame(4).payload == b'frame 4'


def test_a_slot_being_written_is_not_taken(board):
    board.publish(b'whole')
    at = board._slot(2)
    struct.pack_into('<Q', board.buf, at, 2 * 2 + 1)  # frame 2 begun, not finished
    struct.pack_into('<Q', board.buf, frames.LATEST, 2)  # the header said first: a reader must not care

    assert board.frame(2) is None
    assert board.newest() is None  # the writer laps every copy


def test_a_frame_overwritten_during_its_copy_is_not_taken(board, monkeypatch):
    board.publish(b'old')
    real = bytes

    def copy_then_overwrite(view):
        data = real(view)
        struct.pack_into('<Q', board.buf, board._slot(1), 2 * 4 + 1)  # the writer is back at this slot
        return data

    monkeypatch.setattr(frames, 'bytes', copy_then_overwrite, raising=False)

    assert board.frame(1) is None


def test_a_frame_over_the_slot_is_refused_and_nothing_is_published(board):
    with pytest.raises(ValueError, match='over the slot'):
        board.publish(bytes(4097))
    assert board.latest() == 0


def test_the_heartbeat_and_the_failure_are_read_from_the_header(board):
    board.beat(1234, RUNNING, 55.5)
    assert board.health().pid == 1234
    assert board.health().said == 'running'
    assert board.health().alive_at == 55.5

    board.fail('read failed: ' + 'x' * 400)
    board.beat(1234, FAILED, 56.0)

    health = board.health()
    assert health.said == 'failed'
    assert health.error.startswith('read failed: x')
    assert len(health.error) == frames.ERROR_BYTES


def _publisher(name: str, count: int) -> None:
    board = Board.attach(name)
    try:
        for index in range(count):
            board.publish(f'from the child {index}'.encode(), tick=40 * index)
    finally:
        board.close()


def test_frames_published_by_another_process_are_taken_here():
    board = Board.create(slots=3, slot_bytes=4096)
    try:
        child = get_context('spawn').Process(target=_publisher, args=(board.name, 5))
        child.start()
        child.join(timeout=30)
        assert child.exitcode == 0

        found = board.newest()

        assert found is not None
        assert (found.seq, found.payload, found.tick) == (5, b'from the child 4', 160)
    finally:
        board.close()


def test_a_block_not_a_board_is_refused():
    from multiprocessing import shared_memory

    other = shared_memory.SharedMemory(create=True, size=4096)
    try:
        with pytest.raises(ValueError, match='not a frame board'):
            Board.attach(other.name)
    finally:
        other.close()
        other.unlink()


def test_boards_left_by_processes_no_longer_running_are_swept_in_this_namespace_only(tmp_path):
    ours = frames.namespace()
    gone = tmp_path / f'{frames.PREFIX}-{ours}-{2**22 + 54321}-1'
    alive = tmp_path / f'{frames.PREFIX}-{ours}-{os.getpid()}-1'
    elsewhere = tmp_path / f'{frames.PREFIX}-1-{2**22 + 54321}-1'  # another pid namespace's: its pids are not ours
    for path in (gone, alive, elsewhere):
        path.write_bytes(b'')

    assert frames.sweep(tmp_path) == [gone.name]
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted([alive.name, elsewhere.name])


def test_a_board_is_named_by_namespace_and_process():
    made = Board.create(slots=1, slot_bytes=16)
    try:
        assert made.name.startswith(f'{frames.PREFIX}-{frames.namespace()}-{os.getpid()}-')
    finally:
        made.close()
