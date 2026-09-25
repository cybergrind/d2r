import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.test_market import listing


def normalized(name, tier):
    raw = listing()
    for prop in raw['properties']:
        if prop['property_id'] == 797:
            prop['string'] = 'unique'
    if tier is not None:
        raw['properties'].append({'property_id': 930, 'type': 'string', 'string': tier})
    return normalize_listing(raw, name=name, category='uniques', source='fixture', currencies={'ist': 1})


@pytest.mark.parametrize(
    ('name', 'tier', 'base'),
    [
        ('Shaftstop', 'Exceptional', 'Mesh Armor'),
        ('Shaftstop', 'Elite', 'Boneweave'),
        ('Crown of Thieves', 'Exceptional', 'Grand Crown'),
        ('Crown of Thieves', 'Elite', 'Corona'),
    ],
)
def test_named_market_identity_and_explicit_tier_resolve_actual_base(name, tier, base):
    row = normalized(name, tier)
    assert row.get('base_code') == facts(base).base_code
    assert row['facet_basis']['base_code']['kind'] == 'named_base_tier'


def test_missing_or_impossible_named_market_tier_never_defaults_to_original():
    assert 'base_code' not in normalized('Shaftstop', None)
    for tier in ('Normal', 'invented'):
        row = normalized('Shaftstop', tier)
        assert 'base_code' not in row
        assert row['mechanics_conflicts']
    assert 'base_code' not in normalized('Unverified Unique', 'Elite')


@pytest.mark.parametrize(
    ('name', 'base'),
    [('Harlequin Crest', 'Shako'), ("Andariel's Visage", 'Demonhead'), ("Griffon's Eye", 'Diadem')],
)
def test_sole_elite_named_base_does_not_require_redundant_listing_tier(name, base):
    row = normalized(name, None)
    assert row.get('base_code') == facts(base).base_code
    assert row['base_upgrade'] is False
    assert row['facet_basis']['base_code']['tier_source'] == 'sole_elite_definition'
    assert '930' not in row['properties']


def test_missing_tier_does_not_choose_between_legacy_and_current_named_bases():
    assert 'base_code' not in normalized('Azurewrath', None)


def test_elite_definition_does_not_override_explicit_conflicting_tier():
    row = normalized('Harlequin Crest', 'Exceptional')
    assert row.get('base_code') is None
    assert row['mechanics_conflicts']


def test_sole_elite_set_base_preserves_unknown_sockets_and_proves_nonethereal():
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 738, 402, 934)]
    row = normalize_listing(raw, name="Sazabi's Cobalt Redeemer", category='sets', source='fixture')
    assert row['base_code'] == facts('Cryptic Sword').base_code
    assert row['ethereal'] is False
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'


def test_elite_named_base_rejects_a_claimed_upgrade():
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] != 797]
    raw['properties'].append({'property_id': 1216, 'type': 'bool', 'bool': True})
    row = normalize_listing(raw, name='Harlequin Crest', category='uniques', source='fixture')
    assert row['base_upgrade'] is False
    assert row['mechanics_conflicts']
