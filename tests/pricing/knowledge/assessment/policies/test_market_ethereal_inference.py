from copy import deepcopy

import pytest

from pricing.knowledge.assessment.policies import market_ethereal_inference as inference


def listing(ed=120):
    return {
        'name': 'Arachnid Mesh',
        'rarity': 'unique',
        'base_code': 'ulc',
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'425': ed, '1855': 63 * (100 + ed) // 100},
    }


@pytest.mark.parametrize('ed', [90, 106, 108, 109, 110, 116, 118, 119, 120])
def test_known_native_total_proves_nonethereal_without_mutating_the_listing(ed):
    row = listing(ed)
    original = deepcopy(row)
    assert inference.arachnid_ethereal(row) is False
    assert row == original


@pytest.mark.parametrize(
    'changes',
    [
        {'name': 'Other'},
        {'rarity': 'set'},
        {'base_code': None},
        {'base_code': 'zlb'},
        {'base_upgrade': True},
        {'ethereal': True},
        {'ethereal': 0},
        {'sockets': None},
        {'sockets': True},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'socket_contents': 'filled'},
    ],
)
def test_unknown_or_conflicting_variants_are_not_repaired(changes):
    assert inference.arachnid_ethereal({**listing(), **changes}) is None


@pytest.mark.parametrize(
    'properties',
    [
        {'425': 120},
        {'425': 120, '399': 138},
        {'425': 120, '1855': 137},
        {'425': 120, '1855': 206},
        {'425': 120, '1855': True},
        {'425': True, '1855': 138},
        {'425': 121, '1855': 139},
        {'425': 89, '1855': 119},
        {'1855': 138},
        {'425': 120, '1855': 138, '738': True},
        {'425': 120, '1855': 138, '930': 'Exceptional'},
        {'425': 120, '1855': 138, '1216': True},
        {'425': 120, '1855': 138, '402': 1},
    ],
)
def test_bonus_defense_impossible_totals_and_conflicting_selectors_are_not_proof(properties):
    assert inference.arachnid_ethereal({**listing(), 'properties': properties}) is None


@pytest.mark.parametrize('mutation', ['base', 'sockets', 'new-property', 'ed', 'flat-defense'])
def test_native_schema_changes_invalidate_the_proof(monkeypatch, mutation):
    from pricing.knowledge.assessment.domain.facts import thaw
    from pricing.knowledge.assessment.handlers.definitions import named_definitions

    rows = dict(named_definitions())
    row = thaw(rows[('unique', 'Arachnid Mesh')])
    if mutation == 'base':
        row['base_definition']['maxac'] = 64
    elif mutation == 'sockets':
        row['base_definition']['gemsockets'] = 1
    elif mutation == 'new-property':
        row['game_definition']['prop7'] = 'ac'
    elif mutation == 'ed':
        row['game_definition']['max1'] = 130
    else:
        row['game_definition']['prop1'] = 'ac'
    rows[('unique', 'Arachnid Mesh')] = row
    monkeypatch.setattr(inference, 'named_definitions', lambda: rows)
    assert inference.arachnid_ethereal(listing()) is None


def test_explicit_nonethereal_listing_does_not_need_a_missing_flag_inference():
    row = listing(110)
    row['ethereal'] = False
    row['properties'].pop('1855')
    assert inference.arachnid_ethereal(row) is False
    row['properties']['1855'] = 500
    assert inference.arachnid_ethereal(row) is None
