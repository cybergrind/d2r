import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.market_base_inference import original_base_code


@pytest.mark.parametrize(
    ('name', 'total'),
    [
        ("Trang-Oul's Claws", 67),
        ("Trang-Oul's Claws", 74),
        ("Tal Rasha's Fine-Spun Cloth", 35),
        ("Tal Rasha's Fine-Spun Cloth", 40),
        ("Bane's Authority", 3),
    ],
)
def test_explicit_low_total_uniquely_identifies_original_base(name, total):
    row = {
        'name': name,
        'rarity': 'set',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'1855': total},
    }
    assert original_base_code(row) == named_definitions()['set', name]['base_code']


@pytest.mark.parametrize(
    'properties',
    [
        {'399': 74},
        {'1855': 75},
        {'1855': 97},
        {'1855': 74, '930': 'Elite'},
        {'1855': 74, '930': 'Normal'},
        {'1855': 74, '1216': True},
        {'1855': True},
    ],
)
def test_bonus_fields_upgraded_totals_and_conflicting_selectors_cannot_infer_original(properties):
    row = {
        'name': "Trang-Oul's Claws",
        'rarity': 'set',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': properties,
    }
    assert original_base_code(row) is None


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': None},
        {'ethereal': True},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'rarity': 'unique'},
        {'name': 'Other item'},
        {'base_code': 'invalid-base'},
    ],
)
def test_inference_never_repairs_an_unknown_or_conflicting_variant(changes):
    row = {
        'name': "Trang-Oul's Claws",
        'rarity': 'set',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'1855': 74},
        **changes,
    }
    assert original_base_code(row) is None


@pytest.mark.parametrize('properties', [{'1855': 36}, {'1855': 61}, {'399': 3}, {'1855': 3, '930': 'Exceptional'}])
def test_bane_belt_upgrade_and_bonus_fields_do_not_prove_normal_base(properties):
    row = {
        'name': "Bane's Authority",
        'rarity': 'set',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': properties,
    }
    assert original_base_code(row) is None
