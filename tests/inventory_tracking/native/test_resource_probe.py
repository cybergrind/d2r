import struct

import pytest

from inventory_tracking.native.resource_probe import read_item_arrays, read_location


def test_location_chain_is_rechecked():
    memory = {
        0x1020: struct.pack('<Q', 0x2000),
        0x2018: struct.pack('<Q', 0x3000),
        0x3090: struct.pack('<Q', 0x4000),
        0x41F8: struct.pack('<I', 40),
    }
    assert read_location(lambda a, n: memory[a], 0x1000) == 40
    counts = {}

    def changing(a, n):
        counts[a] = counts.get(a, 0) + 1
        if a == 0x2018 and counts[a] > 1:
            return struct.pack('<Q', 0x5000)
        return memory[a]

    with pytest.raises(ValueError, match='changed'):
        read_location(changing, 0x1000)


def test_item_arrays_reject_in_place_mutation():
    descriptor = struct.pack('<QQ', 0x20000, 1)
    stat = struct.pack('<HHi', 0, 70, 16)
    reads = 0

    def read(address, size):
        nonlocal reads
        if address == 0x10030:
            return descriptor
        if address == 0x20000:
            reads += 1
            return stat if reads == 1 else struct.pack('<HHi', 0, 70, 20)
        return bytes(size)

    result = read_item_arrays(read, 0x10000)
    assert not result['complete']
    assert 'changed' in result['reason']


def test_bad_candidate_descriptor_does_not_hide_other_arrays():
    def read(address, size):
        if address == 0x10030:
            return struct.pack('<QQ', 0x20000, 1)
        if address == 0x20000:
            return struct.pack('<HHi', 0, 70, 16)
        if address == 0x100A8:
            raise OSError('unmapped candidate')
        return bytes(size)

    result = read_item_arrays(read, 0x10000)
    assert result['complete']
    assert result['arrays'][0]['stats'][0]['raw'] == 16
    assert result['arrays'][1]['reason'] == 'unmapped candidate'
    assert result['arrays'][2]['stats'] == []


def test_identify_tome_is_collected_and_decoded(monkeypatch):
    from inventory_tracking.native import resource_probe
    from inventory_tracking.tracking.resources import resource_observations
    from tests.inventory_tracking.tracking.test_resources import record

    item = record(534, 0, stats=[{'id': 70, 'layer': 0, 'raw': 4}])
    item['stats_pointer'] = 0x10000
    monkeypatch.setattr(resource_probe, 'read_item_arrays', lambda read, pointer: item['resource_stats'])
    monkeypatch.setattr(resource_probe, 'unit_matches', lambda read, unit: True)
    monkeypatch.setattr(resource_probe, 'describe_item', lambda read, unit: item['details'])
    resources = resource_probe.collect_resources(
        lambda address, size: bytes(size),
        {'players': {'complete': True, 'units': []}, 'items': {'complete': True, 'units': [item]}},
    )
    result = resource_observations({'status': 'research', 'sample_monotonic': 100, 'resources': resources}, 7)
    assert result.identify_tome.value is not None
    assert result.identify_tome.value.quantity == 4


def test_opt_in_item_class_collects_ring_stats_without_changing_defaults(monkeypatch):
    from inventory_tracking.native import resource_probe

    item = {
        'unit_id': 9,
        'txt_id': 537,
        'mode': 0,
        'stats_pointer': 100,
        'details': {'quality': 4, 'owner_id': 7, 'inventory_page': 0, 'x': 3, 'y': 0},
    }
    groups = {'players': {'complete': True, 'units': []}, 'items': {'complete': True, 'units': [item]}}
    arrays = {'complete': True, 'arrays': [{'header_offset': 48, 'stats': [{'id': 105, 'layer': 0, 'raw': 10}]}]}
    monkeypatch.setattr(resource_probe, 'read_item_arrays', lambda *args: arrays)
    monkeypatch.setattr(resource_probe, 'unit_matches', lambda *args: True)
    monkeypatch.setattr(resource_probe, 'describe_item', lambda *args: item['details'])
    assert resource_probe.collect_resources(None, groups)['items'] == []
    result = resource_probe.collect_resources(None, groups, item_class=537)
    assert result['items'][0]['resource_stats'] == arrays
    assert result['items'][0]['unit_id'] == 9
    monkeypatch.setattr(resource_probe, 'unit_matches', lambda *args: False)
    assert not resource_probe.collect_resources(None, groups, item_class=537)['complete']
