import json
import struct

from inventory_tracking.buff_probe import collect_candidates, collect_effect_lists, record


def test_candidate_walk_bounds_cycles_and_unreadable_pointers():
    root = bytearray(0x1000)
    child = bytearray(0x100)
    struct.pack_into('<QQ', root, 0, 0x20000, 0x30000)
    struct.pack_into('<Q', child, 0, 0x10000)
    memory = {0x10000: bytes(root), 0x20000: bytes(child)}
    calls = []

    def read(address, size):
        calls.append(address)
        if address not in memory:
            raise ValueError('unmapped')
        return memory[address][:size]

    result = collect_candidates(read, 0x10000)
    assert calls == [0x10000, 0x20000, 0x30000]
    assert len(result['blocks']) == 2
    assert result['errors'] == [{'address': 0x30000, 'reason': 'unmapped'}]
    assert not result['truncated']
    result = collect_candidates(read, 0x10000, max_nodes=1)
    assert len(result['blocks']) == 1
    assert result['truncated']


def test_interrupted_recording_publishes_completion(monkeypatch, tmp_path):
    monkeypatch.setattr('inventory_tracking.buff_probe.LiveReader.connect', lambda *_: (1, {'identity': {}}, {}))
    monkeypatch.setattr('inventory_tracking.buff_probe.capture_sample', lambda *_: {'stable': True})

    def stop(_):
        raise KeyboardInterrupt

    monkeypatch.setattr('inventory_tracking.buff_probe.time.sleep', stop)
    assert record(tmp_path, {'state': 'running'}, seconds=30) == 0
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['state'] == 'complete'
    assert report['samples'] == 1
    assert report['stopped_by'] == 'user'
    assert json.loads((tmp_path / 'samples.jsonl').read_text()) == {'stable': True}


def test_unmapped_stat_values_do_not_exhaust_discovery_budget():
    root = bytearray(0x1000)
    struct.pack_into('<QQ', root, 0, 0x90000, 0x20000)
    memory = {0x10000: bytes(root), 0x20000: bytes(0x100)}
    result = collect_candidates(
        lambda address, size: memory[address][:size],
        0x10000,
        max_nodes=2,
        readable=lambda address, size: address in memory,
    )
    assert [b['address'] for b in result['blocks']] == [0x10000, 0x20000]
    assert not result['truncated']


def test_effect_chain_reaches_deep_buff_and_reports_cycle_and_budget():
    memory = bytearray(0x2000)
    struct.pack_into('<Q', memory, 0xD0, 0x200)
    for address in range(0x200, 0xC00, 0x200):
        struct.pack_into('<Q', memory, address + 0x68, address + 0x200 if address < 0xA00 else 0)
    struct.pack_into('<II', memory, 0xA20, 208, 375)

    def read(address, size):
        return bytes(memory[address : address + size])

    result = collect_effect_lists(read, 0)
    assert result['complete']
    assert result['chains'][1]['addresses'] == [0x200, 0x400, 0x600, 0x800, 0xA00]
    assert struct.unpack_from('<II', bytes.fromhex(result['nodes'][-1]['hex']), 0x20) == (208, 375)
    limited = collect_effect_lists(read, 0, max_nodes=3)
    assert not limited['complete']
    assert len(limited['nodes']) == 3
    assert limited['errors'][0]['reason'] == 'Effect list node limit'
    struct.pack_into('<Q', memory, 0xA68, 0x200)
    cycled = collect_effect_lists(read, 0)
    assert not cycled['complete']
    assert cycled['errors'][0]['reason'] == 'Effect list cycle'


def test_effect_chain_rejects_changed_identity():
    memory = bytearray(0x400)
    struct.pack_into('<Q', memory, 0xD0, 0x200)
    reads = 0

    def read(address, size):
        nonlocal reads
        if address == 0x200 and size == 0xD0:
            reads += 1
            if reads == 2:
                struct.pack_into('<I', memory, 0x220, 208)
        return bytes(memory[address : address + size])

    result = collect_effect_lists(read, 0)
    assert not result['complete']
    assert result['errors'][-1]['reason'] == 'Effect list identity or links changed'
