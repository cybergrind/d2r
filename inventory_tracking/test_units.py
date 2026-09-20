"""Research traversal must reject cycles, wrong buckets and invalid reads."""

import struct
import unittest

from .units import walk_units


def unit(unit_type, unit_id, next_address=0):
    data = bytearray(0x160)
    struct.pack_into('<IIII', data, 0, unit_type, 0, unit_id, 2)
    struct.pack_into('<Q', data, 0x158, next_address)
    return bytes(data)


class UnitTests(unittest.TestCase):
    def test_cycle_terminates_and_marks_incomplete(self):
        heads = [0] * 128
        heads[1] = 4096
        result = walk_units(lambda address, size: unit(4, 1, 4096), heads, 4)
        assert len(result['units']) == 1
        assert result['complete'] is False
        assert 'cycle' in result['errors'][0]['error']

    def test_wrong_type_is_not_published(self):
        heads = [4096] + [0] * 127
        result = walk_units(lambda address, size: unit(1, 128), heads, 4)
        assert result['units'] == []
        assert not result['complete']

    def test_chain_budget_is_enforced(self):
        heads = [4096] + [0] * 127
        result = walk_units(lambda address, size: unit(4, 128, address + 512), heads, 4, max_units=2)
        assert len(result['units']) == 2
        assert not result['complete']

    def test_stat_discovery_handles_shifted_array_and_rejects_large_counts(self):
        from .units import discover_stat_arrays

        header = bytearray(0x200)
        struct.pack_into('<QQ', header, 0x80, 0x20000, 2)
        struct.pack_into('<QQ', header, 0xA8, 0x30000, 100000)
        stats = struct.pack('<HHiHHi', 0, 6, 100 * 256, 0, 7, 200 * 256)

        def read(address, size):
            if address == 0x10000:
                return bytes(header)
            assert address == 0x20000
            assert size == 16
            return stats

        result = discover_stat_arrays(read, 0x10000)
        assert [x['header_offset'] for x in result] == [0x80]
        assert result[0]['stats'][1]['raw'] == 200 * 256

    def test_observed_build_full_stats_uses_e8_not_old_a8(self):
        from .units import describe_player

        header = bytearray(0x200)
        struct.pack_into('<QQ', header, 0xE8, 0x20000, 2)
        stats = struct.pack('<HHiHHi', 0, 6, 435200, 0, 7, 435333)

        def read(address, size):
            if 0x10000 <= address < 0x10200:
                return bytes(header[address - 0x10000 : address - 0x10000 + size])
            if address == 0x20000:
                return stats[:size]
            if address == 0x30000:
                return b'player\0'.ljust(size, b'\0')
            raise AssertionError(hex(address))

        player = {'data_pointer': 0x30000, 'inventory_pointer': 0, 'stats_pointer': 0x10000}
        result = describe_player(read, player)
        assert result['full_stats_hp_candidate']['current'] == 1700
        assert int(result['full_stats_hp_candidate']['max']) == 1700
