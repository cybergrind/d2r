"""PE discovery must reject bad reads and ambiguous/stale evidence."""

import struct

import pytest

from inventory_tracking.native.images import discover_images, read_pe


def fixture():
    data = bytearray(512)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HHI', data, 132, 0x8664, 1, 12345)
    struct.pack_into('<H', data, 148, 240)
    optional = 152
    struct.pack_into('<H', data, optional, 0x20B)
    struct.pack_into('<I', data, optional + 16, 4096)
    struct.pack_into('<Q', data, optional + 24, 0x140000000)
    struct.pack_into('<II', data, optional + 56, 8192, 512)
    data[392:400] = b'.text\0\0\0'
    struct.pack_into('<IIII', data, 400, 4096, 4096, 512, 512)
    struct.pack_into('<I', data, 428, 0x60000020)
    return bytes(data)


def mapping(base):
    return {'start': base, 'end': base + 8192, 'permissions': 'r-xp', 'path': ''}


def test_relocated_anonymous_image_matches_disk_headers():
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    base = 0x200000000
    result = discover_images(lambda address, size: data[address - base : address - base + size], [mapping(base)], disk)
    assert result['status'] == 'candidate'
    assert result['candidate_base'] == base
    assert result['images'][0]['pe']['sections'][0]['rva'] == 4096


def test_duplicate_header_matches_are_ambiguous():
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    result = discover_images(
        lambda address, size: data[address % 8192 : address % 8192 + size], [mapping(8192), mapping(16384)], disk
    )
    assert result['status'] == 'ambiguous'
    assert 'candidate_base' not in result


def test_non_executable_header_copy_is_not_a_loaded_image():
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    copied = mapping(8192)
    copied['permissions'] = 'rw-p'
    result = discover_images(
        lambda address, size: data[address % 8192 : address % 8192 + size],
        [copied, mapping(16384)],
        disk,
    )
    assert result['status'] == 'candidate'
    assert result['candidate_base'] == 16384
    assert len(result['images']) == 2
    assert not result['images'][0]['executable_sections_mapped']


def test_fragmented_code_with_executable_entry_is_a_candidate():
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    header = mapping(8192)
    header.update(end=8192 + 512, permissions='r--s')
    entry = mapping(12288)
    entry['end'] = 12288 + 16
    result = discover_images(
        lambda address, size: data[address - 8192 : address - 8192 + size],
        [header, entry],
        disk,
    )
    assert result['status'] == 'candidate'
    assert result['candidate_base'] == 8192
    assert result['images'][0]['entry_executable']
    assert not result['images'][0]['executable_sections_mapped']


def test_short_reads_and_unbounded_headers_are_rejected():
    with pytest.raises(ValueError, match='Short PE header read'):
        read_pe(lambda offset, size: fixture()[offset : offset + size - 1])
    bad = bytearray(fixture())
    struct.pack_into('<I', bad, 60, 0xFFFFFFFF)
    with pytest.raises(ValueError, match='PE headers exceed 64 KiB bound'):
        read_pe(lambda offset, size: bad[offset : offset + size])


def test_mapping_gap_prevents_cross_mapping_header_read():
    calls = []
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    entry = mapping(8192)
    entry['end'] = 8192 + 64

    def reader(address, size):
        calls.append((address, size))
        return data[address - 8192 : address - 8192 + size]

    result = discover_images(reader, [entry], disk)
    assert result['status'] == 'unavailable'
    assert calls == [(8192, 64)]


def test_read_budget_stops_scan_without_claiming_unique_match():
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    result = discover_images(
        lambda address, size: data[address % 8192 : address % 8192 + size],
        [mapping(8192), mapping(16384)],
        disk,
        max_candidates=1,
    )
    assert result['status'] == 'incomplete'
    assert 'candidate_base' not in result


def test_restart_during_scan_discards_candidates():
    from unittest.mock import patch

    from inventory_tracking.native.image_probe import inspect_images

    token = {'pid': 123, 'start_ticks': '1'}
    game = {'identity': token, 'executable_fingerprint': {'error': 'missing'}}
    with (
        patch(
            'inventory_tracking.native.image_probe.identity',
            side_effect=[token, token, {'pid': 123, 'start_ticks': '2'}],
        ),
        patch('inventory_tracking.native.image_probe.process_mappings', return_value=[]),
        patch('inventory_tracking.native.image_probe.os.open', return_value=77),
        patch('inventory_tracking.native.image_probe.os.close'),
        patch('inventory_tracking.native.image_probe.discover_images', return_value={'candidate_base': 4096}),
    ):
        result = inspect_images(123, game)
    assert result['status'] == 'stale'
    assert 'candidate_base' not in result


def test_unrelated_mapping_changes_do_not_discard_image():
    from unittest.mock import patch

    from inventory_tracking.native.image_probe import inspect_images

    token = {'pid': 123, 'start_ticks': '1'}
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    game = {'identity': token, 'executable_fingerprint': {}}
    before = [mapping(8192), mapping(16384)]
    after = [mapping(8192), mapping(32768)]
    with (
        patch('inventory_tracking.native.image_probe.identity', return_value=token),
        patch('inventory_tracking.native.image_probe.disk_headers', return_value=({}, disk)),
        patch('inventory_tracking.native.image_probe.process_mappings', side_effect=[before, after]),
        patch('inventory_tracking.native.image_probe.os.open', return_value=77),
        patch('inventory_tracking.native.image_probe.os.close'),
        patch(
            'inventory_tracking.native.image_probe.os.pread', side_effect=lambda fd, a, o: data[o - 8192 : o - 8192 + a]
        ),
    ):
        result = inspect_images(123, game)
    assert result['status'] == 'candidate'


def test_read_mapping_change_discards_image():
    from unittest.mock import patch

    from inventory_tracking.native.image_probe import inspect_images

    token = {'pid': 123, 'start_ticks': '1'}
    data = fixture()
    disk = read_pe(lambda offset, size: data[offset : offset + size])
    game = {'identity': token, 'executable_fingerprint': {}}
    with (
        patch('inventory_tracking.native.image_probe.identity', return_value=token),
        patch('inventory_tracking.native.image_probe.disk_headers', return_value=({}, disk)),
        patch('inventory_tracking.native.image_probe.process_mappings', side_effect=[[mapping(8192)], []]),
        patch('inventory_tracking.native.image_probe.os.open', return_value=77),
        patch('inventory_tracking.native.image_probe.os.close'),
        patch(
            'inventory_tracking.native.image_probe.os.pread', side_effect=lambda fd, a, o: data[o - 8192 : o - 8192 + a]
        ),
    ):
        result = inspect_images(123, game)
    assert result['status'] == 'stale'
    assert 'candidate_base' not in result
