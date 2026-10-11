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


def unique_item(memory, index, class_id, mode, *, quality=7, flags=0, table_id=0):
    address, unit_id = item(memory, index, class_id, mode, 25500 + index, 5400)
    data = 0x700000 + index * 0x100
    struct.pack_into('<Q', memory.blocks[address], 0x10, data)
    block = memory.block(data, 0x60)
    struct.pack_into('<I', block, 0x00, quality)
    struct.pack_into('<I', block, 0x18, flags)
    struct.pack_into('<I', block, 0x34, table_id)
    return address, unit_id


def chain(memory, addresses):
    previous = 0
    for address in reversed(addresses):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', memory.block(ITEMS, 1024), 5 * 8, previous)


def test_expensive_unique_drops_are_named_from_their_base():
    from inventory_tracking.items.metadata import metadata
    from inventory_tracking.loot.ground import GroundUnique, ground_uniques

    by_code = {base['code']: int(class_id) for class_id, base in metadata()['bases'].items()}
    memory = Memory()
    specs = [
        (by_code['7gw'], 3, {}),  # unique Unearthed Wand on the ground: only Death's Web
        (by_code['7gw'], 3, {'quality': 6}),  # a rare one
        (by_code['7gw'], 0, {}),  # a unique one in the stash
        (by_code['hax'], 3, {}),  # The Gnasher: no priced unique on this base
        (by_code['rin'], 5, {}),  # an unidentified unique ring: several candidates
        (by_code['utb'], 3, {'quality': 5}),  # set Mirrored Boots
    ]
    units = [unique_item(memory, index, class_id, mode, **extra) for index, (class_id, mode, extra) in enumerate(specs)]
    chain(memory, [address for address, _ in units])

    found = ground_uniques(memory.read, TABLE, minimum=2.5)

    assert sorted(found, key=lambda u: u.unit_id) == [
        GroundUnique("Death's Web", units[0][1], 25500, 5400),
        GroundUnique('Unique Ring (Sling?)', units[4][1], 25504, 5400),
        GroundUnique("Horazon's Legacy", units[5][1], 25505, 5400),
    ]


def test_item_units_of_a_class_are_returned_in_every_mode():
    from inventory_tracking.loot.ground import ItemSighting, item_units

    memory = Memory()
    specs = [(678, 0, 0, 0), (678, 5, 25500, 5400), (654, 3, 25510, 5410)]  # carried, dropping, another item
    previous = 0
    for index, spec in reversed(list(enumerate(specs))):
        address, _ = item(memory, index, *spec)
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', memory.block(ITEMS, 1024), 5 * 8, previous)

    found = item_units(memory.read, TABLE, {674, 678})

    assert found == [ItemSighting(678, 5, 0, 0, 0), ItemSighting(678, 128 + 5, 5, 25500, 5400)]


def test_wanted_materials_on_the_ground_are_named():
    from inventory_tracking.loot.ground import GroundMaterial, ground_materials
    from inventory_tracking.loot.materials import material_classes

    memory = Memory()
    heads = memory.block(ITEMS, 1024)
    specs = [
        (676, 3, 25500, 5400),  # a shard on the ground
        (586, 0, 1, 1),  # a perfect sapphire in the inventory
        (584, 3, 25510, 5410),  # a plain sapphire: not wanted
        (679, 5, 25520, 5420),  # a statue still dropping
    ]
    previous = 0
    for index, spec in reversed(list(enumerate(specs))):
        address, _ = item(memory, index, *spec)
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 5 * 8, previous)

    found = ground_materials(memory.read, TABLE, material_classes(['shards', 'gems', 'statues']))

    assert found == [
        GroundMaterial('Southern Worldstone Shard', 5, 25500, 5400),
        GroundMaterial("Talic's Anguish", 128 * 3 + 5, 25520, 5420),
    ]


def test_an_identified_charm_on_the_ground_is_one_the_player_dropped():
    # user, 2026-10-10 night: a small charm read, found bad and dropped was offered for pickup again
    from inventory_tracking.items.identity import IDENTIFIED_FLAG
    from inventory_tracking.loot.ground import ground_materials
    from inventory_tracking.loot.materials import appraised_classes, material_classes

    classes = material_classes(['charms', 'gems'])
    charm = next(class_id for class_id, name in classes.items() if name == 'Small Charm')
    memory = Memory()
    fresh, fresh_id = unique_item(memory, 0, charm, 3, quality=4)
    read, _ = unique_item(memory, 1, charm, 3, quality=4, flags=IDENTIFIED_FLAG)
    gem, gem_id = unique_item(memory, 2, 586, 3, quality=2, flags=IDENTIFIED_FLAG)  # a gem is not appraised
    chain(memory, [fresh, read, gem])

    found = ground_materials(memory.read, TABLE, classes, appraised_classes())

    assert [(item.label, item.unit_id) for item in found] == [('Small Charm', fresh_id), (classes[586], gem_id)]
    assert len(ground_materials(memory.read, TABLE, classes)) == 3
