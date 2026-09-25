import pytest

from pricing.knowledge.assessment.coverage import coverage
from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.test_market import listing


def test_crafted_sunder_charm_uses_charm_family_with_unique_identity_policy():
    candidate = facts('Crafted Sunder Charm', 'unique', 'Renewed Cold Rupture')
    assert classify(candidate) == ('charm', 'named')
    assert candidate.base_code != facts('Grand Charm', 'magic').base_code


@pytest.mark.parametrize(
    'name',
    [
        'Renewed Cold Rupture',
        'Renewed Flame Rift',
        'Renewed Crack of the Heavens',
        'Renewed Rotting Fissure',
        'Renewed Bone Break',
        'Renewed Black Cleft',
    ],
)
def test_native_crafted_sunder_names_keep_distinct_base_and_non_equipment_facets(name):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738, 797)]
    row = normalize_listing(raw, name=name, category='uniques', source='fixture')
    assert row['base_code'] == facts('Crafted Sunder Charm', 'unique').base_code
    assert row['ethereal'] is False
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'


def test_coverage_reports_implemented_comparison_strategies_without_claiming_full_price_coverage():
    result = coverage()
    assert 'csch' not in result['unclassified_types']
    assert {'base', 'affixed', 'named', 'runeword'} <= result['price_policies'].keys()
    assert all(p['coverage'] == 'partial' for p in result['price_policies'].values())
