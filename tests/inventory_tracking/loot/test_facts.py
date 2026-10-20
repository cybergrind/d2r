"""Layer 1 of the loot design (inventory_tracking/loot/facts.py): what an item is, as read."""

from dataclasses import replace

from inventory_tracking.game.records import VALUABLE, Carried, Drop, Rolls
from inventory_tracking.loot.facts import Owner, from_carried, from_drop


def test_a_white_bases_ground_read_holds_its_sockets_staff_mods_resists_and_its_chains_enhanced_defense():
    # rca/2026-10-20/loot-m0-research.md R2: the ED lives in the +0xD0 chain; game/decode.py `base_rolls` reads it
    # there since 2026-10-20, and `Rolls.defense` None says the chain was not read whole
    drop = Drop(1, 0.0, 0.0, 'Monarch', VALUABLE, (2, 3), source='shown', txt=447, quality=3,
                rolls=Rolls(4, ((402, 3),), defense=15, resists=12, ethereal=True))  # fmt: skip
    facts = from_drop(drop)
    assert (facts.code, facts.base_type, facts.sockets, facts.ethereal) == ('uit', 'shie', 4, True)
    assert facts.stat(107, 402) == 3
    assert facts.stat(41) == 12
    assert facts.stat(16) == 15
    assert facts.identified
    assert from_drop(replace(drop, rolls=Rolls(4))).stat(16) == 0  # a chain read whole without an ED: 0
    unread = from_drop(replace(drop, rolls=Rolls(4, defense=None)))
    assert unread.stat(16) is None  # unread, not 0
    assert unread.stat(194) == 4


def test_a_magic_items_ground_read_holds_no_affix_and_no_socket_count():
    # R1: an unidentified item's stat lists hold only its base stats; `Rolls(0)` is "unread" for it, not 0os
    drop = Drop(2, 0.0, 0.0, 'Monarch', VALUABLE, (2, 3), source='shown', txt=447, quality=4, rolls=Rolls(0))
    facts = from_drop(drop)
    assert not facts.identified
    assert facts.sockets is None
    assert facts.stat(194) is None
    assert facts.stat(20) is None
    assert facts.title() == 'magic Monarch'


def test_a_carried_item_without_its_read_is_its_class_and_quality_only():
    facts = from_carried(Carried(3, 342, 3, 0, (2, 2), 7, False, 0), owner=Owner.LOOP)
    assert (facts.code, facts.base_name, facts.row, facts.rolls, facts.cell) == ('tbt', 'Light Plated Boots', None,
                                                                                 None, (3, 0))  # fmt: skip
    assert facts.stat(16) is None
