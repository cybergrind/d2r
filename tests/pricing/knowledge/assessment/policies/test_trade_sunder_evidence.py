import copy

import pytest


@pytest.mark.parametrize(
    ('name', 'stat', 'prop', 'catalog'),
    [
        ('Flame Rift', 39, '427', '1363635173'),
        ('Crack of the Heavens', 41, '428', '849307965'),
    ],
)
@pytest.mark.parametrize('value', [70, 90, -70, -90])
def test_original_sunder_projection_preserves_input_and_only_changes_penalty(name, stat, prop, catalog, value):
    from pricing.knowledge.assessment.policies.trade_sunder import project_properties

    row = {'name': name, 'rarity': 'unique', 'catalog_id': catalog, 'properties': {prop: value, '800': False}}
    original = copy.deepcopy(row)
    result = project_properties({'sunder_penalty': 'original_sunder'}, row, {f'{stat}:0': prop})
    assert result == {prop: -abs(value), '800': False}
    assert row == original


@pytest.mark.parametrize(
    'changes',
    [
        {'catalog_id': None},
        {'catalog_id': 'unreviewed'},
        {'catalog_id': '849307965'},
        {'name': "Gheed's Fortune"},
        {'rarity': 'magic'},
        {'properties': {'427': 69}},
        {'properties': {'427': 91}},
        {'properties': {'427': '70'}},
        {'properties': {}},
    ],
)
def test_sunder_projection_rejects_wrong_identity_missing_and_impossible_penalties(changes):
    from pricing.knowledge.assessment.policies.trade_sunder import project_properties

    row = {'name': 'Flame Rift', 'rarity': 'unique', 'catalog_id': '1363635173', 'properties': {'427': -70}}
    row.update(changes)
    with pytest.raises(ValueError, match=r'[Ss]under'):
        project_properties({'sunder_penalty': 'original_sunder'}, row, {'39:0': '427'})


@pytest.mark.parametrize(
    ('review', 'mapping'),
    [
        ({'sunder_penalty': 'unreviewed'}, {'39:0': '427'}),
        ({'sunder_penalty': 'original_sunder'}, {'41:0': '428'}),
        ({'sunder_penalty': 'original_sunder'}, {'39:0': '427', '80:0': '461'}),
    ],
)
def test_sunder_projection_does_not_borrow_other_roll_mapping(review, mapping):
    from pricing.knowledge.assessment.policies.trade_sunder import project_properties

    row = {'name': 'Flame Rift', 'rarity': 'unique', 'catalog_id': '1363635173', 'properties': {'427': -70}}
    with pytest.raises(ValueError, match=r'[Ss]under'):
        project_properties(review, row, mapping)


def test_ordinary_resistance_bonus_is_not_negated_without_a_sunder_review():
    from pricing.knowledge.assessment.policies.trade_sunder import project_properties

    row = {'name': 'Ring', 'rarity': 'magic', 'properties': {'427': 30}}
    assert project_properties({}, row, {'39:0': '427'}) == {'427': 30}
