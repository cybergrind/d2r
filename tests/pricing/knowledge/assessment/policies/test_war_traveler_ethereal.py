"""Native defense bounds distinguish boots without defaulting an omitted flag."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.policies.war_traveler_ethereal import infer


@pytest.mark.parametrize(
    ('code', 'tier', 'ed', 'total'),
    [
        ('xtb', 'Exceptional', 174, 131),
        ('xtb', 'Exceptional', 190, 139),
        ('utb', 'Elite', 190, 197),
        ('utb', 'Elite', None, 165),
    ],
)
def test_known_totals_prove_nonethereal_original_and_upgraded_boots(code, tier, ed, total):
    row = {
        'rarity': 'unique',
        'name': 'War Traveler',
        'base_code': code,
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_upgrade': code == 'utb',
        'properties': {'930': tier, '1855': total, **({'425': ed} if ed else {})},
    }
    before = deepcopy(row)
    assert infer(row) is False
    assert row == before


@pytest.mark.parametrize(
    'changes',
    [
        {'738': True},
        {'1855': 209},
        {'1855': 138},
        {'1855': True},
        {'425': 191},
        {'930': 'Elite'},
        {'1216': True},
        {'402': 1},
        {'399': 139, '1855': None},
    ],
)
def test_conflicting_or_impossible_original_defense_is_not_proof(changes):
    row = {
        'rarity': 'unique',
        'name': 'War Traveler',
        'base_code': 'xtb',
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'930': 'Exceptional', '1855': 139, '425': 190, **changes},
    }
    assert infer(row) is None
