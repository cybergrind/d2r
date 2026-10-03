"""Known impossible named variants must not regain tiers through baseline fallback."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies import named_baselines, named_tiers
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEMS = (
    Item('Ring', 'unique', "Nature's Peace", ((34, 0, 7), (45, 0, 20))),
    Item('Amulet', 'unique', "The Cat's Eye"),
    Item('Small Charm', 'unique', 'Annihilus'),
    Item('Large Charm', 'unique', 'Hellfire Torch'),
    Item('Grand Charm', 'unique', "Gheed's Fortune"),
    Item('Colossal Jewel', 'unique', "Guardian's Thunder"),
    Item('Crafted Sunder Charm', 'unique', 'Renewed Cold Rupture', named_table_id=427),
    *(Item('Jewel', 'unique', 'Rainbow Facet', named_table_id=i) for i in range(392, 400)),
)


@pytest.mark.parametrize('item', ITEMS, ids=lambda item: f'{item.name}-{item.named_table_id}')
@pytest.mark.parametrize('change', [{'ethereal': True}, {'sockets': 1}, {'socket_contents': 'filled'}])
def test_known_impossible_misc_variant_cannot_receive_strict_or_baseline_tier(item, change):
    facts = normalize(replace(item, **change).capture())
    assert named_tiers.assess_tier(facts)['tier'] is None
    assert named_baselines.assess_tier(facts)['tier'] is None


@pytest.mark.parametrize('ethereal', [False, None])
def test_legal_or_unknown_misc_variant_retains_identity_baseline(ethereal):
    facts = normalize(replace(ITEMS[0], ethereal=ethereal, sockets=None, socket_contents='unknown').capture())
    assert named_baselines.assess_tier(facts)['tier'] == 'low'


def test_armor_ethereal_variant_is_not_rejected_by_misc_mechanics():
    facts = normalize(Item('Mesh Armor', 'unique', 'Shaftstop', ethereal=True).capture())
    assert named_baselines.assess_tier(facts)['tier'] is not None


@pytest.mark.parametrize('change', [{'ethereal': True}, {'sockets': 1}, {'socket_contents': 'filled'}])
def test_impossible_ring_has_no_trade_tier_in_rendered_report(change):
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from pricing.knowledge.assessment.engine import assess

    extraction = replace(ITEMS[0], **change).capture()
    result = assess(extraction, profiles=[])
    assert result['trade_tier']['tier'] is None
    document = ItemAssessment.from_record(
        {
            'state': 'complete',
            'request_id': 'invalid-ring',
            'result': {'extraction': extraction, 'assessment': result, 'decision': {'price_status': 'unknown'}},
        }
    )
    assert not any(line.text.startswith('Trade tier:') for line in document.to_osd())


def test_upgraded_ethereal_phase_blade_keeps_its_baseline():
    from inventory_tracking.items.metadata import metadata

    item = Item('Dimensional Blade', 'unique', "Ginther's Rift", ethereal=True)
    facts = normalize(item.capture())
    base = next(row for row in metadata()['bases'].values() if row['name'] == 'Phase Blade')
    upgraded = replace(facts, base_code=base['code'], base_name=base['name'])
    assert named_baselines.assess_tier(upgraded)['tier'] == 'low'
