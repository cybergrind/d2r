import struct

import pytest

from inventory_tracking.input.keybindings import RECORD
from inventory_tracking.macros.skills import (
    CONSUME,
    HEX_PURGE,
    PSYCHIC_WARD,
    SUMMON_DEFILER,
    SWAP_WEAPONS,
    skill_keys,
)
from inventory_tracking.macros.world import (
    decode_slots,
    doors,
    local_player,
    missiles,
    monsters,
    next_name,
    unit_census,
    unit_stats,
)
from inventory_tracking.native.layout import LEVEL_AREA_ID, PATH_ROOM1, ROOM1_ROOM2, ROOM2_LEVEL
from tests.inventory_tracking.macros.fakes import SLOTS


def table(slots):
    return b''.join(struct.pack('<7I', 0xFFFFFFFF if s is None else s, 0xFFFFFFFF, 0, 4, 255, 0, 0) for s in slots)


def bindings(actions):
    return b'\x25\x00' + b''.join(RECORD.pack(action, code, 1) for action, code in actions.items())


def test_slots_decode_as_recorded_for_the_character():
    assert decode_slots(table(SLOTS)) == SLOTS


def test_a_table_of_something_else_is_rejected():
    with pytest.raises(ValueError, match='skill ids'):
        decode_slots(table((70000, *SLOTS[1:])))
    with pytest.raises(ValueError, match='Short'):
        decode_slots(b'\0' * 10)


def test_keys_come_from_the_slot_and_the_key_file():
    # The character's file, 2026-10-06: g action 18, q action 21, r action 48, 6 action 50.
    data = bindings({18: 0x47, 21: 0x51, 48: 0x52, 50: 0x36})
    assert skill_keys(SLOTS, data, (SUMMON_DEFILER, CONSUME, HEX_PURGE, PSYCHIC_WARD)) == {
        SUMMON_DEFILER: 'q',
        CONSUME: '6',
        HEX_PURGE: 'g',
        PSYCHIC_WARD: 'r',
    }


def test_a_skill_off_the_bar_or_on_a_modifier_combination_is_named():
    with pytest.raises(ValueError, match='Consume is not on a skill key'):
        skill_keys(tuple(s for s in SLOTS if s != CONSUME), bindings({}), (CONSUME,))
    with pytest.raises(ValueError, match='Summon Defiler has no key'):
        skill_keys(SLOTS, bindings({21: 0x1009}), (SUMMON_DEFILER,))


def test_a_skill_on_a_mouse_button_is_pressed_as_that_button():
    assert skill_keys(SLOTS, bindings({21: 0x102}), (SUMMON_DEFILER,)) == {SUMMON_DEFILER: 'Button9'}


@pytest.mark.parametrize(('name', 'following'), [('cyber32', 'cyber33'), ('cyber99', 'cyber100'), ('7', '8')])
def test_next_game_name(name, following):
    assert next_name(name) == following


@pytest.mark.parametrize('name', ['pindle', 'Cyber32', 'cyber-3', ''])
def test_names_the_macro_cannot_continue(name):
    with pytest.raises(ValueError, match='number'):
        next_name(name)


def test_the_swap_key_is_read_from_the_key_file_not_assumed():
    # CybergrindAA, 2026-10-06: `c` on action 44; W, the game's default, is on another action there.
    assert skill_keys(SLOTS, bindings({44: 0x43, 46: 0x57}), (SWAP_WEAPONS,)) == {SWAP_WEAPONS: 'c'}
    with pytest.raises(ValueError, match='Swap Weapons has no key'):
        skill_keys(SLOTS, bindings({46: 0x57}), (SWAP_WEAPONS,))


TABLE = 0x100000
LEVEL, ROOM2, ROOM1 = 0x500000, 0x510000, 0x520000


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


def character(memory, index, name, *, life=None, area=109):
    """A player unit in bucket 1; `life` = (life, most life) in whole points, None for none readable."""
    unit_id = 128 * index + 1
    address, data, path, stats = (base + index * 0x400 for base in (0x200000, 0x300000, 0x400000, 0x600000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 0, 7, unit_id, 1)
    struct.pack_into('<QQQ', header, 0x10, data, 0, 0)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stats)
    memory.block(data, 16)[: len(name)] = name.encode()
    struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0, 5000 + index, 0, 5000)
    struct.pack_into('<Q', memory.blocks[path], PATH_ROOM1, ROOM1)
    struct.pack_into('<Q', memory.block(ROOM1, 0x50), ROOM1_ROOM2, ROOM2)
    struct.pack_into('<Q', memory.block(ROOM2, 0xA0), ROOM2_LEVEL, LEVEL)
    struct.pack_into('<I', memory.block(LEVEL, 0x400), LEVEL_AREA_ID, area)
    full = [(0, 150), (12, 91)] if life is None else [(6, life[0] << 8), (7, life[1] << 8), (12, 91)]
    block = memory.block(stats, 0x100)
    struct.pack_into('<QQ', block, 0xE8, stats + 0x200, len(full))
    raw = memory.block(stats + 0x200, 0x100)
    for slot, (stat_id, value) in enumerate(full):
        struct.pack_into('<HHi', raw, slot * 8, 0, stat_id, value)
    return address


def chain(memory, units):
    heads = memory.block(TABLE, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 1 * 8, previous)


def test_the_character_is_found_beside_its_stash_tabs():
    # Shared stash tabs are player units named like the character with no life (collection/research.md R1).
    memory = Memory()
    chain(memory, [character(memory, 0, 'CybergrindAA', life=(900, 1200)), character(memory, 1, 'CybergrindAA')])
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert (player.unit_id, player.name, player.area) == (1, 'CybergrindAA', 109)


def test_the_character_is_found_in_a_game_with_other_players():
    # 2026-10-08: with other players in the game the macro said "not in a game". Another player's
    # unit has a name of its own and no readable life (collection/research.md R3, `Caras`).
    memory = Memory()
    chain(
        memory,
        [
            character(memory, 0, 'Caras'),
            character(memory, 1, 'CybergrindAA', life=(900, 1200)),
            character(memory, 2, 'CybergrindAA'),
        ],
    )
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert (player.unit_id, player.name) == (129, 'CybergrindAA')


def test_no_character_when_none_or_several_have_life():
    memory = Memory()
    chain(memory, [character(memory, 0, 'Caras'), character(memory, 1, 'CybergrindAA')])
    assert local_player(memory.read, TABLE) is None
    memory = Memory()
    chain(memory, [character(memory, 0, 'Caras', life=(1, 1)), character(memory, 1, 'CybergrindAA', life=(2, 2))])
    assert local_player(memory.read, TABLE) is None


def monster(memory, index, txt_id, *, flags=0, alignment=0, owner=0xFFFFFFFF, mode=1):
    """A monster unit in bucket 2 with its type flags, owner and alignment stat."""
    unit_id = 128 * index + 2
    address, data, path, stats = (base + index * 0x400 for base in (0x700000, 0x800000, 0x900000, 0xA00000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 1, txt_id, unit_id, mode)
    struct.pack_into('<Q', header, 0x10, data)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stats)
    block = memory.block(data, 0x80)
    block[0x1A] = flags
    struct.pack_into('<I', block, 84, owner)
    struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0, 5010 + index, 0, 5020)
    full = [(172, alignment)] if alignment else [(12, 85)]
    block = memory.block(stats, 0x100)
    struct.pack_into('<QQ', block, 0xE8, stats + 0x200, len(full))
    raw = memory.block(stats + 0x200, 0x100)
    for slot, (stat_id, value) in enumerate(full):
        struct.pack_into('<HHi', raw, slot * 8, 0, stat_id, value)
    return address


def test_monsters_carry_their_type_flags_and_whether_they_are_allies():
    memory = Memory()
    units = [
        monster(memory, 0, 19, flags=0x0C),  # a champion
        monster(memory, 1, 19, flags=0x10),  # a minion
        monster(memory, 2, 744, alignment=2),  # the character's own Defiler
        monster(memory, 3, 338, owner=1),  # the mercenary, owned
        monster(memory, 4, 19, mode=12),  # a corpse
    ]
    heads = memory.block(TABLE + 1024, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 2 * 8, previous)

    found = monsters(memory.read, TABLE)

    assert [(m.unit_id, m.flags, m.ally, m.owner, m.leader) for m in found] == [
        (2, 0x0C, False, 0xFFFFFFFF, True),
        (130, 0x10, False, 0xFFFFFFFF, False),
        (258, 0, True, 0xFFFFFFFF, False),
        (386, 0, False, 1, False),
    ]
    assert (found[0].x, found[0].y) == (5010.0, 5020.0)


def test_dead_monsters_are_read_on_request_with_their_stat_list_address():
    memory = Memory()
    units = [monster(memory, 0, 19), monster(memory, 4, 19, mode=12)]
    heads = memory.block(TABLE + 1024, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 2 * 8, previous)

    assert [m.unit_id for m in monsters(memory.read, TABLE)] == [2]
    found = monsters(memory.read, TABLE, dead=True)
    assert [(m.unit_id, m.mode) for m in found] == [(2, 1), (514, 12)]
    assert unit_stats(memory.read, found[0].stats_at) == {12: 85}
    assert unit_stats(memory.read, 0x1) == {}


def missile(memory, address, path, unit_id, slot):
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 3, 750, unit_id, 0)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<HH', header, 0xC4, 5012, 5030)
    memory.block(path, 0x30)[:4] = b'\x01\x02\x03\x04'
    struct.pack_into('<Q', memory.block(TABLE + slot * 1024, 1024), (unit_id % 128) * 8, address)


def test_missiles_are_dumped_raw_from_the_client_and_the_server_slots():
    memory = Memory()
    missile(memory, 0xB00000, 0xB10000, 3 + 128 * 2, 3)  # another unit's bolt
    missile(memory, 0xB20000, 0xB30000, 5, 9)  # the player's own blade: the server missile slot

    found = missiles(memory.read, TABLE)
    assert [(x['unit_id'], x['txt_id'], x['slot'], x['xy']) for x in found] == [
        (259, 750, 3, [5012, 5030]),
        (5, 750, 9, [5012, 5030]),
    ]
    assert found[0]['path'].startswith('01020304')
    assert len(found[0]['path']) == 0x60
    assert len(found[0]['record']) == 0x2C0


def test_the_unit_census_says_what_hangs_off_each_slot():
    memory = Memory()
    for slot in range(12):
        memory.block(TABLE + slot * 1024, 1024)
    missile(memory, 0xB20000, 0xB30000, 5, 9)
    census = unit_census(memory.read, TABLE)
    assert census[9] == {'slot': 9, 'heads': 1, 'first': [3, 750, 5, 0], 'units': 1}
    assert census[3] == {'slot': 3, 'heads': 0}
    assert len(census) == 12


def test_door_objects_are_read_with_their_mode_and_static_position():
    memory = Memory()
    heads = memory.block(TABLE + 2 * 1024, 1024)
    units = []
    for index, (txt, mode) in enumerate(((15, 0), (16, 2), (139, 0))):  # a closed wooden door, an opened one, a chest
        unit_id = 128 * index + 5  # all in bucket 5, chained
        address, path = 0xC00000 + index * 0x400, 0xC10000 + index * 0x400
        header = memory.block(address, 0x160)
        struct.pack_into('<IIII', header, 0, 2, txt, unit_id, mode)
        struct.pack_into('<Q', header, 0x38, path)
        block = memory.block(path, 0x18)
        struct.pack_into('<II', block, 0x10, 7800 + index, 5600)
        units.append(address)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 5 * 8, previous)

    found = doors(memory.read, TABLE)
    assert [(d.txt_id, d.mode, d.x, d.y, d.closed) for d in found] == [
        (15, 0, 7800.0, 5600.0, True),
        (16, 2, 7801.0, 5600.0, False),
    ]
    assert found[0].radius == 2.5  # 1 x 3 sub-tiles: half of 3, plus the slack
