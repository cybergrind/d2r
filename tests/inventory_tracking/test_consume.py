import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.consume import observe_consume, read_consume
from inventory_tracking.models import ObservationStatus


CASES = json.loads((Path(__file__).parent / 'fixtures/consume_effects.json').read_text())


def memory_reader(case):
    blocks = [(b['address'], bytes.fromhex(b['hex'])) for b in case['blocks']]

    def read(address, size):
        for start, raw in blocks:
            if start <= address and address + size <= start + len(raw):
                return raw[address - start : address - start + size]
        raise ValueError('Unmapped fixture read')

    return read


@pytest.mark.parametrize(
    ('case', 'level'), list(zip(CASES, [None, 9, 7, 7], strict=True)), ids=[c['label'] for c in CASES]
)
def test_live_effect_level_not_aggregate_or_current_gear(case, level):
    result = read_consume(memory_reader(case), case['root'])
    assert result.active == (level is not None)
    assert result.level == level


def test_cycle_and_changed_state_are_rejected():
    case = CASES[1]
    read = memory_reader(case)
    head = struct.unpack('<Q', read(case['root'] + 0xD0, 8))[0]

    def cycle(address, size):
        raw = bytearray(read(address, size))
        if address == head and size == 0x80:
            struct.pack_into('<Q', raw, 0x68, head)
        return bytes(raw)

    with pytest.raises(ValueError, match='cycle or budget'):
        read_consume(cycle, case['root'])
    calls = 0

    def changed(address, size):
        nonlocal calls
        if address == case['root'] + 0xB48:
            calls += 1
            if calls > 1:
                return bytes(4)
        return read(address, size)

    with pytest.raises(ValueError, match='state changed'):
        read_consume(changed, case['root'])


def test_process_change_refuses_memory_access(monkeypatch):
    monkeypatch.setattr('inventory_tracking.consume.process_mappings', lambda _: [])
    monkeypatch.setattr('inventory_tracking.consume.identity', lambda _: {'pid': 2})

    def forbidden(*args):
        pytest.fail('Changed process must not be opened')

    monkeypatch.setattr('inventory_tracking.consume.os.open', forbidden)
    result = observe_consume(1, {'identity': {'pid': 1}}, {'groups': {'players': {'units': [{'unit_id': 3}]}}}, 3)
    assert result.status == ObservationStatus.UNAVAILABLE
    assert result.reason == 'Consume process changed'
