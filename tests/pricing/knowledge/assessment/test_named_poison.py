from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def hellplague():
    mapping = {17: '510', 18: '510', 60: '462', 62: '463', 48: '458', 49: '459'}
    values = {17: 71, 18: 71, 60: 5, 62: 5, 48: 25, 49: 75}
    stats = {
        f'{s}:0': {'status': 'decoded', 'raw': v, 'value': v, 'market_property': mapping[s]} for s, v in values.items()
    }
    for s, raw, value, unit in [
        (57, 48, 48 / 256, 'damage_per_frame'),
        (58, 96, 96 / 256, 'damage_per_frame'),
        (59, 150, 6, 'seconds'),
        (326, 1, 1, 'count'),
    ]:
        stats[f'{s}:0'] = {'status': 'decoded', 'raw': raw, 'value': value, 'unit': unit}
    stats['126:1'] = {'status': 'decoded', 'value': 2, 'market_property': '586'}
    return replace(
        facts('Long Sword', 'unique', 'Hellplague'),
        stats=stats,
        properties={**{mapping[s]: v for s, v in values.items()}, '586': 2},
        projection_gaps=[f'No verified market mapping for native stat {s}:0.' for s in (57, 58, 59, 326)],
    )


def test_fixed_named_poison_range_does_not_collapse_into_single_market_value():
    contract, gaps = NamedHandler().contract(hellplague(), 'weapon')
    assert not gaps
    assert contract is not None
    assert '589' not in contract.properties  # 28-56 damage cannot become a scalar 28 or 56.
    assert contract.properties['510'] == 71


@pytest.mark.parametrize('key', ['57:0', '58:0', '59:0', '326:0'])
def test_named_poison_requires_every_component_and_single_source(key):
    item = hellplague()
    for stats in (
        {k: v for k, v in item.stats.items() if k != key},
        {**item.stats, key: {**item.stats[key], 'raw': 999}},
        {**item.stats, key: {**item.stats[key], 'value': 999}},
        {**item.stats, key: {**item.stats[key], 'unit': 'unverified'}},
    ):
        contract, gaps = NamedHandler().contract(replace(item, stats=stats), 'weapon')
        assert contract is None
        assert any('poison' in gap.lower() or 'native stat 57' in gap for gap in gaps)


def test_fixed_poison_range_rejects_scalar_market_projection():
    item = hellplague()
    item = replace(item, properties={**item.properties, '589': 56})
    contract, gaps = NamedHandler().contract(item, 'weapon')
    assert contract is None
    assert any('scalar market value' in gap for gap in gaps)
