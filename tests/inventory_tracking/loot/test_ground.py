"""Ground runes from streamed item units: mode 3 (on ground) or 5 (dropping), valuable only."""

import struct

from inventory_tracking.loot.ground import GroundRune, ground_runes


TABLE = 0x100000
ITEMS = TABLE + 4 * 1024


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


def item(memory, index, class_id, mode, x, y):
    unit_id = 128 * index + 5  # bucket 5
    address, path = 0x200000 + index * 0x200, 0x300000 + index * 0x100
    data = memory.block(address, 0x160)
    struct.pack_into('<IIII', data, 0, 4, class_id, unit_id, mode)
    struct.pack_into('<Q', data, 0x38, path)
    struct.pack_into('<II', memory.block(path, 0x28), 0x10, x, 0)
    struct.pack_into('<I', memory.blocks[path], 0x14, y)
    return address, unit_id


def test_only_valuable_runes_on_the_ground_are_returned():
    memory = Memory()
    heads = memory.block(ITEMS, 1024)
    specs = [
        (654, 3, 25500, 5400),  # Ber on the ground
        (645, 0, 1, 1),  # Pul in the inventory
        (625, 3, 25510, 5410),  # El on the ground: below the threshold
        (600, 3, 25520, 5420),  # not a rune
        (657, 5, 25530, 5430),  # Zod still dropping
    ]
    previous = 0
    ids = []
    for index, spec in reversed(list(enumerate(specs))):
        address, unit_id = item(memory, index, *spec)
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
        ids.append(unit_id)
    struct.pack_into('<Q', heads, 5 * 8, previous)

    runes = ground_runes(memory.read, TABLE, minimum='r21')

    assert sorted(runes, key=lambda r: r.class_id) == [
        GroundRune(654, 5, 25500, 5400),
        GroundRune(657, 128 * 4 + 5, 25530, 5430),
    ]


OBJECTS = TABLE + 2 * 1024


def shrine(memory, index, shrine_type, mode, x, y, *, table=0x2C9E9078):
    unit_id = 128 * index + 7  # bucket 7
    address, path, data = 0x400000 + index * 0x200, 0x500000 + index * 0x100, 0x600000 + index * 0x100
    unit = memory.block(address, 0x160)
    struct.pack_into('<IIII', unit, 0, 2, 83, unit_id, mode)
    struct.pack_into('<Q', unit, 0x10, data)
    struct.pack_into('<Q', unit, 0x38, path)
    struct.pack_into('<I', memory.block(path, 0x28), 0x10, x)
    struct.pack_into('<I', memory.blocks[path], 0x14, y)
    block = memory.block(data, 0x40)
    block[0x08] = shrine_type
    struct.pack_into('<Q', block, 0x10, table)
    return address


def test_only_wanted_unused_shrines_are_returned():
    from inventory_tracking.loot.ground import Shrine, nearby_shrines

    memory = Memory()
    heads = memory.block(OBJECTS, 1024)
    specs = [
        {'shrine_type': 18, 'mode': 0, 'x': 14662, 'y': 5182},  # unused Gem Shrine
        {'shrine_type': 14, 'mode': 0, 'x': 14600, 'y': 5100},  # Stamina: not wanted
        {'shrine_type': 18, 'mode': 2, 'x': 14700, 'y': 5200},  # Gem, already used
        {'shrine_type': 18, 'mode': 0, 'x': 14710, 'y': 5210, 'table': 0},  # not a shrine (no table)
    ]
    previous = 0
    for index, spec in reversed(list(enumerate(specs))):
        address = shrine(memory, index, **spec)
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 7 * 8, previous)

    assert nearby_shrines(memory.read, TABLE, types=frozenset({18})) == [Shrine(18, 7, 14662, 5182)]


def test_only_unopened_sparkly_chests_are_super_chests():
    # Win+C dump 20260930T135418Z-6b2890e1 (Cave 2): the glowing chest is object class 397
    # (d2data objects.json 'sparklychest'), mode 0 while closed.
    from inventory_tracking.loot.ground import SuperChest, nearby_super_chests

    memory = Memory()
    heads = memory.block(OBJECTS, 1024)
    specs = [(397, 0, 7612, 12522), (397, 2, 7700, 12600), (181, 0, 7650, 12550)]  # closed, opened, jungle chest
    previous = 0
    for index, (class_id, mode, x, y) in reversed(list(enumerate(specs))):
        address = shrine(memory, index, 0, mode, x, y)
        struct.pack_into('<I', memory.blocks[address], 4, class_id)
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 7 * 8, previous)

    assert nearby_super_chests(memory.read, TABLE) == [SuperChest(7, 7612, 12522)]
    assert SuperChest(7, 7612, 12522).label == 'Super chest'
