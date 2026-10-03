"""Unsocketable original glove totals can prove nonethereal without defaulting flags."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.policies.draculs_ethereal import infer


def listing():
    return {
        'rarity': 'unique',
        'name': "Dracul's Grasp",
        'base_code': 'uvg',
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_upgrade': False,
        'properties': {'930': 'Elite', '1855': 145, '425': 120},
    }


@pytest.mark.parametrize(('ed', 'total'), [(110, 138), (118, 143), (120, 145), (90, 125)])
def test_native_original_total_proves_nonethereal(ed, total):
    row = listing()
    row['properties'].update({'425': ed, '1855': total})
    before = deepcopy(row)
    assert infer(row) is False
    assert row == before


@pytest.mark.parametrize(
    'changes',
    [
        {'738': True},
        {'1855': 159},
        {'1855': 144},
        {'1855': True},
        {'425': 121},
        {'425': 89},
        {'425': True},
        {'930': 'Exceptional'},
        {'1216': True},
        {'402': 1},
        {'399': 145, '1855': None},
    ],
)
def test_conflicting_impossible_or_mislabeled_defense_proves_nothing(changes):
    row = listing()
    row['properties'].update(changes)
    assert infer(row) is None


@pytest.mark.parametrize(
    'changes',
    [
        {'name': 'War Traveler'},
        {'rarity': 'set'},
        {'base_code': 'xvg'},
        {'ethereal': True},
        {'ethereal': 0},
        {'sockets': None},
        {'sockets': True},
        {'socket_contents': 'unknown'},
        {'base_upgrade': True},
    ],
)
def test_other_item_or_unknown_conflicting_variant_proves_nothing(changes):
    assert infer({**listing(), **changes}) is None
