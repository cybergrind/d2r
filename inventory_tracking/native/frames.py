"""Frames shared between processes: one writer publishes each frame's bytes into shared memory, any reader takes the
newest in microseconds, with no syscall, no lock and no wait on the writer (2026-10-23, rca/2026-10-23/
realtime-reads-findings.md).

`Board` is a block of `SharedMemory`: a header and SLOTS slots. Frame n goes into slot n % SLOTS, guarded by the slot's
sequence word (a seqlock): 2n + 1 while it is written, 2n once whole; the header's `latest` is then n. A reader copies
the newest slot's bytes and keeps them only when the sequence word is 2n before and after the copy, so a frame the
writer overwrote under it is never taken (with three slots the writer comes back to a slot two frames later). The
words are plain stores and loads: on x86-64 (stores are not reordered with stores, loads not with loads) this is a
correct seqlock; another architecture would need fences.

The header also holds the writer's pid, a heartbeat (`alive_at`, CLOCK_MONOTONIC, the same clock in every process),
its state and its last error's text, so a reader tells a writer that is gone from a game with nothing new.
"""

import os
import struct
import time
from contextlib import suppress
from dataclasses import dataclass
from multiprocessing import shared_memory
from pathlib import Path


MAGIC = b'D2FR'
VERSION = 1
SLOTS = 3
SLOT_BYTES = 2 * 1024 * 1024  # a frame's payload at most (a Chaos Sanctuary world pickles to ~60 KB)
ERROR_BYTES = 256
# magic, version, slots, (pad), slot bytes, latest frame (0: none), writer pid, state, heartbeat (monotonic s), error
# length: the 8-byte words on 8-byte offsets
HEADER = struct.Struct('<4sII4xQQIIdI')
LATEST, BEAT, ERROR_LENGTH = 24, 32, 48  # offsets of the latest frame's number, (pid, state, heartbeat), error length
# sequence word, payload length, the game's tick (ms; 0 unread), flags, tick seen at, read began, read ended,
# published at (monotonic s)
SLOT = struct.Struct('<QQIIdddd')
HEADER_BYTES = 128
SLOT_HEAD = 64

STARTING, RUNNING, STOPPED, FAILED = 0, 1, 2, 3
STATES = {STARTING: 'starting', RUNNING: 'running', STOPPED: 'stopped', FAILED: 'failed'}
RETRIES = 4  # copies of a frame tried before giving up on it (the writer lapped the reader)


PREFIX = 'd2r-frames'
SHM = Path('/dev/shm')
MADE = 0  # boards this process made (their names)


def namespace() -> str:
    """This process's pid namespace (its inode): a board's pid is told alive only in its own namespace (a sandboxed
    test sees none of the service's processes)."""
    try:
        return os.readlink('/proc/self/ns/pid').removeprefix('pid:[').removesuffix(']')
    except OSError:
        return '0'


def sweep(directory: Path = SHM) -> list[str]:
    """Remove the boards (PREFIX-<namespace>-<pid>-<n>) of this pid namespace's processes no longer running; their
    names."""
    removed = []
    for path in directory.glob(f'{PREFIX}-{namespace()}-*-*'):
        pid = path.name.split('-')[-2]
        if pid.isdigit() and not Path(f'/proc/{pid}').exists():
            with suppress(OSError):
                path.unlink()
                removed.append(path.name)
    return removed


@dataclass(frozen=True)
class Frame:
    """One published frame: its number, the game's tick (ms of the game's clock; 0 unread), when the writer saw that
    tick, when its read began and ended and when it was published (monotonic s), and its payload."""

    seq: int
    tick: int
    seen_at: float
    read_began: float
    read_ended: float
    published_at: float
    payload: bytes
    flags: int = 0


@dataclass(frozen=True)
class Health:
    """The writer as the header says: pid, state, heartbeat (monotonic s), last error, the newest frame's number."""

    pid: int
    state: int
    alive_at: float
    error: str
    latest: int

    @property
    def said(self) -> str:
        return STATES.get(self.state, str(self.state))


def board_bytes(slots: int = SLOTS, slot_bytes: int = SLOT_BYTES) -> int:
    return HEADER_BYTES + ERROR_BYTES + slots * (SLOT_HEAD + slot_bytes)


class Board:
    """The shared block. `create` makes it (the owner unlinks it at `close`), `attach` opens one by name."""

    def __init__(self, memory: shared_memory.SharedMemory, *, owner: bool) -> None:
        self.memory, self.owner = memory, owner
        buf = memory.buf
        assert buf is not None
        self.buf = buf
        magic, version, slots, slot_bytes, *_ = HEADER.unpack_from(self.buf, 0)
        if magic != MAGIC or version != VERSION:
            self.buf.release()
            memory.close()
            raise ValueError(f'not a frame board: {magic!r} version {version}')
        self.slots, self.slot_bytes = slots, slot_bytes
        self.written = self.latest()  # the writer's own count (`publish`)

    @classmethod
    def create(cls, *, slots: int = SLOTS, slot_bytes: int = SLOT_BYTES) -> Board:
        """A new board, named PREFIX-<namespace>-<pid>-<n>; the boards of processes no longer running are removed
        first. Not tracked by multiprocessing's resource tracker (no helper process): `close` unlinks it."""
        sweep()
        global MADE
        MADE += 1
        memory = shared_memory.SharedMemory(
            name=f'{PREFIX}-{namespace()}-{os.getpid()}-{MADE}',
            create=True,
            size=board_bytes(slots, slot_bytes),
            track=False,
        )
        buf = memory.buf
        assert buf is not None
        buf[: HEADER_BYTES + ERROR_BYTES] = bytes(HEADER_BYTES + ERROR_BYTES)
        HEADER.pack_into(buf, 0, MAGIC, VERSION, slots, slot_bytes, 0, 0, STARTING, 0.0, 0)
        return cls(memory, owner=True)

    @classmethod
    def attach(cls, name: str) -> Board:
        """The board `name`, not tracked by this process (only its creator unlinks it)."""
        return cls(shared_memory.SharedMemory(name=name, track=False), owner=False)

    @property
    def name(self) -> str:
        return self.memory.name

    def _slot(self, seq: int) -> int:
        return HEADER_BYTES + ERROR_BYTES + (seq % self.slots) * (SLOT_HEAD + self.slot_bytes)

    # The writer's side

    def publish(
        self, payload: bytes, *, tick: int = 0, seen_at: float = 0.0, read_began: float = 0.0,
        read_ended: float = 0.0, flags: int = 0, clock=time.monotonic,
    ) -> int:  # fmt: skip
        """Frame number of `payload` published; ValueError over the slot's size (nothing published)."""
        if len(payload) > self.slot_bytes:
            raise ValueError(f'a frame of {len(payload)} bytes over the slot of {self.slot_bytes}')
        seq = self.written + 1
        at = self._slot(seq)
        struct.pack_into('<Q', self.buf, at, 2 * seq + 1)  # being written
        self.buf[at + SLOT_HEAD : at + SLOT_HEAD + len(payload)] = payload
        SLOT.pack_into(self.buf, at, 2 * seq + 1, len(payload), tick, flags, seen_at, read_began, read_ended, clock())
        struct.pack_into('<Q', self.buf, at, 2 * seq)  # whole
        struct.pack_into('<Q', self.buf, LATEST, seq)
        self.written = seq
        return seq

    def beat(self, pid: int, state: int, now: float) -> None:
        """The writer's heartbeat: its pid, state and the time (`alive_at`)."""
        struct.pack_into('<IId', self.buf, BEAT, pid, state, now)

    def fail(self, text: str) -> None:
        raw = text.encode('utf-8', 'replace')[:ERROR_BYTES]
        self.buf[HEADER_BYTES : HEADER_BYTES + len(raw)] = raw
        struct.pack_into('<I', self.buf, ERROR_LENGTH, len(raw))

    # A reader's side

    def latest(self) -> int:
        """The newest whole frame's number; 0 before the first."""
        return struct.unpack_from('<Q', self.buf, LATEST)[0]

    def health(self) -> Health:
        _, _, _, _, latest, pid, state, alive_at, length = HEADER.unpack_from(self.buf, 0)
        error = bytes(self.buf[HEADER_BYTES : HEADER_BYTES + min(length, ERROR_BYTES)]).decode('utf-8', 'replace')
        return Health(pid, state, alive_at, error, latest)

    def frame(self, seq: int) -> Frame | None:
        """Frame `seq` as published, None when it is not (yet, or any more) whole in its slot."""
        if seq <= 0:
            return None
        at = self._slot(seq)
        head = SLOT.unpack_from(self.buf, at)
        if head[0] != 2 * seq or head[1] > self.slot_bytes:
            return None
        payload = bytes(self.buf[at + SLOT_HEAD : at + SLOT_HEAD + head[1]])
        if struct.unpack_from('<Q', self.buf, at)[0] != 2 * seq:
            return None  # overwritten during the copy
        _, _, tick, flags, seen_at, began, ended, published = head
        return Frame(seq, tick, seen_at, began, ended, published, payload, flags)

    def newest(self) -> Frame | None:
        """The newest whole frame; None before the first or when the writer laps every copy (RETRIES)."""
        for _ in range(RETRIES):
            seq = self.latest()
            if seq == 0:
                return None
            found = self.frame(seq)
            if found is not None:
                return found
        return None

    def close(self) -> None:
        """Let go of the block; its creator also unlinks it."""
        self.buf.release()
        self.memory.close()
        if self.owner:
            with suppress(FileNotFoundError):
                self.memory.unlink()
