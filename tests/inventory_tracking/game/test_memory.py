"""One look at the game walks each unit table once (cleanup A4, rca/2026-10-19/cleanup/town-items-world.md).

The ground below is one fake game: the character with its grids, a stash tab, and items on the ground, dropping,
in the belt and in the inventory, some of them unreadable in part. Each look is pinned to what the looks gave
when every classifier walked the item table on its own (the outputs below were read from that code on 2026-10-19,
before the walks were shared), and counted in walks: the reads of a unit table's 128 heads.
"""

import struct

import pytest

from inventory_tracking.game import memory as game_memory
from inventory_tracking.game.decode import BASE_ROLLS_SEEN, GOLD_SEEN
from inventory_tracking.game.layout import (
    BASE_STATS,
    FULL_REJUVENATION,
    FULL_STATS,
    GAME_NAME_RVA,
    GOLD_CLASS,
    GOLD_STAT,
    ITEM_OWNER,
    ITEM_UNIT,
    SUPER_HEALING,
)
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import GOLD, HEALING, REJUVENATION, VALUABLE, Drop, Loot
from inventory_tracking.game.units import walked
from inventory_tracking.items.grid import CUBE_GRID, INVENTORY_GRID
from inventory_tracking.items.identity import IDENTIFIED_FLAG
from inventory_tracking.loot import ground
from inventory_tracking.loot.materials import appraised_classes, material_classes
from inventory_tracking.loot.shown import ShownRule
from inventory_tracking.native.layout import (
    BELT_ITEM_MODE,
    LEVEL_AREA_ID,
    PATH_ROOM1,
    ROOM1_ROOM2,
    ROOM2_LEVEL,
)
from inventory_tracking.native.memory import ProcessMemory
from tests.inventory_tracking.fake_memory import Memory


TABLE, BASE = 0x100000, 0x10000000
PLAYER = 1  # the character's unit id
UNMAPPED = 0x7F000000  # a pointer nothing is read at
BER, EL, SHARD, STATUE = 654, 625, 676, 679
RING, SMALL_CHARM, CIRCLET, WAND = 537, 618, 418, 209  # rin, cm1, ci0, 7gw (items/data/item_metadata.json)
UNIQUE, RARE, MAGIC = 7, 6, 4


class Counted(Memory):
    """`Memory` counting its reads."""

    def __init__(self) -> None:
        super().__init__()
        self.reads: list[tuple[int, int]] = []

    def read(self, address, size):
        self.reads.append((address, size))
        return super().read(address, size)

    def walks(self, unit_type: int) -> int:
        """Reads of the unit table's heads of `unit_type`: one a walk."""
        return self.reads.count((TABLE + unit_type * 1024, 1024))


class Game:
    """A fake game's memory: units chained in their table's buckets, each block at its own address."""

    def __init__(self) -> None:
        self.memory = Counted()
        self.next = 0x1000000
        self.chains: dict[tuple[int, int], list[int]] = {}
        image = self.memory.block(BASE + GAME_NAME_RVA, 32)
        image[:6] = b'cyber9'

    def block(self, size: int) -> tuple[int, bytearray]:
        address, self.next = self.next, self.next + 0x1000
        return address, self.memory.block(address, size)

    def unit(self, unit_type, txt, unit_id, mode, *, data=0, path=0, stats=0, inventory=0) -> int:
        address, header = self.block(0x1C0)
        struct.pack_into('<IIIIQ', header, 0, unit_type, txt, unit_id, mode, data)
        struct.pack_into('<Q', header, 0x38, path)
        struct.pack_into('<QQ', header, 0x88, stats, inventory)
        self.chains.setdefault((unit_type, unit_id % 128), []).append(address)
        return address

    def stats(self, entries) -> int:
        """A stat list holder: (layer, stat id, value) at both the full and the base list."""
        holder, block = self.block(0x100)
        array, raw = self.block(max(8, len(entries) * 8))
        for offset in (FULL_STATS, BASE_STATS):
            struct.pack_into('<QQ', block, offset, array, len(entries))
        for slot, entry in enumerate(entries):
            struct.pack_into('<HHi', raw, slot * 8, *entry)
        return holder

    def player(self, unit_id, name, *, life, grids=None) -> int:
        data, raw = self.block(16)
        raw[: len(name)] = name.encode()
        path, block = self.block(0x28)
        struct.pack_into('<HHHH', block, 0, 0, 5000, 0, 5000)
        level, at = self.block(0x400)
        struct.pack_into('<I', at, LEVEL_AREA_ID, 109)
        room2, at = self.block(0xA0)
        struct.pack_into('<Q', at, ROOM2_LEVEL, level)
        room1, at = self.block(0x50)
        struct.pack_into('<Q', at, ROOM1_ROOM2, room2)
        struct.pack_into('<Q', block, PATH_ROOM1, room1)
        full = [(0, 12, 91)] + ([(0, 6, life[0] << 8), (0, 7, life[1] << 8)] if life else [])
        inventory = self.inventory(grids) if grids else 0
        address = self.unit(0, 7, unit_id, 1, data=data, path=path, stats=self.stats(full), inventory=inventory)
        if inventory:
            struct.pack_into('<Q', self.memory.blocks[inventory], 8, address)
        return address

    def inventory(self, grids: dict[int, tuple[int, int, dict[int, int]]]) -> int:
        """An inventory record holding `grids`: index -> (width, height, {cell: item address})."""
        address, block = self.block(0x48)
        count = max(grids) + 1
        array, records = self.block(count * 32)
        struct.pack_into('<I', block, 0, 0x1020304)
        struct.pack_into('<QQ', block, 0x20, array, count)
        for index, (width, height, cells) in grids.items():
            pointers, raw = self.block(width * height * 8)
            for cell, item in cells.items():
                struct.pack_into('<Q', raw, cell * 8, item)
            records[index * 32 + 0x10 : index * 32 + 0x12] = bytes((width, height))
            struct.pack_into('<Q', records, index * 32 + 0x18, pointers)
        return address

    def item(self, txt, unit_id, mode, *, at=(0, 0), quality=2, flags=0, table_id=0, owner=0, path=None, data=None):
        """An item unit; `path`/`data` None: a block of its own, else that pointer (0 none, UNMAPPED unreadable)."""
        if data is None:
            data, block = self.block(0x60)
            struct.pack_into('<I', block, 0x00, quality)
            struct.pack_into('<I', block, ITEM_OWNER, owner)
            struct.pack_into('<I', block, 0x18, flags)
            struct.pack_into('<I', block, 0x34, table_id)
        if path is None:
            path, block = self.block(0x28)
            struct.pack_into('<II', block, 0x10, *at)
            struct.pack_into('<I', block, 0x14, at[1])
        return self.unit(ITEM_UNIT, txt, unit_id, mode, data=data, path=path)

    def chain(self) -> None:
        for unit_type in {unit_type for unit_type, _ in self.chains}:
            self.memory.block(TABLE + unit_type * 1024, 1024)
        for (unit_type, bucket), addresses in self.chains.items():
            previous = 0
            for address in reversed(addresses):
                struct.pack_into('<Q', self.memory.blocks[address], 0x158, previous)
                previous = address
            struct.pack_into('<Q', self.memory.blocks[TABLE + unit_type * 1024], bucket * 8, previous)

    def game_memory(self) -> GameMemory:
        """`GameMemory` over the blocks (the fixture keeps it from opening a process)."""
        memory = GameMemory(0, BASE, TABLE)
        memory.read = self.memory.read  # type: ignore[method-assign]
        return memory


# The look's settings, as the KP_6 loop's (macros/runner.py `wanted`): the materials with the rings, a filter rule
# for unique wands and rare circlets, uniques from 2.5 Ist, gold from 1000, runes from El and marked from Ber
MATERIALS = material_classes(['shards', 'statues', 'charms', 'rings'])
SHOWN = (
    ShownRule(frozenset({UNIQUE}), False, frozenset({WAND})),
    ShownRule(frozenset({RARE}), False, frozenset({CIRCLET})),
)


@pytest.fixture
def game(monkeypatch) -> Game:
    monkeypatch.setattr(game_memory, 'ProcessMemory', lambda pid: ProcessMemory())  # unbound
    GOLD_SEEN.clear()
    BASE_ROLLS_SEEN.clear()
    game_memory.UNPLACED_GOLD.clear()
    play = Game()
    carried = play.item(RING, 128 * 10 + 5, 0, quality=RARE, owner=PLAYER)  # in the inventory
    cubed = play.item(SHARD, 128 * 11 + 5, 0, owner=PLAYER)  # in the cube
    play.player(PLAYER, 'CybergrindAA', life=(900, 1200), grids={
        INVENTORY_GRID: (10, 4, {0: carried}),
        CUBE_GRID: (3, 4, {4: cubed, 7: cubed}),
    })  # fmt: skip
    play.player(2, 'CybergrindAA', life=None)  # a shared stash tab
    play.item(BER, 128 * 1 + 5, 3, at=(5010, 5020))
    play.item(EL, 128 * 2 + 5, 5, at=(5011, 5021))  # dropping
    play.item(BER, 128 * 3 + 5, 3, path=UNMAPPED)  # where it lies cannot be read: not offered
    play.item(SHARD, 128 * 4 + 5, 3, at=(5012, 5022))
    play.item(STATUE, 128 * 5 + 5, 3, path=0)  # no path: the materials' (0, 0)
    play.item(SHARD, 128 * 6 + 5, 3, at=(5013, 5023), data=UNMAPPED)  # its data unread: quality 0
    play.item(SMALL_CHARM, 128 * 7 + 6, 3, at=(5014, 5024), quality=MAGIC)
    play.item(SMALL_CHARM, 128 * 8 + 6, 3, at=(5015, 5025), quality=MAGIC, flags=IDENTIFIED_FLAG)  # the player's
    play.item(RING, 128 * 9 + 6, 3, at=(5016, 5026), quality=UNIQUE)  # a ring and a unique: the unique's label
    play.item(RING, 128 * 12 + 6, 5, at=(5017, 5027), quality=RARE)
    play.item(CIRCLET, 128 * 13 + 7, 3, at=(5018, 5028), quality=RARE)  # the filter shows it
    play.item(CIRCLET, 128 * 14 + 7, 3, at=(5019, 5029), quality=MAGIC)  # it does not
    play.item(CIRCLET, 128 * 15 + 7, 3, at=(5020, 5030), quality=RARE, data=UNMAPPED)  # unread: not shown
    play.item(WAND, 128 * 16 + 7, 3, at=(5021, 5031), quality=UNIQUE)  # Death's Web
    play.item(WAND, 128 * 17 + 7, 0, quality=UNIQUE, owner=PLAYER)  # one in the stash
    play.item(SUPER_HEALING, 128 * 18 + 8, 3, at=(5022, 5032))
    play.item(FULL_REJUVENATION, 128 * 19 + 8, 5, at=(5023, 5033))
    play.item(FULL_REJUVENATION, 128 * 20 + 8, BELT_ITEM_MODE, at=(2, 0), owner=PLAYER)  # belt cell 2
    pile = play.item(GOLD_CLASS, 128 * 21 + 9, 3, at=(5024, 5034))
    struct.pack_into('<Q', play.memory.blocks[pile], 0x88, play.stats([(0, GOLD_STAT, 4200)]))
    small = play.item(GOLD_CLASS, 128 * 22 + 9, 3, at=(5025, 5035))
    struct.pack_into('<Q', play.memory.blocks[small], 0x88, play.stats([(0, GOLD_STAT, 300)]))
    play.chain()
    return play


def look(memory: GameMemory) -> Loot:
    return memory.loot(
        rune_minimum='r01',
        unique_minimum=2.5,
        materials=MATERIALS,
        gold_minimum=1000,
        shown=SHOWN,
        prized_rune_minimum='r30',
        prized_materials=frozenset({SHARD}),
    )


# What `loot` gave on the fixture with a walk of its own for each classifier (the code before 2026-10-19's change)
LOOT_DROPS = (
    Drop(133, 5010, 5020, 'Ber Rune', VALUABLE, (1, 1), True, 'rune', BER),
    Drop(261, 5011, 5021, 'El Rune', VALUABLE, (1, 1), False, 'rune', EL),
    Drop(517, 5012, 5022, 'Southern Worldstone Shard', VALUABLE, (1, 1), True, 'material', SHARD, 2),
    Drop(645, 0, 0, "Talic's Anguish", VALUABLE, (1, 2), False, 'material', STATUE, 2),
    Drop(773, 5013, 5023, 'Southern Worldstone Shard', VALUABLE, (1, 1), True, 'material', SHARD, 0),
    Drop(902, 5014, 5024, 'Small Charm', VALUABLE, (1, 1), False, 'material', SMALL_CHARM, MAGIC),
    Drop(1158, 5016, 5026, 'Unique Ring (Sling?)', VALUABLE, (1, 1), True, 'unique', RING),  # the unique's label
    Drop(1542, 5017, 5027, 'Ring', VALUABLE, (1, 1), False, 'material', RING, RARE),
    Drop(1671, 5018, 5028, 'Rare Circlet', VALUABLE, (2, 2), False, 'shown', CIRCLET, RARE),
    Drop(2055, 5021, 5031, "Death's Web", VALUABLE, (1, 2), True, 'unique', WAND),
    Drop(2697, 5024, 5034, '4200 gold', GOLD, (0, 0)),
    Drop(2312, 5022, 5032, 'a super healing potion', HEALING),
    Drop(2440, 5023, 5033, 'a full rejuvenation potion', REJUVENATION),
)


def test_a_look_at_the_loot_gives_what_one_walk_per_classifier_gave(game, caplog):
    with caplog.at_level('INFO'):
        loot = look(game.game_memory())

    assert loot.drops == LOOT_DROPS
    assert loot.belt == (None, None, FULL_REJUVENATION) + (None,) * 13
    assert (loot.life, loot.max_life, loot.game) == (900, 1200, ('cyber9', PLAYER))
    assert loot.room == ('#.........', '..........', '..........', '..........')
    assert loot.cube == ('...', '.#.', '.#.', '...')
    assert loot.carried == frozenset({128 * 10 + 5, 128 * 11 + 5})
    assert loot.shown == frozenset({1671})
    assert loot.classes == (
        *((drop.unit_id, drop.txt) for drop in LOOT_DROPS[:10]),
        (2697, GOLD_CLASS),
        (2312, SUPER_HEALING),
        (2440, FULL_REJUVENATION),
    )
    assert loot.stats == ((6, 900 << 8), (7, 1200 << 8), (12, 91))
    # the ground census and the gold pile's line, as the loop-watch tools read them (logwords.py)
    assert [record.getMessage() for record in caplog.records] == [
        'Macro: ground: normal Ber Rune at (5010, 5020): taken (rune)',
        'Macro: ground: normal El Rune at (5011, 5021): taken (rune)',
        'Macro: ground: normal Southern Worldstone Shard at (5012, 5022): taken (material)',
        'Macro: ground: magic Small Charm at (5014, 5024): taken (material)',
        'Macro: ground: magic Small Charm at (5015, 5025): left',
        'Macro: ground: unique Ring "Unique Ring (Sling?)" at (5016, 5026): taken (unique)',
        'Macro: ground: rare Ring at (5017, 5027): taken (material)',
        'Macro: ground: rare Circlet "Rare Circlet" at (5018, 5028): taken (shown)',
        'Macro: ground: magic Circlet at (5019, 5029): left',
        'Macro: ground: unique Unearthed Wand "Death\'s Web" at (5021, 5031): taken (unique)',
        'Macro: gold pile 2697: 4200 gold (the full stat list)',
    ]


def test_a_gold_pile_whose_place_is_unread_is_left_out_and_the_rest_of_the_look_kept(game, caplog):
    # It used to empty the whole look (a ValueError), every other drop unseen (player, 2026-10-19: "Never leave a game
    # while a valuable the loop would pick up lies on the ground")
    pile = game.item(GOLD_CLASS, 128 * 23 + 9, 3, path=UNMAPPED)
    struct.pack_into('<Q', game.memory.blocks[pile], 0x88, game.stats([(0, GOLD_STAT, 5000)]))
    game.chain()
    memory = game.game_memory()

    with caplog.at_level('INFO'):
        loot = look(memory)
        again = look(memory)

    assert loot.drops == again.drops == LOOT_DROPS
    assert loot.belt == (None, None, FULL_REJUVENATION) + (None,) * 13
    assert (loot.life, loot.carried) == (900, frozenset({128 * 10 + 5, 128 * 11 + 5}))
    assert (loot.room, loot.cube) == (('#.........',) + ('..........',) * 3, ('...', '.#.', '.#.', '...'))
    unread = [record.getMessage() for record in caplog.records if 'gold pile 2953' in record.getMessage()]
    assert unread == [
        'Macro: gold pile 2953: 5000 gold (the full stat list)',
        'Macro: gold pile 2953: its place is unread: left out of this look',
    ]  # once, not at every look


def test_the_ground_classifiers_of_one_walk_give_what_their_own_walks_gave(game):
    read = game.memory.read
    on_ground = ground.on_ground(read, walked(read, TABLE, ITEM_UNIT)['units'])

    runes = ground.runes_among(on_ground, minimum='r01')
    materials = ground.materials_among(on_ground, MATERIALS, appraised_classes())
    shown = ground.shown_among(on_ground, SHOWN)
    uniques = ground.uniques_among(on_ground, minimum=2.5)
    potions = ground.sightings_among(on_ground, {SUPER_HEALING, FULL_REJUVENATION})

    # each one as its own walk gave it: the table's functions are these over a walk of their own
    assert runes == ground.ground_runes(read, TABLE, minimum='r01')
    assert materials == ground.ground_materials(read, TABLE, MATERIALS, appraised_classes())
    assert shown == ground.ground_shown(read, TABLE, SHOWN)
    assert uniques == ground.ground_uniques(read, TABLE, minimum=2.5)
    every = ground.item_units(read, TABLE, {SUPER_HEALING, FULL_REJUVENATION})
    assert potions == [sighting for sighting in every if sighting.mode in ground.GROUND_MODES]
    # and what those walks gave before the change, pinned
    assert runes == [ground.GroundRune(BER, 133, 5010, 5020), ground.GroundRune(EL, 261, 5011, 5021)]
    assert [(m.label, m.unit_id, m.x, m.y, m.quality) for m in materials] == [
        ('Southern Worldstone Shard', 517, 5012, 5022, 2),
        ("Talic's Anguish", 645, 0, 0, 2),
        ('Southern Worldstone Shard', 773, 5013, 5023, 0),
        ('Small Charm', 902, 5014, 5024, 4),
        ('Ring', 1158, 5016, 5026, 7),
        ('Ring', 1542, 5017, 5027, 6),
    ]
    assert [(m.label, m.unit_id, m.quality) for m in shown] == [
        ('Rare Circlet', 1671, RARE),
        ('Unique Unearthed Wand', 2055, UNIQUE),
    ]
    assert [(u.label, u.unit_id, u.x, u.y) for u in uniques] == [
        ('Unique Ring (Sling?)', 1158, 5016, 5026),
        ("Death's Web", 2055, 5021, 5031),
    ]
    assert potions == [
        ground.ItemSighting(SUPER_HEALING, 2312, 3, 5022, 5032),
        ground.ItemSighting(FULL_REJUVENATION, 2440, 5, 5023, 5033),
    ]


def test_one_look_at_the_loot_walks_each_unit_table_once(game):
    memory = game.game_memory()
    look(memory)
    # before 2026-10-19: the item table 6 times (runes, materials, shown, uniques, the look's own, the potions)
    # and the player table twice (the character, its grids)
    assert (game.memory.walks(ITEM_UNIT), game.memory.walks(0)) == (1, 1)


def test_the_carried_items_and_the_stash_are_read_with_one_walk_of_each_table(game):
    memory = game.game_memory()
    pack = memory.carried()
    assert pack is not None
    assert [(item.unit_id, item.txt, item.x, item.y) for item in pack.items] == [(128 * 10 + 5, RING, 0, 0)]
    assert [(item.unit_id, item.x, item.y) for item in pack.in_cube] == [(128 * 11 + 5, 1, 1)]
    # before 2026-10-19: the player table twice, for the character and for its grids
    assert (game.memory.walks(ITEM_UNIT), game.memory.walks(0)) == (1, 1)
    game.memory.reads.clear()
    assert memory.stash_view() is None  # no stash page in this game: no view
    assert (game.memory.walks(ITEM_UNIT), game.memory.walks(0)) == (1, 1)
