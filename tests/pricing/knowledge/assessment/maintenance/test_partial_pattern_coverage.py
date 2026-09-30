"""A useful preparation base does not finish its source's inserted-item branch."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory, fingerprint
from pricing.knowledge.assessment.maintenance.review_dossiers import _pattern_bindings, compile_dossiers
from tests.pricing.knowledge.assessment.maintenance.test_pattern_dossiers import pattern_fixture


def inputs():
    role, use, row = pattern_fixture()
    role['must'] = {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'}
    use['profile_fingerprint'] = fingerprint(role)
    use['source_coverage'] = {'kind': 'preparation_only', 'remaining_branches': ['Assess the finished socket payload.']}
    return role, use, row


def test_partial_source_keeps_base_demand_but_not_complete_source_coverage():
    role, use, row = inputs()
    inventory = compile_inventory([row], [role], {})
    entry = compile_dossiers(inventory, [role], [use])['identities'][0]
    assert entry['demand']['distinct_builds'] == 1
    assert entry['pattern_review_profile_ids'] == [role['id']]
    assert entry['reviewed_pattern_occurrence_ids'] == []
    assert entry['partial_pattern_reviews'][0]['occurrence_ids'] == ['one']
    assert entry['partial_pattern_reviews'][0]['remaining_branches'] == ['Assess the finished socket payload.']
    assert _pattern_bindings([row], [use], {role['id']: role}) == []


@pytest.mark.parametrize('change', ['empty-branches', 'blank-branch', 'unknown-kind', 'not-pattern', 'filled-role'])
def test_partial_source_metadata_must_describe_a_real_preparation_rule(change):
    role, use, _ = inputs()
    if change == 'empty-branches':
        use['source_coverage']['remaining_branches'] = []
    elif change == 'blank-branch':
        use['source_coverage']['remaining_branches'] = [' ']
    elif change == 'unknown-kind':
        use['source_coverage']['kind'] = 'finished'
    elif change == 'not-pattern':
        use.pop('pattern')
        use.pop('pattern_label')
        use['item'] = 'Named'
        role['names'] = ['Named']
    else:
        role['must']['value'] = 'filled'
    use['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source coverage'):
        compile_demand([use], [role])


def test_actual_complete_pattern_is_not_reclassified_by_empty_socket_predicate():
    role, use, row = inputs()
    use = deepcopy(use)
    del use['source_coverage']
    inv = compile_inventory([row], [role], {})
    assert compile_dossiers(inv, [role], [use])['identities'][0]['reviewed_pattern_occurrence_ids'] == ['one']


def test_repeated_source_context_cannot_erase_a_partial_configuration(tmp_path):
    from tests.pricing.knowledge.assessment.maintenance.test_pattern_source_context import pattern_setup, run

    role, occurrence, doc, use = pattern_setup(tmp_path)
    role['must'] = {'all': [role['must'], {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'}]}
    use['source_coverage'] = {'kind': 'preparation_only', 'remaining_branches': ['Verify the filled payload.']}
    use['profile_fingerprint'] = fingerprint(role)
    doc['rows'][0]['branches'][0]['profile_fingerprint'] = fingerprint(role)
    result = run(tmp_path, role, occurrence, doc, use)
    assert result[0]['state'] == 'pending'
    assert result[0]['remaining_branches'] == ['Verify the filled payload.']


@pytest.mark.parametrize('value', [None, {}, [], 'partial'])
def test_present_partial_metadata_cannot_be_null_or_malformed(value):
    role, use, _ = inputs()
    use['source_coverage'] = value
    with pytest.raises(ValueError, match='source coverage'):
        compile_demand([use], [role])


def test_separately_reviewed_finished_rule_can_complete_the_same_source():
    role, use, row = inputs()
    filled = deepcopy(role)
    filled['id'] = role['id'] + '-filled'
    filled['must']['value'] = 'filled'
    finished_use = deepcopy(use)
    finished_use.pop('source_coverage')
    finished_use.update(profile_id=filled['id'], pattern=filled['id'], profile_fingerprint=fingerprint(filled))
    inventory = compile_inventory([row], [role, filled], {})
    entry = compile_dossiers(inventory, [role, filled], [use, finished_use])['identities'][0]
    assert entry['reviewed_pattern_occurrence_ids'] == ['one']
    assert entry['partial_pattern_reviews'][0]['profile_id'] == role['id']
    assert entry['demand']['distinct_builds'] == 1
