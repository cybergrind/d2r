"""Read-only access to the game's memory: the one place /proc/<pid>/mem is opened. Never attaches or writes.

- `ProcessMemory`: a /proc/<pid>/mem handle bound to one process at a time;
- `BoundedReader`: reads only inside readable mappings, under a byte budget;
- `game_read`: one bounded read of the unit table, the process identity rechecked after it;
- `stable_read`: a small value read twice under the identity and mapping checks;
- `vm_read_spans`: many spans in few process_vm_readv calls; `vm_read`/`proc_read`: the access probes.
A stale pid or a remapped page gives an error, never wrong data: the callers make it "unread".
"""

import ctypes
import errno
import os
from bisect import bisect_right
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from inventory_tracking.common import error
from inventory_tracking.native.process import identity, process_mappings


Read = Callable[[int, int], bytes]  # (address, size) -> bytes of the game's memory
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


def vm_read_spans(call, pid: int, spans) -> list[bytes | None] | None:
    """Each span (address, size) of process `pid`, None where unreadable, in as few calls as the kernel's partial
    reads allow (a read stops at the first span it cannot read: that one is None, the rest are asked again). None
    when the kernel refuses the call altogether."""
    out: list[bytes | None] = [None] * len(spans)
    start = 0
    while start < len(spans):
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


def proc_read(pid, address, size):
    try:
        with ProcessMemory(pid) as memory:
            count = len(memory.pread(address, size))
        return {'bytes_read': count, 'requested': size, 'ok': count == size}
    except OSError as exc:
        return error(exc)
