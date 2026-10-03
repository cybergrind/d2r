"""Recoverable shell evidence must not silently become a clean-item quote."""

from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.mechanics.jmod_shell import NATIVE_HASHES, shell_evidence


ROOT = Path(__file__).resolve().parents[5]


def listing():
    return {
        'name': 'Monarch',
        'base_code': 'uit',
        'rarity': 'magic',
        'sockets': 4,
        'ethereal': None,
        'socket_contents': 'filled',
        'properties': {'402': 4, '449': 30, '446': 20, '1855': 139},
    }


def test_total_defense_proves_nonethereal_shell_without_pricing_contents():
    row = listing()
    before = deepcopy(row)
    result = shell_evidence(row, ROOT)
    assert result == {
        'identity': "Jeweler's Monarch of Deflecting",
        'ethereal': False,
        'ethereal_basis': 'explicit_total_defense',
        'socket_contents': 'filled',
        'scope': 'recoverable_shell_only',
        'price_eligible': False,
    }
    assert row == before


@pytest.mark.parametrize('total', [133, 148])
def test_native_defense_endpoints(total):
    row = listing()
    row['properties']['1855'] = total
    assert shell_evidence(row, ROOT)['ethereal'] is False


@pytest.mark.parametrize('total', [None, True, 132, 149, 199, 222, '139'])
def test_missing_or_ambiguous_total_does_not_prove_nonethereal(total):
    row = listing()
    row['properties']['1855'] = total
    assert shell_evidence(row, ROOT) is None


def test_flat_defense_field_is_not_total_defense():
    row = listing()
    row['properties']['399'] = row['properties'].pop('1855')
    assert shell_evidence(row, ROOT) is None


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('name', 'Aegis'),
        ('base_code', 'invalid-base'),
        ('rarity', 'rare'),
        ('sockets', 3),
        ('sockets', True),
        ('ethereal', True),
        ('ethereal', 0),
    ],
)
def test_conflicting_variants_do_not_qualify(field, value):
    row = listing()
    row[field] = value
    assert shell_evidence(row, ROOT) is None


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('402', 3),
        ('449', 20),
        ('449', 50),
        ('446', 27),
        ('446', None),
        ('738', True),
        ('797', 'normal'),
    ],
)
def test_payload_totals_and_raw_variant_conflicts_are_not_intrinsic_affix_proof(field, value):
    row = listing()
    row['properties'][field] = value
    assert shell_evidence(row, ROOT) is None


def test_unknown_contents_stay_unknown():
    row = listing()
    row['socket_contents'] = 'unknown'
    assert shell_evidence(row, ROOT)['socket_contents'] == 'unknown'


def test_missing_native_evidence_fails_closed(tmp_path):
    assert shell_evidence(listing(), tmp_path) is None


@pytest.mark.parametrize('changed', NATIVE_HASHES)
def test_changed_native_catalog_requires_new_review(tmp_path, changed):
    target = tmp_path / 'third-parties/d2data/json'
    target.mkdir(parents=True)
    for name in NATIVE_HASHES:
        data = (ROOT / 'third-parties/d2data/json' / f'{name}.json').read_bytes()
        (target / f'{name}.json').write_bytes(data + (b'\n' if name == changed else b''))
    assert shell_evidence(listing(), tmp_path) is None
