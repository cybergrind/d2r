"""Monster units from the streamed unit table: position, level, and data/stats on first sight only."""

import struct

import pytest

from inventory_tracking.game.decode import monsters, monsters_and_dead
from inventory_tracking.game.layout import ALIGNMENT_STAT, HERALD_TIER_STAT, MONSTER_OWNER
from inventory_tracking.game.records import Monster
from inventory_tracking.native.layout import TERROR_SERVICE_RVA
from inventory_tracking.terror.monsters import (
    level_entry,
    loaded_rooms,
    monster_units,
    player_level,
    player_life,
    player_states,
    terror_entries,
    terror_levels,
)
from inventory_tracking.terror.tracker import leading, modifiers, stat
from tests.inventory_tracking.fake_memory import Memory


TABLE = 0x100000
MONSTERS = TABLE + 1 * 1024
LEVEL, ROOM2, ROOM1 = 0x500000, 0x510000, 0x520000
BOUNDS = (100, 200, 8, 8)


def level_rooms(memory, area=108):
    struct.pack_into('<I', memory.block(LEVEL, 0x400), 0x1F8, area)
    struct.pack_into('<Q', memory.block(ROOM2, 0xA0), 0x90, LEVEL)
    struct.pack_into('<IIII', memory.blocks[ROOM2], 0x60, *BOUNDS)
    struct.pack_into('<Q', memory.block(ROOM1, 0x50), 0x18, ROOM2)


def stat_list(memory, header, array, stats):
    struct.pack_into('<QQ', header, 0, array, len(stats))
    raw = memory.block(array, 0x100)
    for slot, (stat_id, value) in enumerate(stats):
        struct.pack_into('<HHi', raw, slot * 8, 0, stat_id, value)


def monster(memory, index, txt_id, mode, x, y, *, stats=(), base=()):
    unit_id = 128 * index + 3  # bucket 3
    address, path, data, stat_block = (base + index * 0x400 for base in (0x200000, 0x300000, 0x400000, 0x600000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 1, txt_id, unit_id, mode)
    struct.pack_into('<Q', header, 0x10, data)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stat_block)
    struct.pack_into('<HxxH', memory.block(path, 0x28), 0x02, x, y)
    struct.pack_into('<Q', memory.blocks[path], 0x20, ROOM1)
    memory.block(data, 0x80)[0:4] = b'\xaa\xbb\xcc\xdd'
    block = memory.block(stat_block, 0x100)
    full, base_header = bytearray(16), bytearray(16)
    stat_list(memory, full, stat_block + 0x200, stats)
    stat_list(memory, base_header, stat_block + 0x300, base)
    block[0xE8:0xF8], block[0x30:0x40] = full, base_header
    return address, unit_id


def chain(memory, units):
    heads = memory.block(MONSTERS, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 3 * 8, previous)


def test_monsters_carry_position_area_and_first_sight_details():
    memory = Memory()
    level_rooms(memory)
    first, first_id = monster(memory, 0, 156, 1, 5100, 5200, stats=[(6, 1000), (7, 2000)], base=[(12, 95)])
    second, second_id = monster(memory, 1, 156, 12, 5110, 5210)
    chain(memory, [first, second])

    found, complete = monster_units(memory.read, TABLE, known={second_id})

    assert complete

    assert found[0] == Monster(
        first_id,
        156,
        1,
        5100,
        5200,
        area=108,
        room=BOUNDS,
        data_hex='aabbccdd' + '00' * 0x7C,
        stats=((0, 6, 1000), (0, 7, 2000)),
        base_stats=((0, 12, 95),),
    )
    # already known: no data, no stats
    assert found[1] == Monster(second_id, 156, 12, 5110, 5210, area=108, room=BOUNDS)
    assert [m.path_at for m in found] == [0x300000, 0x300400]  # the dynamic path: where the HUD reads it live


def test_loaded_rooms_follow_room1_neighbours_within_the_level():
    memory = Memory()
    level_rooms(memory)
    other_room2, other_room1, foreign_room1, foreign_room2 = 0x530000, 0x540000, 0x550000, 0x560000
    struct.pack_into('<Q', memory.block(other_room2, 0xA0), 0x90, LEVEL)
    struct.pack_into('<IIII', memory.blocks[other_room2], 0x60, 108, 200, 8, 8)
    struct.pack_into('<Q', memory.block(other_room1, 0x50), 0x18, other_room2)
    struct.pack_into('<Q', memory.block(foreign_room2, 0xA0), 0x90, 0x570000)  # another level
    struct.pack_into('<Q', memory.block(foreign_room1, 0x50), 0x18, foreign_room2)
    near = 0x580000
    struct.pack_into('<3Q', memory.block(near, 24), 0, ROOM1, other_room1, foreign_room1)
    struct.pack_into('<Q', memory.blocks[ROOM1], 0x00, near)
    struct.pack_into('<I', memory.blocks[ROOM1], 0x40, 3)

    assert loaded_rooms(memory.read, ROOM1, LEVEL) == frozenset({BOUNDS, (108, 200, 8, 8)})


def test_level_entry_counts_room2s_and_keeps_the_level_bytes_for_research():
    memory = Memory()
    level_rooms(memory)
    second = 0x530000
    struct.pack_into('<Q', memory.blocks[LEVEL], 0x10, ROOM2)
    struct.pack_into('<Q', memory.blocks[ROOM2], 0x48, second)
    memory.block(second, 0xA0)
    memory.blocks[LEVEL][0x300] = 0x7F

    count, level_hex = level_entry(memory.read, LEVEL)

    assert count == 2
    assert len(level_hex) == 0x800
    assert level_hex[0x600:0x602] == '7f'


def test_the_player_level_is_stat_12_of_the_player_unit():
    memory = Memory()
    address, stat_block = 0x700000, 0x710000
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 0, 7, 1, 1)
    struct.pack_into('<Q', header, 0x88, stat_block)
    block = memory.block(stat_block, 0x100)
    base = bytearray(16)
    stat_list(memory, base, stat_block + 0x300, [(0, 150), (12, 93)])
    block[0x30:0x40] = base
    struct.pack_into('<Q', memory.block(TABLE, 1024), 1 * 8, address)  # players: unit id 1 -> bucket 1

    assert player_level(memory.read, TABLE) == 93

    struct.pack_into('<Q', memory.blocks[TABLE], 1 * 8, 0)
    assert player_level(memory.read, TABLE) is None


def test_the_player_life_is_stats_6_and_7_of_the_full_list_in_whole_points():
    memory = Memory()
    address, stat_block = 0x700000, 0x710000
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 0, 7, 1, 1)
    struct.pack_into('<Q', header, 0x88, stat_block)
    full = bytearray(16)
    stat_list(memory, full, stat_block + 0x200, [(6, 812 << 8), (7, 1450 << 8)])
    memory.block(stat_block, 0x100)[0xE8:0xF8] = full
    struct.pack_into('<Q', memory.block(TABLE, 1024), 1 * 8, address)

    assert player_life(memory.read, TABLE) == (812, 1450)

    struct.pack_into('<Q', memory.blocks[TABLE], 1 * 8, 0)
    assert player_life(memory.read, TABLE) is None


def test_the_player_states_are_the_bits_set_beside_its_stats():
    # State 208 (Consume) is bit 0x10000 at stats +0xB48 (tracking/consume.py): 32 states a word from +0xB30.
    memory = Memory()
    address, stat_block = 0x700000, 0x710000
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 0, 7, 1, 1)
    struct.pack_into('<Q', header, 0x88, stat_block)
    full = bytearray(16)
    stat_list(memory, full, stat_block + 0x2000, [(6, 812 << 8), (7, 1450 << 8)])
    block = memory.block(stat_block, 0xC00)
    block[0xE8:0xF8] = full
    struct.pack_into('<I', block, 0xB30, 1 << 9)  # Amplify Damage
    struct.pack_into('<I', block, 0xB34, 1 << (60 - 32))  # Decrepify
    struct.pack_into('<I', block, 0xB48, 0x10000)
    struct.pack_into('<Q', memory.block(TABLE, 1024), 1 * 8, address)

    assert player_states(memory.read, TABLE) == frozenset((9, 60, 208))

    struct.pack_into('<Q', memory.blocks[TABLE], 1 * 8, 0)
    assert player_states(memory.read, TABLE) is None


def terror_service(memory, levels, base=0x140000000):
    service, entries = 0x800000, 0x810000
    struct.pack_into('<Q', memory.block(base + TERROR_SERVICE_RVA, 8), 0, service)
    struct.pack_into('<QQ', memory.block(service, 0x100), 0x80, entries, len(levels))
    block = memory.block(entries, 16 * max(len(levels), 1))
    for index, level in enumerate(levels):
        struct.pack_into('<I', block, 16 * index, level)
    return base


def test_the_terrorized_levels_are_the_clients_own_list():
    # Glacial Trail and Drifter Cavern, as the service read them on 2026-10-12 (the client's Terror Zone
    # service: 16-byte entries, the level id first).
    memory = Memory()
    assert terror_levels(memory.read, terror_service(memory, [115, 116])) == (115, 116)


def test_the_clients_tz_entries_include_level_and_effect_before_monsters_are_seen():
    # The automap reads 16-byte entries: area at +0, displayed TZ level at +8,
    # a packed modifier field at +12. These bytes are in the service, not monster units.
    memory = Memory()
    base = terror_service(memory, [115, 116])
    struct.pack_into('<I', memory.blocks[0x810000], 8, 95)
    struct.pack_into('<I', memory.blocks[0x810000], 12, 274)  # low byte 18: Cold Enchanted
    struct.pack_into('<I', memory.blocks[0x810000], 24, 95)
    struct.pack_into('<I', memory.blocks[0x810000], 28, 274)

    found = terror_entries(memory.read, base)
    assert found is not None
    assert [(entry.area, entry.level, entry.modifier, entry.modifier_word) for entry in found] == [
        (115, 95, 18, 274),
        (116, 95, 18, 274),
    ]


def test_no_terrorized_levels_is_an_empty_list_and_no_service_is_unread():
    memory = Memory()
    assert terror_levels(memory.read, terror_service(memory, [])) == ()
    bare = Memory()
    bare.block(0x140000000 + TERROR_SERVICE_RVA, 8)
    assert terror_levels(bare.read, 0x140000000) is None


def test_entries_that_are_no_level_ids_are_refused_with_their_bytes():
    memory = Memory()
    base = terror_service(memory, [115, 70000])
    with pytest.raises(ValueError, match='73000000'):
        terror_levels(memory.read, base)


def parity_unit(memory, index, txt_id, mode, at, *, flags=0, owner=0xFFFFFFFF, mods=(), stats=(), data=True):
    """A monster as both walks read it (bucket 3): the path's position with its fractions and its Room1, the
    monster data with its type flags, owner and modifiers, and the full stat list."""
    unit_id = 128 * index + 3
    address, path, block, stat_block = (base + index * 0x400 for base in (0x200000, 0x300000, 0x400000, 0x600000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 1, txt_id, unit_id, mode)
    struct.pack_into('<Q', header, 0x10, block if data else 0)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stat_block)
    struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0x8000, at[0], 0x4000, at[1])
    struct.pack_into('<Q', memory.blocks[path], 0x20, ROOM1)
    raw = memory.block(block, 0x80)
    raw[0x1A] = flags
    raw[0x20 : 0x20 + len(mods)] = bytes(mods)
    struct.pack_into('<I', raw, MONSTER_OWNER, owner)
    full = bytearray(16)
    stat_list(memory, full, stat_block + 0x200, stats)
    memory.block(stat_block, 0x100)[0xE8:0xF8] = full
    return address, unit_id


def test_the_terror_walk_and_the_look_read_the_units_they_share_alike():
    """Parity of the two views of one walk (game/decode.py `monster_table`): every field both read agrees, and
    the terror view keeps the dead and the units without monster data, which the look leaves out."""
    memory = Memory()
    level_rooms(memory)
    units = [
        parity_unit(memory, 0, 19, 1, (5100, 5200), flags=0x0C, mods=(17, 5), stats=[(6, 256 * 400), (7, 256 * 500)]),
        parity_unit(memory, 1, 19, 1, (5110, 5210), flags=0x10, mods=(17,), stats=[(HERALD_TIER_STAT, 3)]),
        parity_unit(memory, 2, 744, 1, (5120, 5220), stats=[(ALIGNMENT_STAT, 2)]),  # the character's Defiler
        parity_unit(memory, 3, 338, 1, (5130, 5230), owner=1),  # the mercenary
        parity_unit(memory, 4, 19, 12, (5140, 5240), flags=0x08),  # a unique lying dead
        parity_unit(memory, 5, 19, 1, (5150, 5250), data=False),  # no monster data: the look skips it
    ]
    chain(memory, [address for address, _ in units])
    addresses = {unit_id: address for address, unit_id in units}

    terror, complete = monster_units(memory.read, TABLE, known=set())
    look, dead = monsters_and_dead(memory.read, TABLE, dead=True)

    assert complete
    by_id = {monster.unit_id: monster for monster in terror}
    assert list(by_id) == list(addresses)
    assert [m.unit_id for m in look] == list(addresses)[:5]
    assert dead == {units[4][1]}
    assert [m.unit_id for m in monsters(memory.read, TABLE)] == list(addresses)[:4]
    for seen in look:
        sighted = by_id[seen.unit_id]
        event = {'txt_id': sighted.txt_id, 'stats': sighted.stats, 'data_hex': sighted.data_hex}
        data = bytes.fromhex(sighted.data_hex or '')
        assert (sighted.txt_id, sighted.mode) == (seen.txt_id, seen.mode)
        assert (sighted.x, sighted.y) == (int(seen.x), int(seen.y))  # whole world units against the fractions
        assert (seen.x % 1, seen.y % 1) == (0.5, 0.25)
        assert data[0x1A] == seen.flags
        assert struct.unpack_from('<I', data, MONSTER_OWNER)[0] == seen.owner
        assert modifiers(event) == seen.modifiers
        assert leading(event) == seen.leader
        assert bool(stat(event, ALIGNMENT_STAT)) == seen.ally
        assert stat(event, HERALD_TIER_STAT) == seen.tier
        assert (stat(event, 6) >> 8, stat(event, 7) >> 8) == (seen.life, seen.max_life)
        assert (sighted.area, sighted.room, sighted.unit_at) == (108, BOUNDS, addresses[seen.unit_id])
        assert (seen.area, seen.room, seen.data_hex, seen.stats, seen.unit_at) == (None, None, None, None, 0)
