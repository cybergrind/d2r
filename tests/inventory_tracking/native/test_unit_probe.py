"""Research snapshots must reject mutations before publication."""

import struct
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from inventory_tracking.native.unit_probe import inspect_units
from inventory_tracking.native.units import walk_units


def snapshot(*, mutation=None, late=False):
    header = bytearray(0x160)
    struct.pack_into('<IIII', header, 0, 4, 531, 128, 2)
    struct.pack_into('<Q', header, 0x10, 0x4000)
    heads = struct.pack('<128Q', 0x3000, *([0] * 127))
    item = walk_units(lambda a, n: bytes(header), struct.unpack('<128Q', heads), 4)
    reads = 0

    def read(address, size):
        nonlocal reads
        if size == 1024:
            return heads if address == 0x2000 else bytes(1024)
        if address == 0x3000:
            reads += 1
            changed = bytearray(header)
            if mutation and (not late or reads >= 2):
                fmt, offset, value = mutation
                struct.pack_into(fmt, changed, offset, value)
            return bytes(changed)
        raise AssertionError((address, size))

    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:

        def mock(name, **kwargs):
            return stack.enter_context(patch('inventory_tracking.native.unit_probe.' + name, **kwargs))

        mock('identity', return_value={'pid': 1})
        mock('process_mappings', return_value=[])
        mock('os.open', return_value=42)
        mock('os.close')
        reader = mock('ResearchReader').return_value
        reader.read.side_effect = read
        reader.ranges = set()
        reader.bytes_requested = 0
        mock('read_pe', return_value={})
        mock('walk_units', side_effect=[{'units': [], 'complete': True, 'errors': []}, item])
        mock('describe_item', return_value={'owner_id': 7, 'x': 12, 'y': 0})
        images = {'identity': {'pid': 1}, 'candidate_base': 0x1000, 'images': [{'base': 0x1000, 'pe': {}}]}
        capture = {'unit_table_candidates': [{'table_address': 0x1000}]}
        result = inspect_units(1, images, capture, Path(directory))
        import json

        manifest = json.loads((Path(directory) / 'units.json').read_text())
        return result, manifest


def test_unchanged_research_remains_complete_and_unvalidated():
    result, _ = snapshot()
    assert result['complete']
    assert result['validated'] is False


@pytest.mark.parametrize(
    'mutation',
    [('<I', 0x0C, 0), ('<Q', 0x10, 0x5000), ('<Q', 0x88, 0x6000)],
    ids=['mode', 'data-pointer', 'stats-pointer'],
)
def test_mode_or_pointer_change_rejects_snapshot(mutation):
    result, _ = snapshot(mutation=mutation)
    assert not result['complete']
    assert result['summary'] == {}


def test_change_after_initial_unit_check_rejects_snapshot():
    result, manifest = snapshot(mutation=('<I', 0x0C, 0), late=True)
    assert not result['complete']
    assert result['summary'] == {}
    assert manifest['groups']['items']['errors']


def test_indexed_reader_keeps_gap_and_permission_checks():
    from inventory_tracking.native.unit_probe import ResearchReader

    mappings = [
        {'start': 100, 'end': 104, 'permissions': 'r--p'},
        {'start': 104, 'end': 108, 'permissions': 'r--p'},
        {'start': 112, 'end': 116, 'permissions': 'r--p'},
        {'start': 116, 'end': 120, 'permissions': '---p'},
    ]
    with patch('inventory_tracking.native.unit_probe.os.pread', return_value=b'abcdef') as read:
        assert ResearchReader(1, mappings).read(102, 6) == b'abcdef'
        read.assert_called_once_with(1, 6, 102)
    for address, size in [(106, 8), (114, 4), (90, 4)]:
        with pytest.raises(ValueError, match='Unmapped or unreadable'):
            ResearchReader(1, mappings).read(address, size)
