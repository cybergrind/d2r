"""Raw variant equipment cells cannot borrow another build, variant or slot."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.planner_equipment_quote import equipment_quote_matches
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import PROFILES, read


def example(index=1):
    name = 'standard' if index == 1 else 'mf'
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == f'fire-warlock-{name}-ars-diabolos'))
    source = role['source']
    quote = read(source['path'])['variants'][index]['player']['Off-Hand'][0]
    return {
        'equipment_quote': {**source, 'locator': source['locator'] + '/0'},
        'quote': quote,
        'guide_tab': role['variant'],
    }, role


@pytest.mark.parametrize('index', [1, 2])
def test_raw_variant_cell_requires_explicit_source_quote_review(index):
    evidence, role = example(index)
    with pytest.raises(ValueError, match='Equipment quote'):
        equipment_quote_matches(evidence, role, lambda p: read(p['path']))
    assert equipment_quote_matches(evidence, role, lambda p: read(p['path']), allow_unquoted=True)


@pytest.mark.parametrize('change', ['slot', 'variant', 'build', 'hash', 'invented', 'noncanonical'])
def test_raw_variant_cell_rejects_unrelated_or_changed_evidence(change):
    evidence, role = example()
    ref = evidence['equipment_quote']
    if change == 'slot':
        ref['locator'] = ref['locator'].replace('Off-Hand', 'Weapon')
    elif change == 'variant':
        ref['locator'] = ref['locator'].replace('/1/', '/2/')
    elif change == 'build':
        role['build'] = 'different-build'
    elif change == 'hash':
        ref['sha256'] = 'stale'
    elif change == 'invented':
        evidence['quote'] = 'Invented equipment quote'
    else:
        ref['locator'] = ref['locator'].replace('/1/', '/01/')
    with pytest.raises(ValueError, match='Equipment quote'):
        equipment_quote_matches(evidence, role, lambda p: read(p['path']), allow_unquoted=True)
