"""Monster units from the streamed unit table: position, level, and data/stats on first sight only."""

import struct

from inventory_tracking.terror.monsters import Monster, level_entry, loaded_rooms, monster_units


TABLE = 0x100000
MONSTERS = TABLE + 1 * 1024
LEVEL, ROOM2, ROOM1 = 0x500000, 0x510000, 0x520000
BOUNDS = (100, 200, 8, 8)


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
        108,
        BOUNDS,
        data_hex='aabbccdd' + '00' * 0x7C,
        stats=((0, 6, 1000), (0, 7, 2000)),
        base_stats=((0, 12, 95),),
    )
    assert found[1] == Monster(second_id, 156, 12, 5110, 5210, 108, BOUNDS)  # already known: no data, no stats


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
