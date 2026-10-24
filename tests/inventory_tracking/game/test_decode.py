"""A base's rolls read off the ground (inventory_tracking/game/decode.py `base_rolls`, `chain_defense`).

The fake item below is laid out as the captures show this build's (rca/2026-10-20/loot-m0-research.md R2): sockets,
staff mods and resists in the +0xE8 totals, a superior armor's enhanced defense (16) only in the +0xD0 modifier
chain, each list of it naming its owner (item address, unit type 4, unit id) and linking to the next at +0x48.
"""

import struct
from dataclasses import replace

from inventory_tracking.game import decode
from inventory_tracking.game.decode import BASE_ROLLS_SEEN, base_rolls, rolled, rolls
from inventory_tracking.game.layout import FULL_STATS
from inventory_tracking.game.records import VALUABLE, Drop, Rolls
from inventory_tracking.items.identity import ETHEREAL_FLAG, FLAGS_OFFSET, ITEM_DATA_SIZE, RUNEWORD_FLAG
from inventory_tracking.macros.pickmode import shield_base
from tests.inventory_tracking.fake_memory import Memory


ITEM, ROOT, DATA = 0x10000, 0x20000, 0x30000  # the unit, its stat list holder, its item data
UNIT = 1728653239
MONARCH = 447  # uit (items/data/item_metadata.json)
CHAIN, LINK, LIST_STATS = 0xD0, 0x48, 0x30  # native/item_diagnostics.py


class Item:
    """A fake item's memory: the holder, the totals and the modifier chain's lists."""

    def __init__(self, totals, *, flags: int = 0) -> None:
        self.memory = Memory()
        self.next = 0x100000
        self.root = self.memory.block(ROOT, 0x200)
        struct.pack_into('<II', self.root, 8, 4, UNIT)
        struct.pack_into('<QQ', self.root, FULL_STATS, self.array(totals), len(totals))
        data = self.memory.block(DATA, ITEM_DATA_SIZE)
        struct.pack_into('<I', data, FLAGS_OFFSET, flags)

    def array(self, entries) -> int:
        address, self.next = self.next, self.next + 0x1000
        raw = self.memory.block(address, max(8, len(entries) * 8))
        for slot, entry in enumerate(entries):
            struct.pack_into('<HHi', raw, slot * 8, *entry)
        return address

    def chain(self, *lists: tuple[tuple[int, int], list]) -> None:
        """The +0xD0 chain: each list (owner (address, unit id), its (layer, stat id, value) entries), in order."""
        addresses = [0x200000 + index * 0x1000 for index in range(len(lists))]
        for index, ((owner, unit), entries) in enumerate(lists):
            header = self.memory.block(addresses[index], 0x60)
            struct.pack_into('<QII', header, 0, owner, 4, unit)
            struct.pack_into('<QQ', header, LIST_STATS, self.array(entries), len(entries))
            struct.pack_into('<Q', header, LINK, addresses[index + 1] if index + 1 < len(lists) else 0)
        struct.pack_into('<Q', self.root, CHAIN, addresses[0] if addresses else 0)

    def unit(self) -> dict:
        return {'unit_id': UNIT, 'address': ITEM, 'stats_pointer': ROOT, 'data_pointer': DATA}


def monarch(quality: int = 3) -> Drop:
    return Drop(UNIT, 0.0, 0.0, 'Monarch', VALUABLE, (2, 3), source='shown', txt=MONARCH, quality=quality)


def test_a_superior_monarchs_enhanced_defense_is_read_from_its_modifier_chain():
    # The player, 08:42 on 2026-10-20: "superior bases"; the 15 % ED Monarch rule (pickmode.shield_base) never fired on
    # a ground ED read always 0: 16 was taken from the totals, where this build never keeps it
    item = Item([(0, 194, 4), (0, 31, 160), (0, 72, 86)])
    item.chain(((ITEM, UNIT), [(0, 16, 15)]))
    found = rolled(item.memory.read, monarch(), item.unit())
    assert found.rolls == Rolls(4, (), 15, 0, False)
    assert rolls(found) == ' 4os 15% ED'  # the census line says it
    assert shield_base(found)
    assert BASE_ROLLS_SEEN[UNIT] == found.rolls  # read once a unit


def test_a_list_another_item_owns_is_passed_over():
    # What fills the sockets has a list of its own in the chain (516 of 9,751 captured units, 2026-10-20)
    item = Item([(0, 194, 4)])
    item.chain(((0x50000, 999), []), ((ITEM, UNIT), [(0, 16, 12)]))
    assert base_rolls(item.memory.read, item.unit()) == Rolls(4, (), 12)


def test_a_chain_without_an_enhanced_defense_reads_0_and_no_chain_reads_0():
    plain = Item([(0, 194, 4)])
    plain.chain()
    assert base_rolls(plain.memory.read, plain.unit()) == Rolls(4)
    BASE_ROLLS_SEEN.clear()
    other = Item([(0, 194, 0), (402, 107, 3)], flags=ETHEREAL_FLAG)
    other.chain(((ITEM, UNIT), [(0, 20, 20), (0, 102, 30)]))  # block and faster block: not ED
    assert base_rolls(other.memory.read, other.unit()) == Rolls(0, ((402, 3),), 0, 0, True)


def test_the_runeword_flag_is_read_into_the_rolls():
    """D12 (2026-10-23): the ItemData flag IFLAG_RUNEWORD (MapAssist Types/Items.cs:2460, 0x04000000) on a ground
    base: a runeword, never a plain base (loot/facts.py `from_drop`)."""
    BASE_ROLLS_SEEN.clear()
    item = Item([(0, 194, 4)], flags=RUNEWORD_FLAG | ETHEREAL_FLAG)
    item.chain()
    assert base_rolls(item.memory.read, item.unit()) == Rolls(4, ethereal=True, runeword=True)
    BASE_ROLLS_SEEN.clear()
    plain = Item([(0, 194, 4)], flags=ETHEREAL_FLAG)
    plain.chain()
    assert base_rolls(plain.memory.read, plain.unit()) == Rolls(4, ethereal=True)


def test_a_chain_not_read_whole_leaves_the_ed_unread_and_is_read_again():
    item = Item([(0, 194, 4)])
    item.chain(((ITEM, UNIT), [(0, 16, 15)]))
    struct.pack_into('<II', item.root, 8, 4, UNIT + 1)  # the holder names another unit: not this item's
    found = base_rolls(item.memory.read, item.unit())
    assert found == Rolls(4, (), None, damage=None)
    assert not shield_base(replace(monarch(), rolls=found))  # unread: not taken
    assert rolls(replace(monarch(), rolls=found)) == ' 4os'
    assert UNIT not in BASE_ROLLS_SEEN
    struct.pack_into('<II', item.root, 8, 4, UNIT)  # the next look reads it whole
    assert base_rolls(item.memory.read, item.unit()) == Rolls(4, (), 15)
    assert UNIT in BASE_ROLLS_SEEN


def test_a_broken_link_or_a_list_of_another_kind_leaves_the_ed_unread():
    broken = Item([(0, 194, 4)])
    struct.pack_into('<Q', broken.root, CHAIN, 0x7F000000)  # points at nothing readable
    assert base_rolls(broken.memory.read, broken.unit()) == Rolls(4, (), None, damage=None)
    BASE_ROLLS_SEEN.clear()
    foreign = Item([(0, 194, 4)])
    foreign.chain(((ITEM, UNIT), [(0, 16, 15)]))
    struct.pack_into('<I', foreign.memory.blocks[0x200000], 8, 1)  # a monster's list, not an item's
    assert base_rolls(foreign.memory.read, foreign.unit()) == Rolls(4, (), None, damage=None)


def test_the_totals_enhanced_defense_is_taken_should_a_build_keep_it_there(monkeypatch):
    item = Item([(0, 194, 0), (0, 16, 15)])
    monkeypatch.setattr(decode, 'chain_sums', lambda read, unit, ids: dict.fromkeys(ids, 0))
    assert base_rolls(item.memory.read, item.unit()) == Rolls(0, (), 15)


GIANT_THRESHER, GRAND_MATRON_BOW, ARCHON = 258, 302, 443  # 7wc, amc, utp (items/data/item_metadata.json)


def test_a_superior_weapons_enhanced_damage_is_read_from_its_modifier_chain():
    # M5 (the player, 2026-10-20 ~12:00: "start all three"): a polearm is read off the ground, its ED (17) in the
    # chain
    item = Item([(0, 194, 0)], flags=ETHEREAL_FLAG)
    item.chain(((ITEM, UNIT), [(0, 17, 15), (0, 18, 15)]))
    thresher = Drop(UNIT, 0.0, 0.0, 'Giant Thresher', VALUABLE, (2, 4), source='shown', txt=GIANT_THRESHER,
                    quality=3)  # fmt: skip
    found = rolled(item.memory.read, thresher, item.unit())
    assert found.rolls == Rolls(0, (), 0, 0, True, 15)
    assert rolls(found) == ' 0os 15% ED'


def test_a_bows_skill_tab_automod_is_read_from_its_totals():
    # 96 of 96 captured superior Amazon bows hold 188 in the totals (a Grand Matron Bow 188:0 = 3, 194 = 5)
    item = Item([(0, 194, 4), (0, 188, 3)])
    item.chain(((ITEM, UNIT), [(0, 17, 12), (0, 18, 12)]))
    bow = Drop(UNIT, 0.0, 0.0, 'Grand Matron Bow', VALUABLE, (2, 4), source='shown', txt=GRAND_MATRON_BOW, quality=3)
    found = rolled(item.memory.read, bow, item.unit())
    assert found.rolls == Rolls(4, (), 0, 0, False, 12, ((0, 3),))
    assert rolls(found) == ' 4os +3 Bow and Crossbow Skills 12% ED'


POSSESSED_GRIMOIRE = 517  # waa (items/data/item_metadata.json, itemtypes `grim`)


def test_a_white_grimoires_sockets_are_read_off_the_ground():
    # The player, 2026-10-20 ~17:30: "add grimoires to the ground read" (a socketed Possessed Grimoire was shown, its
    # socket count unread); a magic one still holds nothing to judge (R1)
    item = Item([(0, 194, 2)])
    item.chain()
    book = Drop(UNIT, 0.0, 0.0, 'Possessed Grimoire', VALUABLE, (2, 2), source='shown', txt=POSSESSED_GRIMOIRE,
                quality=2)  # fmt: skip
    assert rolled(item.memory.read, book, item.unit()).rolls == Rolls(2)
    assert rolled(item.memory.read, replace(book, quality=4), item.unit()).rolls is None


def test_a_magic_body_armor_is_not_read_its_ground_holds_nothing_to_judge():
    # R1: an unidentified magic item holds no socket count and no affix; the old types are still read for magic
    item = Item([(0, 194, 0)])
    item.chain()
    archon = Drop(UNIT, 0.0, 0.0, 'Archon Plate', VALUABLE, (2, 3), source='shown', txt=ARCHON, quality=4)
    assert rolled(item.memory.read, archon, item.unit()).rolls is None
    assert rolled(item.memory.read, replace(archon, quality=2), item.unit()).rolls == Rolls(0)


TOMB_WAND, JAWBONE_VISOR, SCISSORS_QUHAB, BONEWEAVE_BOOTS = 105, 473, 188, 457  # 9bw, ba6, 9qr, umb (items metadata)


def test_every_weapon_and_armor_type_of_the_item_data_is_read_off_the_ground():
    # The player, 2026-10-20 ~18:45: "it looks like we don't need to pickup them to assess, so it worth to assess every
    # item": every weapon and armor type of the items metadata but the throwing potions
    from inventory_tracking.game.layout import BASE_ROLLED_TYPES
    from inventory_tracking.items.metadata import metadata

    types = {row['type'] for row in metadata()['bases'].values() if row['category'] in ('weapons', 'armor')}
    assert types - {'tpot'} == BASE_ROLLED_TYPES


def test_a_white_class_items_staff_mods_are_read_from_its_totals():
    # [verified] 2026-10-20 on 24,852 captured white and superior units: a class item's staff mods (107) lie in the
    # +0xE8 totals, e.g. a normal Jawbone Visor 107:149 = 2, 107:150 = 2, 107:154 = 2, 194 = 3; a Tomb Wand 107:92 = 2
    item = Item([(0, 194, 3), (149, 107, 2), (150, 107, 2), (154, 107, 3)])
    item.chain()
    visor = Drop(UNIT, 0.0, 0.0, 'Jawbone Visor', VALUABLE, (2, 2), source='shown', txt=JAWBONE_VISOR, quality=2)
    found = rolled(item.memory.read, visor, item.unit())
    assert found.rolls == Rolls(3, ((149, 2), (150, 2), (154, 3)))
    assert rolls(found) == ' 3os +2 Battle Orders +2 Grim Ward +3 War Cry'  # skills.json 149, 150, 154
    wand = Drop(UNIT + 1, 0.0, 0.0, 'Tomb Wand', VALUABLE, (1, 2), source='shown', txt=TOMB_WAND, quality=4)
    assert rolled(item.memory.read, wand, item.unit()).rolls is None  # a magic wand holds nothing to judge (R1)


def test_a_look_reads_a_base_once_and_then_takes_it_from_the_cache():
    # The cost of the wider read: one stat and chain read the first time a shown base is seen, a dict hit after
    import time

    item = Item([(0, 194, 2), (269, 107, 3)])
    item.chain()
    claw = Drop(UNIT, 0.0, 0.0, 'Scissors Quhab', VALUABLE, (1, 3), source='shown', txt=SCISSORS_QUHAB, quality=2)
    reads = []

    def counted(address, size):
        reads.append(address)
        return item.memory.read(address, size)

    first = rolled(counted, claw, item.unit())
    assert first.rolls == Rolls(2, ((269, 3),))
    once = len(reads)
    started = time.perf_counter()
    for _ in range(1000):
        assert rolled(counted, claw, item.unit()).rolls == first.rolls
    looks = time.perf_counter() - started
    assert len(reads) == once  # no memory read after the first
    assert looks < 0.5  # 1,000 looks of a cached base: well under 1 ms each
    boots = Drop(UNIT, 0.0, 0.0, 'Boneweave Boots', VALUABLE, (2, 2), source='shown', txt=BONEWEAVE_BOOTS, quality=2)
    assert rolled(counted, boots, item.unit()).rolls is not None  # read (a cached unit id), and no wants row picks it
