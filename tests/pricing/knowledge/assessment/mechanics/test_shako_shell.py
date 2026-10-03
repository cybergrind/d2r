"""Total defense can prove nonethereal without proving Shako's intrinsic roll."""

from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.mechanics.shako_shell import shell_evidence


ROOT = Path(__file__).resolve().parents[5]


def listing(total=98):
    return {
        'name': 'Harlequin Crest',
        'rarity': 'unique',
        'base_code': 'uap',
        'ethereal': None,
        'sockets': None,
        'socket_contents': 'unknown',
        'properties': {'1855': total},
    }


@pytest.mark.parametrize('total', [98, 99, 120, 130, 140, 141])
def test_defense_proves_nonethereal_but_not_an_empty_socket_or_perfect_roll(total):
    row = listing(total)
    before = deepcopy(row)
    assert shell_evidence(row, ROOT) == {
        'identity': 'Harlequin Crest',
        'ethereal': False,
        'ethereal_basis': 'explicit_total_defense',
        'sockets': None,
        'socket_contents': 'unknown',
        'scope': 'underlying_item_only',
        'intrinsic_defense_proved': False,
        'price_eligible': False,
    }
    assert row == before


@pytest.mark.parametrize('total', [None, True, '141', 97, 142, 147, 211])
def test_ambiguous_or_illegal_defense_does_not_prove_a_nonethereal_variant(total):
    assert shell_evidence(listing(total), ROOT) is None


def test_flat_defense_cannot_replace_total_defense():
    row = listing()
    row['properties'] = {'399': 141}
    assert shell_evidence(row, ROOT) is None


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': 0},
        {'sockets': 2},
        {'sockets': True},
        {'base_code': 'invalid-base'},
        {'name': 'Other'},
        {'rarity': 'set'},
        {'base_upgrade': True},
        {'properties': {'1855': 141, '738': True}},
        {'sockets': 0, 'socket_contents': 'filled'},
        {'sockets': 0, 'properties': {'1855': 141, '402': 1}},
        {'properties': {'1855': 141, '1216': True}},
        {'properties': {'1855': 141, '930': 'Exceptional'}},
        {'properties': {'1855': 141, '797': 'magic'}},
    ],
)
def test_conflicting_identity_and_variants_fail_closed(changes):
    assert shell_evidence({**listing(), **changes}, ROOT) is None


def test_filled_socket_is_preserved_and_not_used_to_claim_perfect_base_defense():
    row = {**listing(141), 'sockets': 1, 'socket_contents': 'filled'}
    result = shell_evidence(row, ROOT)
    assert result['socket_contents'] == 'filled'
    assert result['sockets'] == 1
    assert result['intrinsic_defense_proved'] is False


def test_missing_native_sources_prevent_inference(tmp_path):
    assert shell_evidence(listing(), tmp_path) is None
