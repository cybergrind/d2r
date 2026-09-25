import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.test_market import listing


def flagged(name, flag, tier=None):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 930)]
    raw['properties'].append({'property_id': 1216, 'type': 'bool', 'bool': flag})
    if tier:
        raw['properties'].append({'property_id': 930, 'type': 'string', 'string': tier})
    category = 'sets' if name == "Sazabi's Mental Sheath" else 'uniques'
    return normalize_listing(raw, name=name, category=category, source='fixture')


@pytest.mark.parametrize(
    ('name', 'flag', 'base'),
    [
        ('Shaftstop', True, 'Boneweave'),
        ('Guardian Angel', True, 'Hellforge Plate'),
        ('Magefist', False, 'Light Gauntlets'),
        ("Sazabi's Mental Sheath", False, 'Basinet'),
    ],
)
def test_explicit_upgrade_flag_resolves_only_one_possible_named_base(name, flag, base):
    row = flagged(name, flag)
    assert row['base_code'] == facts(base).base_code
    assert row['base_upgrade'] is flag
    assert row['facet_basis']['base_code']['tier_source'] == 'explicit_upgrade_flag'
    assert '930' not in row['properties']


def test_normal_unique_upgrade_flag_does_not_choose_between_two_upgrade_outcomes():
    assert 'base_code' not in flagged('Magefist', True)
    assert 'base_code' not in flagged('Azurewrath', False)
    row = flagged('Shaftstop', False, 'Elite')
    assert row['mechanics_conflicts']


@pytest.mark.parametrize('flag', [0, 1, 'false', None])
def test_malformed_upgrade_flag_cannot_resolve_missing_tier(flag):
    assert 'base_code' not in flagged('Shaftstop', flag)
