"""Physical charm damage must participate in exact market comparisons."""

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.exact import AffixedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


def captured(maximum):
    row = Item('Grand Charm', 'magic', raw_stats=((19, 0, 49), (22, 0, maximum)), complete=True).capture()
    # The production decoder puts facets in item.affixes; the bank must do so too.
    row['item']['affixes'] = row.pop('affixes', row['item'].get('affixes', []))
    return normalize(row)


def test_physical_charm_comparisons_preserve_maximum_damage():
    first, gaps = AffixedHandler().contract(captured(10), 'charm')
    second, other_gaps = AffixedHandler().contract(captured(14), 'charm')
    assert not gaps
    assert not other_gaps
    assert first.properties['448'] == 10
    assert second.properties['448'] == 14
    assert first.properties != second.properties


def test_item_bank_uses_the_production_market_facet_envelope():
    row = Item('Grand Charm', 'magic', raw_stats=((19, 0, 49),), complete=True).capture()
    assert row['item']['affixes'][0]['property_id'] == '423'
    assert normalize(row).properties['423'] == 49


def test_mirrored_damage_stats_are_one_bonus_not_a_sum():
    row = Item(
        'Grand Charm',
        'magic',
        raw_stats=((19, 0, 49), (21, 0, 2), (23, 0, 2), (159, 0, 2), (22, 0, 10), (24, 0, 10), (160, 0, 10)),
        complete=True,
    ).capture()
    contract, gaps = AffixedHandler().contract(normalize(row), 'charm')
    assert not gaps
    assert contract.properties['416'] == 2
    assert contract.properties['448'] == 10


def test_conflicting_damage_mirrors_block_price_comparison():
    row = Item('Grand Charm', 'magic', raw_stats=((19, 0, 49), (22, 0, 10), (24, 0, 14)), complete=True).capture()
    contract, gaps = AffixedHandler().contract(normalize(row), 'charm')
    assert contract is None
    assert any('conflicting mirrored' in gap for gap in gaps)


def test_secondary_damage_without_primary_cannot_be_silently_discarded():
    row = Item('Grand Charm', 'magic', raw_stats=((19, 0, 49), (24, 0, 10)), complete=True).capture()
    contract, gaps = AffixedHandler().contract(normalize(row), 'charm')
    assert contract is None
    assert any('not completely decoded' in gap for gap in gaps)


def test_weapon_totals_do_not_become_flat_modifiers():
    from pricing.knowledge.assessment.mechanics.affixed_physical import affixed_physical_properties

    row = Item('Phase Blade', 'magic', raw_stats=((21, 0, 31), (22, 0, 35)), complete=True).capture()
    assert affixed_physical_properties(normalize(row)) == ({}, set(), [])
