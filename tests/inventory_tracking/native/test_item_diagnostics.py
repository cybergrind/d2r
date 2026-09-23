import struct

from inventory_tracking.native.item_diagnostics import capture_stat_candidates


def memory_fixture():
    memory = bytearray(0x50000)
    struct.pack_into('<Q', memory, 0x10090, 0x20000)
    struct.pack_into('<I', memory, 0x2001C, 0x40)
    struct.pack_into('<QQ', memory, 0x20030, 0x30000, 2)
    struct.pack_into('<HHiHHi', memory, 0x30000, 0, 17, 80, 0, 18, 80)
    return memory


def test_modifier_candidates_are_research_only_and_retain_source_addresses():
    memory = memory_fixture()
    result = capture_stat_candidates(lambda a, n: bytes(memory[a : a + n]), 0x10000)
    assert result['validated'] is False
    chain = next(c for c in result['chains'] if c['head_offset'] == 0x90)
    assert chain['complete']
    assert chain['lists'][0]['address'] == 0x20000
    assert [s['raw'] for s in chain['lists'][0]['stats']] == [80, 80]


def test_cycle_is_bounded_and_not_called_complete():
    memory = memory_fixture()
    struct.pack_into('<Q', memory, 0x20048, 0x20000)
    result = capture_stat_candidates(lambda a, n: bytes(memory[a : a + n]), 0x10000)
    chain = next(c for c in result['chains'] if c['head_offset'] == 0x90)
    assert not chain['complete']
    assert len(chain['lists']) == 1


def test_changing_candidate_stats_are_not_accepted():
    memory = memory_fixture()
    calls = 0

    def read(address, size):
        nonlocal calls
        if address == 0x30000:
            calls += 1
            struct.pack_into('<i', memory, 0x30004, 80 + calls)
        return bytes(memory[address : address + size])

    result = capture_stat_candidates(read, 0x10000)
    chain = next(c for c in result['chains'] if c['head_offset'] == 0x90)
    assert not chain['complete']
    assert 'changed' in chain['reason']
    assert not chain['lists']


def test_insight_additional_pointer_is_captured_as_research_only():
    memory = memory_fixture()
    struct.pack_into('<Q', memory, 0x10118, 0x20000)
    result = capture_stat_candidates(lambda a, n: bytes(memory[a : a + n]), 0x10000)
    chain = next(c for c in result['chains'] if c['head_offset'] == 0x118)
    assert chain['complete']
    assert chain['lists'][0]['stats'][0]['raw'] == 80
    assert result['validated'] is False
