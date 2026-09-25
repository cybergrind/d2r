from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def raven():
    values = {153: 1, 148: 20, 9: 40, 2: 20, 19: 250, 54: 15, 55: 45, 56: 4}
    mapping = {153: '591', 148: '1868', 9: '400', 2: '429', 19: '423', 54: '482', 55: '483'}
    stats = {
        f'{s}:0': {
            'status': 'decoded',
            'value': v,
            'raw': 100 if s == 56 else v,
            'unit': 'seconds' if s == 56 else None,
            'market_property': mapping.get(s),
        }
        for s, v in values.items()
    }
    return replace(
        facts('Ring', 'unique', 'Raven Frost'),
        stats=stats,
        properties={mapping[s]: v for s, v in values.items() if s in mapping},
        projection_gaps=['No verified market mapping for native stat 56:0.'],
    )


def test_raven_fixed_cold_allows_price_without_listing_fixed_damage():
    contract, gaps = NamedHandler().contract(raven(), 'jewelry')
    assert not gaps
    assert contract.intrinsic_properties['482'] == 15
    assert contract.intrinsic_properties['483'] == 45
    required = {k: v for k, v in contract.properties.items() if k not in contract.intrinsic_properties}
    assert required == {'429': 20, '423': 250}
    rows = [
        {
            'name': 'Raven Frost',
            'rarity': 'unique',
            'base_code': raven().base_code,
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'properties': required,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-24',
            'ask_ist': i,
        }
        for i in (1, 2, 3)
    ]
    assert price_from_comparables(evaluate(contract.to_dict(), rows), today=date(2026, 9, 24))['estimate_ist'] == 2


@pytest.mark.parametrize('key', ['54:0', '55:0', '56:0'])
def test_changed_or_missing_named_fixed_cold_never_becomes_intrinsic(key):
    item = raven()
    for stats in (
        {k: v for k, v in item.stats.items() if k != key},
        {**item.stats, key: {**item.stats[key], 'value': 999}},
        {**item.stats, key: {**item.stats[key], 'raw': 999}},
    ):
        contract, gaps = NamedHandler().contract(replace(item, stats=stats), 'jewelry')
        assert contract is None
        assert gaps
