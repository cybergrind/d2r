"""The one read-only memory layer: binding, bounded reads, the one unit table and the guarded reads."""

import ctypes
import errno
import threading
from unittest.mock import patch

import pytest

from inventory_tracking.native import memory, memory as native_memory
from inventory_tracking.native.memory import (
    BoundedReader,
    ProcessMemory,
    Replay,
    game_read,
    mappings_held,
    one_unit_table,
    stable_read,
    unit_table,
)


TOKEN = {'pid': 12, 'start_ticks': 'abc'}
IMAGES = {'identity': TOKEN, 'candidate_base': 0x1000}
MAPPING = {'start': 0x2000, 'end': 0x3000, 'permissions': 'r--p', 'path': ''}


class Files:
    """os.open / os.pread / os.close of fake fds: each pid opens fd 100 + pid."""

    def __init__(self, data=b'abcdefgh'):
        self.data, self.opened, self.closed = data, [], []

    def open(self, path, flags):
        self.opened.append(path)
        return 100 + int(path.split('/')[2])

    def pread(self, fd, size, address):
        assert fd not in self.closed
        return self.data[:size]

    def close(self, fd):
        self.closed.append(fd)


@pytest.fixture
def files(monkeypatch):
    found = Files()
    monkeypatch.setattr(memory.os, 'open', found.open)
    monkeypatch.setattr(memory.os, 'pread', found.pread)
    monkeypatch.setattr(memory.os, 'close', found.close)
    return found


def test_process_memory_binds_once_rebinds_on_another_pid_and_closes(files):
    handle = ProcessMemory(7)
    handle.bind(7)
    assert files.opened == ['/proc/7/mem']
    handle.bind(8)
    assert files.closed == [107]
    assert (handle.pid, handle.fileno()) == (8, 108)
    with handle:
        assert handle.read(0, 4) == b'abcd'
    assert files.closed == [107, 108]
    assert handle.pid is None
    handle.close()  # closing twice closes nothing more
    assert files.closed == [107, 108]
    with pytest.raises(OSError, match='not bound'):
        handle.read(0, 4)


def test_a_failed_bind_leaves_it_unbound():
    def refuse(pid):
        raise PermissionError('denied')

    handle = ProcessMemory(opener=refuse)
    with pytest.raises(PermissionError):
        handle.bind(7)
    assert (handle.pid, handle.fd) == (None, None)


def test_a_short_read_is_an_error_but_pread_gives_what_the_kernel_gave(files):
    with ProcessMemory(7) as handle:
        assert handle.pread(0, 16) == b'abcdefgh'
        with pytest.raises(ValueError, match='short read'):
            handle.read(0, 16)


def test_bounded_reader_keeps_gap_and_permission_checks():
    mappings = [
        {'start': 100, 'end': 104, 'permissions': 'r--p'},
        {'start': 104, 'end': 108, 'permissions': 'r--p'},
        {'start': 112, 'end': 116, 'permissions': 'r--p'},
        {'start': 116, 'end': 120, 'permissions': '---p'},
    ]
    with patch('inventory_tracking.native.memory.os.pread', return_value=b'abcdef') as read:
        assert BoundedReader(1, mappings).read(102, 6) == b'abcdef'
        read.assert_called_once_with(1, 6, 102)
    for address, size in [(106, 8), (114, 4), (90, 4)]:
        with pytest.raises(ValueError, match='Unmapped or unreadable'):
            BoundedReader(1, mappings).read(address, size)


def test_bounded_reader_refuses_over_budget_and_short_reads():
    with patch('inventory_tracking.native.memory.os.pread', return_value=b'ab'):
        reader = BoundedReader(1, [MAPPING], budget=4)
        with pytest.raises(ValueError, match='short research read'):
            reader.read(0x2000, 4)
        with pytest.raises(ValueError, match='budget exceeded'):
            reader.read(0x2000, 2)


def test_mappings_held_compares_only_the_ranges_read():
    moved = {**MAPPING, 'start': 0x2800}
    assert mappings_held([MAPPING], [MAPPING, {**MAPPING, 'start': 0x9000, 'end': 0xA000}], {(0x2000, 8)})
    assert not mappings_held([MAPPING], [moved], {(0x2000, 8)})


@pytest.mark.parametrize(
    ('candidates', 'table'),
    [
        ([{'table_address': 0x5000}], 0x5000),
        ([{'table_address': 0x5000}, {'table_address': 0x5000}], 0x5000),
        ([{'table_address': 0x5000}, {'table_address': 0x6000}], None),
        ([], None),
    ],
)
def test_the_unit_table_is_the_one_scanned_address(candidates, table):
    capture = {'unit_table_candidates': candidates}
    assert one_unit_table(capture) == table
    if table is None:
        with pytest.raises(ValueError, match='Expected one freshly scanned unit table address'):
            unit_table(capture)
    else:
        assert unit_table(capture) == table


CAPTURE = {'unit_table_candidates': [{'table_address': 0x2000}]}


def test_game_read_yields_a_bounded_read_and_the_table_and_closes(files, monkeypatch):
    monkeypatch.setattr(memory, 'process_mappings', lambda pid: [MAPPING])
    monkeypatch.setattr(memory, 'identity', lambda pid: TOKEN)
    with game_read(12, IMAGES, CAPTURE, changed='Game process changed during the test read') as (read, table):
        assert table == 0x2000
        assert read(0x2000, 4) == b'abcd'
        with pytest.raises(ValueError, match='Unmapped'):
            read(0x4000, 4)
    assert files.closed == [112]


def test_game_read_rechecks_the_process_after_the_read(files, monkeypatch):
    monkeypatch.setattr(memory, 'process_mappings', lambda pid: [MAPPING])
    monkeypatch.setattr(memory, 'identity', lambda pid: {'pid': 12, 'start_ticks': 'new'})
    with (
        pytest.raises(ValueError, match=r'^Game process changed during the test read$'),
        game_read(12, IMAGES, CAPTURE, changed='Game process changed during the test read') as (read, _),
    ):
        read(0x2000, 4)
    assert files.closed == [112]


def test_game_read_lets_a_failed_read_through_unrechecked_and_opens_nothing_without_one_table(files, monkeypatch):
    monkeypatch.setattr(memory, 'process_mappings', lambda pid: [MAPPING])
    checked = []
    monkeypatch.setattr(memory, 'identity', lambda pid: checked.append(pid) or TOKEN)
    with pytest.raises(KeyError), game_read(12, IMAGES, CAPTURE, changed='changed'):
        raise KeyError('decode')
    assert checked == []
    assert files.closed == [112]
    with (
        pytest.raises(ValueError, match='Expected one'),
        game_read(12, IMAGES, {'unit_table_candidates': []}, changed='x'),
    ):
        pass
    assert files.opened == ['/proc/12/mem']


def flag(raw: bytes) -> bool:
    if raw not in (b'\x00', b'\x01'):
        raise ValueError('Invalid flag byte')
    return raw == b'\x01'


@pytest.mark.parametrize(
    ('reads', 'identities', 'mappings', 'expected'),
    [
        ([b'\x01', b'\x01'], [TOKEN, TOKEN], [[MAPPING], [MAPPING]], True),
        ([b'\x00', b'\x00'], [TOKEN, TOKEN], [[MAPPING], [MAPPING]], False),
        ([b'\x01', b'\x00'], [TOKEN, TOKEN], [[MAPPING], [MAPPING]], 'Flag changed during read'),
        ([b'\x02'], [TOKEN, TOKEN], [[MAPPING], [MAPPING]], 'Invalid flag byte'),
        ([b''], [TOKEN, TOKEN], [[MAPPING], [MAPPING]], 'Invalid flag byte'),
        ([], [{}], [[MAPPING]], 'Flag process changed'),
        ([], [TOKEN], [[]], 'Flag byte is unreadable'),
        ([], [TOKEN], [[{**MAPPING, 'permissions': '---p'}]], 'Flag byte is unreadable'),
        ([b'\x01', b'\x01'], [TOKEN, {}], [[MAPPING], [MAPPING]], 'Flag process/mappings changed'),
        ([b'\x01', b'\x01'], [TOKEN, TOKEN], [[MAPPING], [{**MAPPING, 'start': 0x1800}]], 'Flag process/mappings'),
    ],
)
def test_stable_read_reads_twice_under_the_identity_and_mapping_checks(
    files, monkeypatch, reads, identities, mappings, expected
):
    identity, mapped, read_bytes = iter(identities), iter(mappings), iter(reads)
    monkeypatch.setattr(memory, 'identity', lambda pid: next(identity))
    monkeypatch.setattr(memory, 'process_mappings', lambda pid: next(mapped))
    monkeypatch.setattr(memory.os, 'pread', lambda fd, size, address: next(read_bytes))

    def read():
        return stable_read(12, IMAGES, 0x2000, 1, flag, name='Flag', unreadable='Flag byte is unreadable')

    if isinstance(expected, bool):
        assert read() is expected
    else:
        with pytest.raises(ValueError, match=expected):
            read()
    assert len(files.closed) == len(files.opened)  # whatever happened, nothing is left open


class Spans:
    """A process's memory as {address: bytes} with a process_vm_readv over it that counts its calls and stops at the
    first span it cannot read, as the kernel does."""

    def __init__(self, data: dict[int, bytes]) -> None:
        self.data, self.calls, self.preads = data, [], []

    def pread(self, address, size):
        self.preads.append((address, size))
        if address not in self.data:
            raise ValueError('unreadable')
        return self.data[address][:size]

    def call(self, pid, local, count, remote, remote_count, flags):
        spans = [(remote[i].iov_base, remote[i].iov_len) for i in range(remote_count)]
        self.calls.append(spans)
        done = b''
        for address, size in spans:
            if address not in self.data:
                break
            done += self.data[address][:size]
        if not done:
            ctypes.set_errno(errno.EFAULT)
            return -1
        ctypes.memmove(local._obj.iov_base, done, len(done))
        return len(done)


def test_a_pass_is_served_from_one_batch_of_the_last_passes_reads_in_their_order():
    memory = Spans({0x100: b'HEAD', 0x200: b'ARRAY...'})
    replay = Replay(7, memory.pread, call=memory.call)
    with replay.pass_of('look'):  # the first: a pread each, the pattern recorded
        assert [replay.read(0x100, 4), replay.read(0x200, 8), replay.read(0x100, 4)] == [b'HEAD', b'ARRAY...', b'HEAD']
    assert len(memory.preads) == 3
    assert memory.calls == []
    memory.data[0x100] = b'NEW!'
    memory.preads.clear()

    with replay.pass_of('look'):
        # the header read twice around its array, as read_stats rereads it: each read its own copy, in order
        assert [replay.read(0x100, 4), replay.read(0x200, 8), replay.read(0x100, 4)] == [b'NEW!', b'ARRAY...', b'NEW!']
        assert replay.read(0x100, 4) == b'NEW!'  # a read past the copies asked: a pread

    assert memory.calls == [[(0x100, 4), (0x200, 8), (0x100, 4)]]
    assert memory.preads == [(0x100, 4)]
    tally = replay.report()['look']
    assert (tally.passes, tally.served, tally.missed, tally.calls) == (2, 3, 4, 1)


def test_an_unreadable_read_is_left_out_of_the_batch_and_a_refused_call_ends_the_batches():
    memory = Spans({0x100: b'HEAD'})
    replay = Replay(7, memory.pread, call=memory.call)
    for _ in range(2):
        with replay.pass_of('look'):
            assert replay.read(0x100, 4) == b'HEAD'
            with pytest.raises(ValueError, match='unreadable'):
                replay.read(0x500, 4)
    assert memory.calls == [[(0x100, 4)]]  # the unreadable span not asked again

    def refused(*args):
        ctypes.set_errno(errno.EPERM)
        return -1

    replay.call = refused
    with replay.pass_of('look'):
        assert replay.read(0x100, 4) == b'HEAD'
    assert replay.call is None  # one pread a field from then on
    memory.preads.clear()
    with replay.pass_of('look'):
        assert replay.read(0x100, 4) == b'HEAD'
    assert memory.preads == [(0x100, 4)]


def test_another_threads_reads_are_preads_and_a_pass_inside_a_pass_is_part_of_it():
    memory = Spans({0x100: b'HEAD', 0x200: b'BODY'})
    replay = Replay(7, memory.pread, call=memory.call)
    with replay.pass_of('look'):
        replay.read(0x100, 4)
        with replay.pass_of('inner'):
            replay.read(0x200, 4)
        other = threading.Thread(target=lambda: replay.read(0x200, 4))
        other.start()
        other.join()
    assert replay.patterns == {'look': [(0x100, 4), (0x200, 4)]}
    assert replay.read(0x100, 4) == b'HEAD'  # outside a pass: a pread
    assert len(memory.preads) == 4


def test_a_batch_that_fails_part_way_or_raises_leaves_every_read_to_a_pread_with_its_own_bytes():
    memory = Spans({0x100: b'AAAA', 0x200: b'BBBB', 0x300: b'CCCC'})
    replay = Replay(7, memory.pread, call=memory.call)

    def look():
        with replay.pass_of('look'):
            return [replay.read(address, 4) for address in (0x100, 0x200, 0x300)]

    look()
    # The game gone in the middle of the batch (ESRCH after the first span): the rest are preads
    memory.data[0x200] = b'bbbb'  # changed since: the pread reads it as it is now

    def gone(pid, local, count, remote, remote_count, flags):
        memory.calls.append(remote_count)
        if remote_count < 3:
            ctypes.set_errno(errno.ESRCH)
            return -1
        ctypes.memmove(local._obj.iov_base, b'AAAA', 4)
        return 4  # a partial read: the first span only

    replay.call = gone
    memory.preads.clear()
    assert look() == [b'AAAA', b'bbbb', b'CCCC']
    assert memory.preads == [(0x200, 4), (0x300, 4)]

    def broken(*args):
        raise RuntimeError('a binding gone wrong')

    replay.call = broken
    memory.preads.clear()
    assert look() == [b'AAAA', b'bbbb', b'CCCC']  # the error stays in the batch
    assert len(memory.preads) == 3

    replay.call = None  # no process_vm_readv in libc
    memory.preads.clear()
    assert look() == [b'AAAA', b'bbbb', b'CCCC']
    assert len(memory.preads) == 3


def test_a_list_relinked_since_the_last_pass_is_read_where_it_points_now():
    # unit A -> B in the first pass; then A -> C and B freed: the walk reads C, never the B of the last pass
    a, b, c = 0x1000, 0x2000, 0x3000
    memory = Spans({a: b.to_bytes(8, 'little'), b: bytes(8), c: bytes(8)})
    replay = Replay(7, memory.pread, call=memory.call)

    def walk():
        found, at = [], a
        with replay.pass_of('walk'):
            while at:
                found.append(at)
                at = int.from_bytes(replay.read(at, 8), 'little')
        return found

    assert walk() == [a, b]
    memory.data[a] = (c).to_bytes(8, 'little')
    del memory.data[b]

    assert walk() == [a, c]
    assert memory.calls[-1] == [(a, 8), (b, 8)]  # B asked, not read: the batch stopped there, A alone came
    assert walk() == [a, c]
    assert memory.calls[-1] == [(a, 8), (c, 8)]


def test_replay_off_reads_one_pread_a_field_and_the_line_says_when_the_call_is_refused(monkeypatch):
    memory = Spans({0x100: b'AAAA'})
    replay = Replay(7, memory.pread, call=memory.call)
    monkeypatch.setattr(native_memory, 'REPLAY', False)
    for _ in range(3):
        with replay.pass_of('look'):
            assert replay.read(0x100, 4) == b'AAAA'
    assert memory.calls == []
    assert len(memory.preads) == 3
    assert replay.patterns == {}
    assert replay.report() == {}

    monkeypatch.setattr(native_memory, 'REPLAY', True)
    replay.call = None
    said = []
    replay.said, replay.every = said.append, 0.0
    for _ in range(2):
        with replay.pass_of('look'):
            replay.read(0x100, 4)
    assert len(said) == 1
    assert said[0].startswith('refused, pread; look 2 passes')
