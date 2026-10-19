"""The one read-only memory layer: binding, bounded reads, the one unit table and the guarded reads."""

from unittest.mock import patch

import pytest

from inventory_tracking.native import memory
from inventory_tracking.native.memory import (
    BoundedReader,
    ProcessMemory,
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
