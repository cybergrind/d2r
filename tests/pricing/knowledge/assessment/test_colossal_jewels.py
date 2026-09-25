import pytest

from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.test_market import listing


@pytest.mark.parametrize('rarity', ['magic', 'rare', 'unique'])
def test_colossal_jewel_routes_to_jewel_family_without_becoming_normal_jewel(rarity):
    item = facts('Colossal Jewel', rarity)
    family, policy = classify(item)
    assert family == 'jewel'
    assert policy == ('named' if rarity == 'unique' else 'affixed')
    assert item.base_code != facts('Jewel', rarity).base_code


@pytest.mark.parametrize(
    'name',
    [
        "Defender's Bile",
        "Guardian's Thunder",
        "Protector's Frost",
        "Defender's Fire",
        "Protector's Stone",
        "Guardian's Light",
    ],
)
def test_named_colossal_jewel_market_uses_its_verified_base_and_impossible_flags(name):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738, 797)]
    row = normalize_listing(raw, name=name, category='uniques', source='fixture')
    assert row['base_code'] == facts('Colossal Jewel', 'unique').base_code
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row['ethereal'] is False
    assert row['observed_at'] is None
