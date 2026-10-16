"""The KP_6 loop's pickup mode (macros/pickmode.py; routes/lower-kurast-loop-plan.md phase 7). Item classes by their
items.txt row as the bundled metadata names them (items/metadata.py `item_base`), looked up, not written from memory."""

from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.pickmode import MODES, REGULAR, SURE, kept, next_mode, sure
from inventory_tracking.macros.world import GOLD, HEALING, VALUABLE, Drop, Loot


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def drop(name: str, *, source: str = 'material', quality: int = 2, kind: str = VALUABLE) -> Drop:
    return Drop(class_of(name), 0.0, 0.0, name, kind, source=source, txt=class_of(name), quality=quality)


def test_every_rune_gem_and_charm_is_a_sure_valuable():
    for name in ('El Rune', 'Ber Rune', 'Chipped Amethyst', 'Perfect Skull', 'Flawed Topaz', 'Small Charm',
                 'Large Charm', 'Grand Charm'):  # fmt: skip
        assert sure(drop(name, source='rune' if 'Rune' in name else 'material'))


def test_a_ring_is_one_when_rare_and_a_unique_when_the_marks_price_it():
    assert sure(drop('Ring', quality=6))
    assert not sure(drop('Ring', quality=4))  # magic
    assert sure(drop('Ring', source='unique', quality=7))
    assert not sure(drop('Amulet', quality=6))  # not asked for
    assert not sure(drop('Jewel', quality=4))


def test_the_rest_the_regular_pickup_takes_is_left_and_the_supplies_stay():
    assert not sure(drop('Phase Blade', source='shown', quality=4))
    assert not sure(drop('Archon Plate', source='named', quality=7))  # a unique the marks do not price
    assert sure(Drop(9, 0.0, 0.0, '6000 gold', GOLD))  # the staff's repairs (the player, 2026-10-16)
    assert sure(Drop(10, 0.0, 0.0, 'a super healing potion', HEALING))


def test_the_mode_keeps_or_filters_and_a_double_press_goes_round():
    blade, rune = drop('Phase Blade', source='shown', quality=4), drop('Ist Rune', source='rune')
    loot = Loot(drops=(blade, rune))
    assert kept(loot, REGULAR) == loot
    assert kept(loot, SURE).drops == (rune,)
    assert MODES[0] == SURE
    assert next_mode(SURE) == REGULAR
    assert next_mode(REGULAR) == SURE
