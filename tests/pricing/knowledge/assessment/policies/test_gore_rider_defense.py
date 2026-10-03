"""A joint original-base/nonethereal proof requires the exact ED and defense pair."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.policies.gore_rider_defense import infer, original_code


def row():
    return {
        'rarity': 'unique',
        'name': 'Gore Rider',
        'base_code': None,
        'base_upgrade': None,
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'1855': 162, '425': 200},
    }


@pytest.mark.parametrize(('ed', 'total'), [(164, 142), (182, 152), (200, 162), (160, 140)])
def test_exact_original_pair_proves_both_variant_fields(ed, total):
    listing = row()
    listing['properties'].update({'425': ed, '1855': total})
    before = deepcopy(listing)
    assert original_code(listing) == 'xhb'
    assert infer(listing) is False
    assert listing == before


@pytest.mark.parametrize(
    'changes',
    [
        {'1855': 213},
        {'1855': 161},
        {'1855': True},
        {'425': None},
        {'425': 201},
        {'425': 159},
        {'930': 'Normal'},
        {'930': 'Elite'},
        {'1216': True},
        {'738': True},
        {'402': 1},
        {'399': 162},
    ],
)
def test_unknown_or_contradictory_pair_proves_neither_field(changes):
    listing = row()
    listing['properties'].update(changes)
    assert original_code(listing) is None
    assert infer(listing) is None


@pytest.mark.parametrize(
    'changes',
    [
        {'base_code': 'uhb'},
        {'base_upgrade': True},
        {'ethereal': True},
        {'sockets': None},
        {'sockets': True},
        {'socket_contents': 'unknown'},
        {'name': 'War Traveler'},
    ],
)
def test_wrong_or_unknown_variant_is_not_normalized(changes):
    assert original_code({**row(), **changes}) is None


@pytest.mark.parametrize(('ed', 'total'), [(200, 195), (200, 207), (200, 210), (200, 213), (196, 210)])
def test_upgraded_base_is_explicit_and_uses_rerolled_armor(ed, total):
    from pricing.knowledge.assessment.policies.gore_rider_defense import infer_variant, variant_code

    listing = {
        **row(),
        'base_code': 'uhb',
        'base_upgrade': True,
        'properties': {'425': ed, '1855': total, '930': 'Elite', '1216': True},
    }
    before = deepcopy(listing)
    assert original_code(listing) is None
    assert variant_code(listing) == 'uhb'
    assert infer_variant(listing) is False
    assert listing == before


@pytest.mark.parametrize(
    'changes',
    [
        {'1855': 194},
        {'1855': 214},
        {'1855': 279},
        {'930': 'Exceptional'},
        {'1216': False},
        {'738': True},
        {'425': None},
        {'1855': None},
    ],
)
def test_upgraded_conflicts_do_not_become_original_proof(changes):
    from pricing.knowledge.assessment.policies.gore_rider_defense import infer_variant, variant_code

    listing = {
        **row(),
        'base_code': 'uhb',
        'base_upgrade': True,
        'properties': {'425': 200, '1855': 213, '930': 'Elite', **changes},
    }
    assert variant_code(listing) is None
    assert infer_variant(listing) is None


def test_upgraded_defense_without_explicit_base_is_not_guessed():
    from pricing.knowledge.assessment.policies.gore_rider_defense import variant_code

    listing = {**row(), 'properties': {'425': 200, '1855': 213}}
    assert variant_code(listing) is None
