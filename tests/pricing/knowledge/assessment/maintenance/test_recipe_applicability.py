"""Runeword quality exclusions do not imply socket, upgrade or price coverage."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs


def review():
    return json.loads((ROOT / 'pricing/knowledge/assessment/rules/recipe_applicability.json').read_text())


@pytest.mark.parametrize('quality', ['magic', 'rare', 'crafted', 'unique', 'set'])
def test_special_quality_closes_only_runeword_creation(quality):
    data = inputs()
    data[3]['profiles'][0]['qualities'] = [quality]
    rows = {row['id']: row for row in build_matrix(*data, recipe_applicability=review())['rows']}
    row = rows[f'use:role:{quality}']
    assert row['dimensions']['recipe_eligibility']['state'] == 'excluded'
    assert row['dimensions']['recipe_eligibility']['sources'][-1] == {
        'artifact': 'recipe_applicability',
        'locator': '/rules/0',
    }
    for dimension in ('socket_mechanics', 'market', 'stat_annotations', 'report'):
        assert row['dimensions'][dimension]['state'] == 'pending'
    assert rows['identity:u']['dimensions']['recipe_eligibility']['state'] == 'excluded'
    assert rows['identity:x']['dimensions']['recipe_eligibility']['state'] == 'pending'


@pytest.mark.parametrize('quality', ['normal', 'superior', 'low_quality', 'runeword', None, 'unknown'])
def test_other_qualities_still_require_individual_recipe_review(quality):
    data = inputs()
    data[3]['profiles'][0]['qualities'] = [quality]
    result = build_matrix(*data, recipe_applicability=review())
    row = next(row for row in result['rows'] if row['id'] == f'use:role:{quality}')
    assert row['dimensions']['recipe_eligibility']['state'] == 'pending'


def test_absent_review_does_not_close_recipes():
    assert all(row['dimensions']['recipe_eligibility']['state'] == 'pending' for row in build_matrix(*inputs())['rows'])


def test_unresolved_catalog_identity_cannot_borrow_quality_exclusion():
    data = inputs()
    data[0]['identities'][0]['catalog_ids'] = []
    result = build_matrix(*data, recipe_applicability=review())
    row = next(row for row in result['rows'] if row['id'] == 'identity:u')
    assert row['dimensions']['recipe_eligibility']['state'] == 'pending'


def test_completion_rechecks_native_review_inputs(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import verify_artifact_inputs

    with pytest.raises(ValueError, match='Missing completion input'):
        verify_artifact_inputs({'recipe_applicability': review(), 'list_rules': []}, tmp_path)
    verify_artifact_inputs({'recipe_applicability': review(), 'list_rules': []}, ROOT)


def test_changed_native_evidence_rejects_the_exclusion():
    document = review()
    path = next(iter(document['inputs']))
    document['inputs'][path] = '0' * 64
    with pytest.raises(ValueError, match='Stale'):
        build_matrix(*inputs(), recipe_applicability=document)


def test_rule_cannot_silently_expand_to_normal_items():
    document = deepcopy(review())
    document['rules'][0]['qualities'].append('normal')
    with pytest.raises(ValueError, match='quality'):
        build_matrix(*inputs(), recipe_applicability=document)


def test_named_evidence_inherits_only_verified_catalog_quality_exclusion():
    from pricing.knowledge.assessment.maintenance.recipe_applicability import apply_recipe_applicability

    identity = next(row for row in build_matrix(*inputs())['rows'] if row['id'] == 'identity:u')
    evidence = {
        'id': 'evidence:named',
        'kind': 'evidence',
        'name': 'Unmentioned',
        'quality': 'unique',
        'identity_ids': ['identity:u'],
        'dimensions': {
            'discovery': {'state': 'reviewed', 'sources': [{'artifact': 'recommendations', 'locator': '/rows/0'}]},
            **{
                key: {'state': 'pending', 'sources': []}
                for key in ('recipe_eligibility', 'socket_mechanics', 'market', 'leveling')
            },
        },
    }
    apply_recipe_applicability([identity, evidence], review(), ROOT)
    result = evidence['dimensions']['recipe_eligibility']
    assert result['state'] == 'excluded'
    assert result['identity_ids'] == ['identity:u']
    assert result['sources'][-1] == {'artifact': 'recipe_applicability', 'locator': '/rules/0'}
    for key in ('socket_mechanics', 'market', 'leveling'):
        assert evidence['dimensions'][key]['state'] == 'pending'
    for changes in (
        {'identity_ids': []},
        {'identity_ids': ['missing']},
        {'identity_ids': ['identity:u', 'missing']},
        {'name': 'Other'},
        {'quality': 'set'},
    ):
        invalid = deepcopy(evidence)
        invalid.update(changes)
        invalid['dimensions']['recipe_eligibility'] = {'state': 'pending', 'sources': []}
        apply_recipe_applicability([identity, invalid], review(), ROOT)
        assert invalid['dimensions']['recipe_eligibility']['state'] == 'pending'
    for catalog_ids, discovery in (([], 'reviewed'), (['unique1'], 'blocked')):
        invalid_identity = deepcopy(identity)
        invalid_identity['catalog_ids'] = catalog_ids
        invalid_identity['dimensions']['discovery']['state'] = discovery
        candidate = deepcopy(evidence)
        candidate['dimensions']['recipe_eligibility'] = {'state': 'pending', 'sources': []}
        apply_recipe_applicability([invalid_identity, candidate], review(), ROOT)
        assert candidate['dimensions']['recipe_eligibility']['state'] == 'pending'
