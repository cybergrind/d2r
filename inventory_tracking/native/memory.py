"""Read-only access to the game's memory: the one place /proc/<pid>/mem is opened. Never attaches or writes.

- `ProcessMemory`: a /proc/<pid>/mem handle bound to one process at a time;
- `BoundedReader`: reads only inside readable mappings, under a byte budget;
- `game_read`: one bounded read of the unit table, the process identity rechecked after it;
- `stable_read`: a small value read twice under the identity and mapping checks;
- `vm_read_spans`: many spans in few process_vm_readv calls; `vm_read`/`proc_read`: the access probes;
- `Replay`: each kind of pass's reads (a look, the loot's walk) asked of the kernel in one batch at the pass's start.
A stale pid or a remapped page gives an error, never wrong data: the callers make it "unread".
"""

import ctypes
import errno
import os
import threading
import time
from bisect import bisect_right
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.common import LOG, error
from inventory_tracking.native.process import identity, process_mappings


Read = Callable[[int, int], bytes]  # (address, size) -> bytes of the game's memory
Span = tuple[int, int]  # (address, size) of a read
READ_BUDGET = 8 * 1024 * 1024  # bytes one BoundedReader may read


def open_memory(pid: int) -> int:
    """A read-only fd on `pid`'s memory."""
    return os.open(f'/proc/{pid}/mem', os.O_RDONLY)


class ProcessMemory:
    """A read-only /proc/<pid>/mem handle bound to one process at a time; `with` closes it."""

    def __init__(self, pid: int | None = None, *, opener: Callable[[int], int] = open_memory) -> None:
        self.opener = opener
        self.pid: int | None = None
        self.fd: int | None = None
        if pid is not None:
            self.bind(pid)

    def bind(self, pid: int) -> None:
        """Open on `pid`, kept when it already is; an OSError leaves it unbound."""
        if pid == self.pid:
            return
        self.close()
        self.fd = self.opener(pid)
        self.pid = pid

    def fileno(self) -> int:
        if self.fd is None:
            raise OSError(errno.EBADF, 'process memory not bound')
        return self.fd

    def pread(self, address: int, size: int) -> bytes:
        """What the kernel gives, possibly short: for callers whose decoder rejects a short read itself."""
        return os.pread(self.fileno(), size, address)

    def read(self, address: int, size: int) -> bytes:
        data = os.pread(self.fileno(), size, address)
        if len(data) != size:
            raise ValueError('short read')
        return data

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
        self.pid, self.fd = None, None

    def __enter__(self) -> ProcessMemory:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class BoundedReader:
    """Reads of `fd` only inside readable `mappings`, at most 8 KiB each and `budget` bytes in all; `ranges` is
    what was read, for the mapping recheck after (`mappings_held`)."""

    def __init__(self, fd: int, mappings: list[dict[str, Any]], *, budget: int = READ_BUDGET) -> None:
        self.fd = fd
        self.budget = budget
        self.mappings = mappings
        self.starts = [m['start'] for m in mappings]
        self.bytes_requested = 0
        self.ranges: set[tuple[int, int]] = set()

    def read(self, address: int, size: int) -> bytes:
        self.bytes_requested += size
        if not 0 < size <= 8192 or self.bytes_requested > self.budget:
            raise ValueError('research read budget exceeded')
        cursor = address
        start_index = max(0, bisect_right(self.starts, address) - 1)
        for index in range(start_index, len(self.mappings)):
            mapping = self.mappings[index]
            if mapping['start'] > cursor:
                break
            if mapping['start'] <= cursor < mapping['end']:
                if not mapping['permissions'].startswith('r'):
                    break
                cursor = min(address + size, mapping['end'])
                if cursor == address + size:
                    self.ranges.add((address, size))
                    data = os.pread(self.fd, size, address)
                    if len(data) != size:
                        raise ValueError('short research read')
                    return data
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')


def read_mappings(mappings, address, size):
    """Compare only mapping portions used by a read, ignoring unrelated allocations.

    This is a before/after consistency check, not an atomic memory snapshot.
    """
    end = address + size
    return [
        (max(address, m['start']), min(end, m['end']), m['start'], m['permissions'], m['path'])
        for m in mappings
        if m['start'] < end and m['end'] > address
    ]


def mappings_held(before, after, ranges) -> bool:
    """Whether every (address, size) read lies in the same mappings `before` and `after` the reads."""
    return all(read_mappings(before, address, size) == read_mappings(after, address, size) for address, size in ranges)


@contextmanager
def bounded(pid: int, mappings: list[dict[str, Any]] | None = None, *, budget: int = READ_BUDGET):
    """A BoundedReader on `pid` over `mappings` (read after the open when None), closed on exit."""
    with ProcessMemory(pid) as memory:
        found = process_mappings(pid) if mappings is None else mappings
        yield BoundedReader(memory.fileno(), found, budget=budget)


def one_unit_table(capture) -> int | None:
    """The unit table address the attach's scan found; None unless exactly one (or with no capture yet)."""
    tables = {found.get('table_address') for found in (capture or {}).get('unit_table_candidates', ())}
    return next(iter(tables)) if len(tables) == 1 and None not in tables else None


def unit_table(capture) -> int:
    table = one_unit_table(capture)
    if table is None:
        raise ValueError('Expected one freshly scanned unit table address')
    return table


@contextmanager
def game_read(pid: int, images, capture, *, changed: str) -> Iterator[tuple[Read, int]]:
    """(bounded read, unit table) for one read of the game, opened read-only for it. ValueError: no single table,
    or the process changed by the end (`changed` is that error's text). A read that raised is not rechecked."""
    table = unit_table(capture)
    token = images['identity']
    with bounded(pid) as reader:
        yield reader.read, table
    if identity(pid) != token:
        raise ValueError(changed)


def stable_read[T](
    pid: int, images, address: int, size: int, decode: Callable[[bytes], T], *, name: str, unreadable: str
) -> T:
    """`decode` of `size` bytes at `address`, read twice: the process identity and the mappings checked before and
    after, the bytes alike both times. ValueError (text from `name`, `unreadable`) or OSError otherwise."""
    token = images['identity']
    if identity(pid) != token:
        raise ValueError(f'{name} process changed')
    before = read_mappings(process_mappings(pid), address, size)
    if not before or not all(m[3].startswith('r') for m in before):
        raise ValueError(unreadable)
    with ProcessMemory(pid) as memory:
        raw = memory.pread(address, size)
        value = decode(raw)
        if memory.pread(address, size) != raw:
            raise ValueError(f'{name} changed during read')
    if identity(pid) != token or read_mappings(process_mappings(pid), address, size) != before:
        raise ValueError(f'{name} process/mappings changed')
    return value


class IOVec(ctypes.Structure):
    _fields_ = [('iov_base', ctypes.c_void_p), ('iov_len', ctypes.c_size_t)]


def vm_read(pid, address, size):
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        fn = libc.process_vm_readv
    except AttributeError:
        return {'error': 'process_vm_readv unavailable in libc'}
    fn.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(IOVec),
        ctypes.c_ulong,
        ctypes.POINTER(IOVec),
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    fn.restype = ctypes.c_ssize_t
    buffer = ctypes.create_string_buffer(size)
    local = IOVec(ctypes.cast(buffer, ctypes.c_void_p), size)
    remote = IOVec(address, size)
    count = fn(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    if count < 0:
        number = ctypes.get_errno()
        return error(OSError(number, os.strerror(number)))
    return {'bytes_read': count, 'requested': size, 'ok': count == size}


IOV_MAX = 1024  # iovecs per process_vm_readv call (Linux UIO_MAXIOV)
REFUSED = frozenset((errno.EPERM, errno.EACCES, errno.ENOSYS))  # the kernel will not do it for this process


def vm_call():
    """libc's process_vm_readv, bound once for many reads (`vm_read_spans`), or None where it cannot be had."""
    try:
        call = ctypes.CDLL(None, use_errno=True).process_vm_readv
    except OSError, AttributeError:
        return None
    call.restype = ctypes.c_ssize_t
    pointer = ctypes.POINTER(IOVec)
    call.argtypes = (ctypes.c_int, pointer, ctypes.c_ulong, pointer, ctypes.c_ulong, ctypes.c_ulong)
    return call


def vm_read_spans(call, pid: int, spans, *, calls: float = float('inf')) -> list[bytes | None] | None:
    """Each span (address, size) of process `pid`, None where unreadable, in as few calls as the kernel's partial
    reads allow (a read stops at the first span it cannot read: that one is None, the rest are asked again). None
    when the kernel refuses the call altogether. At most `calls` calls: the spans past the last are None."""
    out: list[bytes | None] = [None] * len(spans)
    start = 0
    while start < len(spans) and calls > 0:
        calls -= 1
        chunk = spans[start : start + IOV_MAX]
        total = sum(size for _, size in chunk)
        buffer = ctypes.create_string_buffer(total)
        local = IOVec(ctypes.addressof(buffer), total)
        remote = (IOVec * len(chunk))(*(IOVec(address, size) for address, size in chunk))
        got = call(pid, ctypes.byref(local), 1, remote, len(chunk), 0)
        if got < 0:
            code = ctypes.get_errno()
            if code in REFUSED:
                return None
            if code == errno.ESRCH:
                return out  # the game is gone
            got = 0  # EFAULT: the first span is unreadable
        raw, offset, done = buffer.raw, 0, 0
        for _, size in chunk:
            if offset + size > got:
                break
            out[start + done] = raw[offset : offset + size]
            offset, done = offset + size, done + 1
        start += done + (done < len(chunk))  # past the span the read stopped at
    return out


# The replayed batch (2026-10-23, the player: "we need to find out way to bring memory reads from 100ms to <10ms for
# important information"; rca/2026-10-23/lag-findings.md). Every field of a look was one pread, 500-2000 a look or a
# loot walk, and each pread gives the GIL up and waits to have it back behind the service's Python (the convoy of
# rca/2026-10-13/latency-findings.md §2.3: 532 preads 0.6 ms alone, 146 ms under one busy thread at the 0.5 ms switch
# interval). The addresses a pass reads barely change from one pass to the next (the same units, the same stat
# lists), so a pass first asks the kernel for every span the last pass of its kind read, in one or two
# process_vm_readv calls, and its decoders are served from those bytes; a span not among them (a new unit, a moved
# list) is one pread as before. Off: every read is a pread.
REPLAY = True
REPLAY_SPANS = 16384  # spans kept of a pass for the next (a loot walk reads ~2000)
REPLAY_BYTES = 8 * 1024 * 1024  # bytes asked of a batch at most
REPLAY_CALLS = 8  # process_vm_readv calls a batch may make: each unreadable span costs one more
REPLAY_KEPT = 512  # pass times kept per kind (`Replay.report`)


@dataclass
class Tally:
    """One kind of pass, since the last report: passes, the spans served from the batch and read on their own, the
    batch calls, and each pass's milliseconds."""

    passes: int = 0
    served: int = 0
    missed: int = 0
    calls: int = 0
    ms: deque[float] = field(default_factory=lambda: deque(maxlen=REPLAY_KEPT))


class _Pass:
    """One pass under way: the bytes read for it at its start (`served`: a span's first copy; `extra`: its later
    copies in order) and the spans it reads, in order (the next pass's pattern)."""

    def __init__(self, served: dict[Span, bytes], extra: dict[Span, deque[bytes]]) -> None:
        self.served, self.extra, self.read = served, extra, list[Span]()
        self.hits = self.misses = 0


class _Chunk:
    """At most IOV_MAX spans of a pattern, ready for one call: the remote iovecs (read-only, so two runs' threads
    may share them; each call has a buffer of its own)."""

    def __init__(self, spans: list[Span]) -> None:
        self.spans = spans
        self.sizes = [size for _, size in spans]
        self.total = sum(self.sizes)
        self.remote = (IOVec * len(spans))(*(IOVec(address, size) for address, size in spans))


class Replay:
    """The reads of a process's memory through `fallback` (a pread), batched per kind of pass (`pass_of`): a pass
    asks the kernel at its start for every span the last pass of its kind read, in the order it read them (a stat
    list's header twice around its array, as `read_stats` rereads it), and serves each read in turn from those bytes:
    the n-th read of a span gets the n-th copy, a read beyond them or of a span not asked is `fallback`'s. Passes are
    the calling thread's: another thread's reads go to `fallback`; a pass begun inside one is part of it. `call` is
    libc's process_vm_readv (None, or refused: every read is `fallback`'s)."""

    def __init__(self, pid: int, fallback: Read, *, call=None, clock: Callable[[], float] = time.perf_counter) -> None:
        self.pid, self.fallback, self.call, self.clock = pid, fallback, call, clock
        self.patterns: dict[str, list[Span]] = {}
        self.prepared: dict[str, tuple[list[Span], list[_Chunk]]] = {}  # kind -> (pattern, its chunks)
        self.tallies: dict[str, Tally] = {}
        self.local = threading.local()
        # `said(text)` every `every` seconds of `clock` from a pass's end (`tallied`: the run's `memory reads` line)
        self.said: Callable[[str], None] | None = None
        self.every = 60.0
        self.said_at: float | None = None

    def share(self, patterns: dict[str, list[Span]], prepared: dict[str, tuple[list[Span], list[_Chunk]]]) -> None:
        """Keep the patterns in `patterns` and `prepared` (the runner's, across its runs of one thread at a time)."""
        self.patterns, self.prepared = patterns, prepared

    def read(self, address: int, size: int) -> bytes:
        current: _Pass | None = getattr(self.local, 'current', None)
        if current is None:
            return self.fallback(address, size)
        key = (address, size)
        data = current.served.pop(key, None)
        if data is None and (later := current.extra.get(key)):
            data = later.popleft()
        if data is not None:
            current.hits += 1
        else:
            current.misses += 1
            data = self.fallback(address, size)  # a read that fails is left out of the next pass's batch
        current.read.append(key)
        return data

    @contextmanager
    def pass_of(self, kind: str) -> Iterator[None]:
        """Within the block this thread's reads are one pass of `kind`."""
        if getattr(self.local, 'current', None) is not None or not REPLAY:
            yield
            return
        began = self.clock()
        try:
            calls, served, extra = self._batch(kind)
        except Exception as exc:  # whatever the batch met, the pass reads one pread a field: never the caller's
            LOG.warning('Memory: the batched read of %s failed (%s): one pread a field', kind, exc)
            calls, served, extra = 0, {}, {}
        current = self.local.current = _Pass(served, extra)
        try:
            yield
        finally:
            self.local.current = None
            if current.read:  # a pass that read nothing (a remembered answer) leaves the last pattern
                self.patterns[kind] = current.read[:REPLAY_SPANS]
            tally = self.tallies.setdefault(kind, Tally())
            tally.passes += 1
            tally.served += current.hits
            tally.missed += current.misses
            tally.calls += calls
            now = self.clock()
            tally.ms.append(1000 * (now - began))
            if self.said is not None:
                if self.said_at is None:
                    self.said_at = now
                elif now - self.said_at >= self.every:
                    self.said_at = now
                    self.said(tallied(self.report(), batched=self.call is not None and REPLAY))

    def _chunks(self, kind: str) -> list[_Chunk]:
        """The last pattern of `kind` as chunks for the calls, kept while the pattern is the same."""
        pattern = self.patterns.get(kind)
        if not pattern:
            return []
        kept = self.prepared.get(kind)
        if kept is not None and kept[0] == pattern:
            return kept[1]
        asked, total = [], 0
        for address, size in pattern:
            if not address or size <= 0:
                continue
            total += size
            if total > REPLAY_BYTES:
                break
            asked.append((address, size))
        chunks = [_Chunk(asked[at : at + IOV_MAX]) for at in range(0, len(asked), IOV_MAX)]
        self.prepared[kind] = (pattern, chunks)
        return chunks

    def _batch(self, kind: str) -> tuple[int, dict[Span, bytes], dict[Span, deque[bytes]]]:
        """(calls made, the first copy of each span read now, the later copies) for the last pattern of `kind`."""
        served: dict[Span, bytes] = {}
        extra: dict[Span, deque[bytes]] = {}
        if self.call is None:
            return 0, served, extra
        calls = 0
        for chunk in self._chunks(kind):
            calls += 1
            buffer = ctypes.create_string_buffer(chunk.total)
            local = IOVec(ctypes.addressof(buffer), chunk.total)
            got = self.call(self.pid, ctypes.byref(local), 1, chunk.remote, len(chunk.spans), 0)
            if got < 0 and ctypes.get_errno() in REFUSED:
                self.call = None  # refused for this process: reads one pread each from now on
                return calls, {}, {}
            raw, offset, found = buffer.raw, 0, list[bytes | None]()
            for size in chunk.sizes:
                if offset + size > got:
                    break
                found.append(raw[offset : offset + size])
                offset += size
            if len(found) < len(chunk.spans):  # stopped at a span it cannot read: that one is left, the rest asked
                tally = [0]

                def counted(*args, tally=tally):
                    tally[0] += 1
                    return self.call(*args)

                rest = chunk.spans[len(found) + 1 :]
                slow = vm_read_spans(counted, self.pid, rest, calls=REPLAY_CALLS - 1) if rest else []
                calls += tally[0]
                found += [None, *(slow if slow is not None else [None] * len(rest))]
            for key, data in zip(chunk.spans, found, strict=True):
                if data is None:
                    continue
                if key in served:
                    extra.setdefault(key, deque()).append(data)
                else:
                    served[key] = data
        return calls, served, extra

    def report(self) -> dict[str, Tally]:
        """The tallies since the last report, taken."""
        taken, self.tallies = self.tallies, {}
        return taken


def tallied(tallies: dict[str, Tally], *, batched: bool = True) -> str:
    """The `memory reads` line's text of `tallies`, the busiest kind first: passes, ms p50/p90/max, batch calls a
    pass, the share of reads served from the batch; `batched` False (the call refused or REPLAY off) leads it with
    "refused, pread"."""
    parts = [] if batched else ['refused, pread']
    for kind, tally in sorted(tallies.items(), key=lambda item: -sum(item[1].ms)):
        ms = sorted(tally.ms)
        if not ms:
            continue
        reads = tally.served + tally.missed
        parts.append(
            f'{kind} {tally.passes} passes {ms[len(ms) // 2]:.1f}/{ms[int(0.9 * (len(ms) - 1))]:.1f}/{ms[-1]:.1f} ms, '
            f'{tally.calls / max(1, tally.passes):.1f} calls, {reads / max(1, tally.passes):.0f} reads, '
            f'{100 * tally.served / max(1, reads):.0f}% batched'
        )
    return '; '.join(parts)


def proc_read(pid, address, size):
    try:
        with ProcessMemory(pid) as memory:
            count = len(memory.pread(address, size))
        return {'bytes_read': count, 'requested': size, 'ok': count == size}
    except OSError as exc:
        return error(exc)
