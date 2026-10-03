from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.chance_guards_market_review import possibilities


def row(**properties):
    return {
        'name': 'Chance Guards',
        'rarity': 'unique',
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': properties,
    }


def test_original_native_defense_and_flat_defense_are_separate():
    assert possibilities(row(**{'425': 23, '1855': 27})) == [('mgl', False)]
    # Bonus-defense property399 is not total-defense property1855.
    assert possibilities(row(**{'425': 23, '399': 27})) == []
    assert len(possibilities(row(**{'425': 23}))) == 6


def test_perfect_elite_defense_proves_variant_without_ed_selector():
    assert possibilities(row(**{'1855': 102})) == [('umg', False)]
    assert possibilities(row(**{'1855': 99, '425': 30, '930': 'Elite'})) == [('umg', False)]


@pytest.mark.parametrize(
    'props',
    [
        {'425': 31},
        {'425': True},
        {'1855': True},
        {'1855': 28, '425': 20},
        {'1855': 102, '930': 'Normal'},
        {'1855': 102, '1216': False},
        {'1855': 102, '738': True},
        {'1855': 102, '399': 102},
        {'402': 1},
        {'934': 'Perfect Topaz'},
    ],
)
def test_impossible_or_conflicting_properties_are_rejected(props):
    assert possibilities(row(**props)) == []


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('sockets', None),
        ('sockets', True),
        ('socket_contents', 'filled'),
        ('base_code', 'mgl'),
        ('base_upgrade', False),
        ('ethereal', True),
        ('name', 'Waterwalk'),
    ],
)
def test_missing_or_conflicting_facets_cannot_establish_elite_variant(field, value):
    item = deepcopy(row(**{'1855': 102}))
    item[field] = value
    assert possibilities(item) == []


def test_census_preserves_unknowns_and_rejects_conflicting_duplicates():
    from pricing.knowledge.assessment.maintenance.chance_guards_market_review import audit

    item = {**row(), 'id': 'a', 'seller_id': 'seller'}
    result = audit([item, item])
    assert len(result['observations']) == 1
    assert result['statuses'] == {'unverified_scope': 1}
    assert result['proven_sellers'] == []
    assert result['trade_threshold'] is None
    with pytest.raises(ValueError, match='Conflicting'):
        audit([item, {**item, 'seller_id': 'different'}])
