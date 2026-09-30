"""Level survey: find Room2 lists by back-pointer, tell loaded rooms from level-only rooms."""

import struct

import pytest

from inventory_tracking.levels.research import survey


TABLE, PLAYER, OBJECT, PATH, OBJECT_PATH = 0x100000, 0x200000, 0x200400, 0x210000, 0x210100
ACT, MISC = 0x220000, 0x230000
LEVEL, NEXT_LEVEL = 0x400000, 0x401000
ROOM1_A, ROOM1_B, NEAR = 0x300000, 0x300200, 0x300400
ROOM2_A, ROOM2_B, ROOM2_C, PRESET = 0x310000, 0x310200, 0x310400, 0x320000


class Memory:
    def __init__(self):
        self.blocks = {}

    def block(self, address, size):
        self.blocks[address] = bytearray(size)
        return self.blocks[address]

    def read(self, address, size):
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return bytes(data[address - start : address - start + size])
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')


def unit(memory, address, unit_type, txt_id, unit_id, path):
    data = memory.block(address, 0x160)
    struct.pack_into('<IIII', data, 0, unit_type, txt_id, unit_id, 0)
    struct.pack_into('<Q', data, 0x20, ACT)
    struct.pack_into('<Q', data, 0x38, path)


@pytest.fixture
def memory():
    memory = Memory()
    table = memory.block(TABLE, 6 * 1024)
    struct.pack_into('<Q', table, 0 * 1024 + 1 * 8, PLAYER)
    struct.pack_into('<Q', table, 2 * 1024 + 2 * 8, OBJECT)
    unit(memory, PLAYER, 0, 7, 1, PATH)
    unit(memory, OBJECT, 2, 357, 2, OBJECT_PATH)
    path = memory.block(PATH, 0x28)
    struct.pack_into('<HxxH', path, 0x02, 5000, 6000)
    struct.pack_into('<Q', path, 0x20, ROOM1_A)
    path = memory.block(OBJECT_PATH, 0x28)
    struct.pack_into('<I', path, 0x10, 5100)
    struct.pack_into('<I', path, 0x14, 6100)

    # Two streamed Room1s, near each other, for the first two of three Room2s.
    for room1, room2 in ((ROOM1_A, ROOM2_A), (ROOM1_B, ROOM2_B)):
        data = memory.block(room1, 0x100)
        struct.pack_into('<Q', data, 0x18, room2)
    struct.pack_into('<Q', memory.blocks[ROOM1_A], 0x00, NEAR)
    struct.pack_into('<I', memory.blocks[ROOM1_A], 0x40, 1)
    struct.pack_into('<Q', memory.block(NEAR, 8), 0, ROOM1_B)
    for room2, following in ((ROOM2_A, ROOM2_B), (ROOM2_B, ROOM2_C), (ROOM2_C, 0)):
        data = memory.block(room2, 0x100)
        struct.pack_into('<Q', data, 0x08, following)
        struct.pack_into('<Q', data, 0x90, LEVEL)
    # A legacy-shaped preset (type 2, object 357) reachable only from the unloaded Room2.
    struct.pack_into('<Q', memory.blocks[ROOM2_C], 0x40, PRESET)
    struct.pack_into('<II', memory.block(PRESET, 0x80), 0, 2, 357)

    level = memory.block(LEVEL, 0x400)
    struct.pack_into('<Q', level, 0x10, ROOM2_A)
    struct.pack_into('<Q', level, 0x20, NEXT_LEVEL)
    struct.pack_into('<I', level, 0x1F8, 74)
    struct.pack_into('<I', memory.block(NEXT_LEVEL, 0x400), 0x1F8, 75)

    act = memory.block(ACT, 0x80)
    struct.pack_into('<I', act, 0x28, 1)
    struct.pack_into('<Q', act, 0x78, MISC)
    misc = memory.block(MISC, 0x878)
    struct.pack_into('<I', misc, 0x830, 2)
    struct.pack_into('<Q', misc, 0x840, 0x1234)
    struct.pack_into('<Q', misc, 0x860, ACT)
    struct.pack_into('<I', misc, 0x868, 0x5678)
    struct.pack_into('<Q', misc, 0x870, LEVEL)
    return memory


def test_survey_separates_level_room2s_from_streamed_room1s(memory):
    result = survey(memory.read, TABLE)

    summary = result['summary']
    assert summary['level_no'] == 74
    assert summary['player'] == {'x': 5000, 'y': 6000}
    assert summary['difficulty'] == 2
    assert (summary['loaded_room1s'], summary['room2s_in_level'], summary['room2s_with_room1']) == (2, 3, 2)
    assert (summary['levels_in_act_chain'], summary['levels_with_room2s']) == (2, 1)
    assert summary['journal_unit_seen']
    assert not summary['summoner_unit_seen']
    assert result['level']['room2_list_candidates'][0] == {'level_offset': 0x10, 'next_offset': 0x08, 'count': 3}
    assert result['act']['misc_act_matches']
    assert result['act']['end_seed_hash'] == 0x5678
    assert (result['markers']['journal_units'][0]['x'], result['markers']['journal_units'][0]['y']) == (5100, 6100)


def test_marker_hit_reports_the_room_without_a_loaded_room1(memory):
    hits = survey(memory.read, TABLE)['markers']['typed_room2_hits']

    assert hits == [
        {'room2_index': 2, 'has_loaded_room1': False, 'marker': 'journal_object', 'address': PRESET + 4, 'typed': True}
    ]


def test_survey_requires_a_player_in_a_room(memory):
    struct.pack_into('<Q', memory.blocks[PLAYER], 0x38, 0)

    with pytest.raises(ValueError, match='No player unit with a room'):
        survey(memory.read, TABLE)


OBJECT_DATA, SHRINE_TXT, OBJECT_TXT = 0x240000, 0x250000, 0x260000


def test_objects_carry_their_data_block_and_a_candidate_shrine_decode(memory):
    # Confirmed 2026-09-30 (Stamina Shrine dump): +0x08 shrine type byte, +0x10 shrine txt pointer.
    struct.pack_into('<Q', memory.blocks[OBJECT], 0x10, OBJECT_DATA)
    data = memory.block(OBJECT_DATA, 0x40)
    struct.pack_into('<Q', data, 0x00, OBJECT_TXT)
    data[0x08] = 18
    struct.pack_into('<Q', data, 0x10, SHRINE_TXT)

    result = survey(memory.read, TABLE)

    [obj] = result['units']['objects']
    assert obj['data_hex'] == bytes(data).hex()
    assert obj['shrine_candidate'] == {'type': 18, 'name': 'Gem Shrine', 'table': SHRINE_TXT}
    assert result['summary']['shrine_candidates'] == [
        {'txt_id': 357, 'x': 5100, 'y': 6100, 'type': 18, 'name': 'Gem Shrine'}
    ]


def test_objects_without_a_shrine_table_are_not_shrine_candidates(memory):
    struct.pack_into('<Q', memory.blocks[OBJECT], 0x10, OBJECT_DATA)
    memory.block(OBJECT_DATA, 0x40)

    result = survey(memory.read, TABLE)

    assert result['units']['objects'][0]['shrine_candidate'] is None
    assert result['summary']['shrine_candidates'] == []


ITEM, ITEM_PATH = 0x200800, 0x210200


def test_ground_items_are_recorded_for_checking_positions(memory):
    table = memory.blocks[TABLE]
    struct.pack_into('<Q', table, 4 * 1024 + 3 * 8, ITEM)
    item = memory.block(ITEM, 0x160)
    struct.pack_into('<IIII', item, 0, 4, 654, 3, 3)  # Ber, unit 3, mode 3 (on the ground)
    struct.pack_into('<Q', item, 0x38, ITEM_PATH)
    path = memory.block(ITEM_PATH, 0x28)
    struct.pack_into('<I', path, 0x10, 5120)
    struct.pack_into('<I', path, 0x14, 6120)

    result = survey(memory.read, TABLE)

    assert result['summary']['ground_items'] == [{'txt_id': 654, 'mode': 3, 'x': 5120, 'y': 6120, 'rune': 'Ber Rune'}]


def test_real_stamina_shrine_block_decodes():
    # Win+C dump 20260930T121835Z-713d7e8a (Black Marsh): object class 83 next to the player; the
    # user identified it in game as a Stamina Shrine (d2data shrines.json code 14).
    from inventory_tracking.levels.research import shrine_candidate

    block = bytes.fromhex('48e30465000000000e0000000000000078909e2c00000000') + bytes(0x28)

    assert shrine_candidate(block) == {'type': 14, 'name': 'Stamina Shrine', 'table': 0x2C9E9078}


def test_collision_grid_candidate_is_found_by_the_room_bounds_in_subtiles():
    # Room1 -> struct holding the room's sub-tile bounds (tiles x 5) and a pointer to a
    # width x height u16 mask: the shape D2MOO's ActiveRoom collision grid has.
    from inventory_tracking.levels.research import Probe, collision_candidates

    memory = Memory()
    room1, room2, grid, mask = 0x500000, 0x510000, 0x520000, 0x530000
    struct.pack_into('<Q', memory.block(room1, 0x100), 0x60, grid)
    struct.pack_into('<IIII', memory.block(room2, 0x100), 0x60, 100, 200, 2, 1)  # tiles
    g = memory.block(grid, 0x80)
    struct.pack_into('<IIII', g, 0x08, 500, 1000, 10, 5)  # sub-tiles
    struct.pack_into('<Q', g, 0x20, mask)
    cells = memory.block(mask, 10 * 5 * 2)
    struct.pack_into('<H', cells, 0, 1)  # one blocked cell

    [found] = collision_candidates(Probe(memory.read), room1, room2)

    assert (found['room1_offset'], found['coords_offset'], found['mask_offset']) == (0x60, 0x08, 0x20)
    assert found['size'] == [10, 5]
    assert found['values'] == {'0': 49, '1': 1}
    assert bytes.fromhex(found['mask_hex'])[:2] == b'\x01\x00'


def test_no_candidate_without_matching_bounds():
    from inventory_tracking.levels.research import Probe, collision_candidates

    memory = Memory()
    room1, room2 = 0x500000, 0x510000
    memory.block(room1, 0x100)
    struct.pack_into('<IIII', memory.block(room2, 0x100), 0x60, 100, 200, 2, 1)

    assert collision_candidates(Probe(memory.read), room1, room2) == []


def test_a_pointer_to_arbitrary_data_is_not_a_mask():
    from inventory_tracking.levels.research import Probe, collision_candidates

    memory = Memory()
    room1, room2, grid, noise = 0x500000, 0x510000, 0x520000, 0x530000
    struct.pack_into('<Q', memory.block(room1, 0x100), 0x60, grid)
    struct.pack_into('<IIII', memory.block(room2, 0x100), 0x60, 100, 200, 2, 1)
    g = memory.block(grid, 0x80)
    struct.pack_into('<IIII', g, 0x08, 500, 1000, 10, 5)
    struct.pack_into('<Q', g, 0x20, noise)
    data = memory.block(noise, 100)
    struct.pack_into('<50H', data, 0, *range(50))  # 50 distinct values: not a flag mask

    assert collision_candidates(Probe(memory.read), room1, room2) == []
