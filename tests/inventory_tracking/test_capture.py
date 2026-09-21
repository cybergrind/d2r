"""Capture bounds, missing bytes and signature boundaries."""

import io
import struct

import pytest

from inventory_tracking.capture import capture_ranges, scan_unit_table


def test_short_reads_preserve_holes_and_boundaries():
    calls = []

    def read(address, size):
        calls.append((address, size))
        return b'A' * (size - 1)

    stream = io.BytesIO()
    result = capture_ranges(read, [(100, 108), (112, 116)], stream, chunk_size=4)
    assert calls == [(100, 4), (104, 4), (112, 4)]
    assert result['bytes_read'] == 9
    assert [(x['address'], x['size']) for x in result['blocks']] == [(100, 3), (104, 3), (112, 3)]
    assert len(result['errors']) == 3
    assert stream.getvalue() == b'A' * 9


def test_budget_rejected_before_any_read():
    with pytest.raises(ValueError, match='Capture exceeds byte budget'):
        capture_ranges(lambda *args: pytest.fail('must not read'), [(0, 100)], io.BytesIO(), max_bytes=99)


def test_signature_spans_contiguous_blocks_but_not_holes():
    signature = bytes.fromhex('48 03 C7 49 8B 8C C6') + struct.pack('<I', 0x5000)
    blocks = [(0x1100, signature[:5]), (0x1105, signature[5:])]
    matches = scan_unit_table(blocks, 0x1000, 0x10000)
    assert matches == [{'signature_address': 0x1100, 'table_rva': 0x5000, 'table_address': 0x6000}]
    assert scan_unit_table([(0x1100, signature[:5]), (0x1106, signature[5:])], 0x1000, 0x10000) == []
    assert scan_unit_table(blocks, 0x1000, 0x4000) == []


def test_restart_after_capture_suppresses_signature_results():
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    from inventory_tracking.capture_probe import capture_image
    from inventory_tracking.images import read_pe

    from .test_images import fixture, mapping

    data = fixture() + bytes(8192 - 512)
    pe = read_pe(lambda offset, size: data[offset : offset + size])
    token = {'pid': 123, 'start_ticks': '1'}
    images = {'identity': token, 'candidate_base': 8192, 'images': [{'base': 8192, 'pe': pe}]}
    with (
        tempfile.TemporaryDirectory() as directory,
        patch(
            'inventory_tracking.capture_probe.identity',
            side_effect=[token, token, {'pid': 123, 'start_ticks': '2'}],
        ),
        patch('inventory_tracking.capture_probe.process_mappings', return_value=[mapping(8192)]),
        patch('inventory_tracking.capture_probe.os.open', return_value=77),
        patch('inventory_tracking.capture_probe.os.close'),
        patch(
            'inventory_tracking.capture_probe.os.pread',
            side_effect=lambda fd, size, offset: data[offset - 8192 : offset - 8192 + size],
        ),
    ):
        result = capture_image(123, images, Path(directory))
        assert result['status'] == 'stale'
        assert result['unit_table_candidates'] == []
        assert (Path(directory) / 'capture.json').exists()
