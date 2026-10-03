import copy
from itertools import product

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_compound_rolls as compounds
from pricing.knowledge.definition_store import catalog


GROUPS = ('all_attributes', 'all_resistances')
ATTRS = ('0:0', '1:0', '2:0', '3:0')
RES = ('39:0', '41:0', '43:0', '45:0')
KEYS = (*ATTRS, *RES, '85:0')


def definition():
    return thaw(catalog().named['unique', 'Annihilus'])


def test_annihilus_has_two_independent_native_groups():
    assert compounds.verified_definition(definition(), metadata()['stats'], GROUPS)
    points = {k: {10, 18, 19, 20} for k in (*ATTRS, *RES)} | {'85:0': {5, 9, 10}}
    expected = {(*([a] * 4), *([r] * 4), xp) for a, r, xp in product((10, 18, 19, 20), (10, 18, 19, 20), (5, 9, 10))}
    assert set(compounds.legal_vectors(KEYS, points, GROUPS)) == expected
    assert compounds.agree(KEYS, (19, 19, 19, 19, 20, 20, 20, 20, 10), GROUPS)
    bad = tuple(compounds.mismatched_vectors(KEYS, (20,) * 8 + (10,), dict.fromkeys((*ATTRS, *RES), (10, 20)), GROUPS))
    assert len(bad) == 8
    assert all(not compounds.agree(KEYS, v, GROUPS) for v in bad)


@pytest.mark.parametrize('stat', ['0', '1', '2', '3', '39', '41', '43', '45'])
@pytest.mark.parametrize('mutation', ['missing', 'range', 'property', 'operation'])
def test_each_group_member_requires_native_definition_and_operation(stat, mutation):
    d = definition()
    specs = copy.deepcopy(metadata()['stats'])
    if mutation == 'missing':
        del d['roll_ranges'][stat]
    elif mutation == 'range':
        d['roll_ranges'][stat]['max'] = 19
    elif mutation == 'property':
        d['roll_ranges'][stat]['property'] = 'unreviewed'
    else:
        specs[stat]['op'] += 1
    assert not compounds.verified_definition(d, specs, GROUPS)


@pytest.mark.parametrize('group', [('all_attributes', 'all_attributes'), ('unknown',), ()])
def test_duplicate_unknown_or_empty_groups_cannot_prove_shared_rolls(group):
    assert not compounds.verified_definition(definition(), metadata()['stats'], group)


@pytest.mark.parametrize('prop', ['all-stats', 'res-all'])
def test_equal_ranges_without_shared_game_property_are_not_enough(prop):
    d = definition()
    slot = next(k for k, v in d['game_definition'].items() if k.startswith('prop') and v == prop)
    d['game_definition'][slot] = 'unreviewed'
    assert not compounds.verified_definition(d, metadata()['stats'], GROUPS)
