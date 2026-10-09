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
from inventory_tracking.macros.world import decode_slots, local_player, next_name
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


def test_a_skill_off_the_bar_or_on_a_mouse_button_is_named():
    with pytest.raises(ValueError, match='Consume is not on a skill key'):
        skill_keys(tuple(s for s in SLOTS if s != CONSUME), bindings({}), (CONSUME,))
    with pytest.raises(ValueError, match='Summon Defiler has no key'):
        skill_keys(SLOTS, bindings({21: 0x102}), (SUMMON_DEFILER,))


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
