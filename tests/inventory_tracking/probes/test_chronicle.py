import struct

import pytest

from inventory_tracking.probes.chronicle import MAPS, NODE, entries


DATA, ARRAY, NODES = 0x1000, 0x2000, 0x3000


def memory(counts=(2, 0, 0)) -> dict[int, bytes]:
    """A data record whose first (set) map chains two entries in one of its two buckets."""
    return {
        DATA + MAPS: struct.pack('<QQQQ', 2, ARRAY, counts[0], 0),
        DATA + MAPS + 0x20: struct.pack('<QQQQ', 8, 0, counts[1], 0),
        DATA + MAPS + 0x40: struct.pack('<QQQQ', 0, 0, counts[2], 0),
        ARRAY: struct.pack('<QQ', 0, NODES),
        NODES: NODE.pack(NODES + 0x40, 271, 271, 0, 0, 29333333),
        NODES + 0x40: NODE.pack(0, 5, 5, 0, 0, 29166666),
    }


def reader(blocks):
    return lambda address, size: blocks[address][:size]


def test_entries_follow_each_bucket_chain_and_come_back_by_id():
    found = entries(reader(memory()), DATA)
    assert [entry['id'] for entry in found['set']] == [5, 271]
    assert found['set'][1]['found'] == 29333333 * 60
    assert found['unique'] == []
    assert found['runeword'] == []


def test_a_map_whose_count_disagrees_with_its_chains_is_refused():
    with pytest.raises(ValueError, match='set'):
        entries(reader(memory(counts=(3, 0, 0))), DATA)
