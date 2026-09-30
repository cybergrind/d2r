"""A scope flag cannot replace exhaustive, current and conservative membership."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs


POLICY = {
    'schema_version': 1,
    'scope': 'non_ladder_value_and_exceptional_leveling',
    'migration_status': 'complete',
    'uses': [],
    'dimensions': [],
}


def test_migration_flag_alone_cannot_close_scope_gate():
    matrix, inventory = inputs()
    result = compile_completion(matrix, inventory, {'complete': True}, value_scope=POLICY)
    assert 'scope:value-migration' in {r['id'] for r in result['queue']}


def test_validated_manifest_closes_only_scope_migration_gate():
    matrix, inventory = inputs()
    before = compile_completion(matrix, inventory, {'complete': True}, value_scope=POLICY)
    manifest = before['scope_manifest']
    assert {r['id'] for r in manifest['members']} == {'identity:a', 'occurrence:o'}
    assert all(r['state'] == 'retained' for r in manifest['members'])
    after = compile_completion(matrix, inventory, {'complete': True}, value_scope=POLICY, value_manifest=manifest)
    assert {r['id'] for r in before['queue']} - {r['id'] for r in after['queue']} == {'scope:value-migration'}
    assert not after['complete']
    assert before['scope'] != after['scope']


@pytest.mark.parametrize('change', ['remove', 'exclude', 'new-identity', 'source-changed', 'policy-changed'])
def test_manifest_cannot_hide_missing_or_changed_members(change):
    matrix, inventory = inputs()
    policy = deepcopy(POLICY)
    manifest = compile_completion(matrix, inventory, {'complete': True}, value_scope=policy)['scope_manifest']
    if change == 'remove':
        manifest['members'].pop()
    elif change == 'exclude':
        manifest['members'][0]['state'] = 'excluded'
    elif change == 'new-identity':
        inventory['identities'].append({'id': 'valuable-new'})
    elif change == 'source-changed':
        inventory['occurrences'][0]['details'] = {'new_configuration': True}
    else:
        policy['reviewed_at'] = 'different-policy-revision'
    result = compile_completion(matrix, inventory, {'complete': True}, value_scope=policy, value_manifest=manifest)
    assert 'scope:value-migration' in {r['id'] for r in result['queue']}


def test_mixed_configuration_and_historical_unknown_demand_are_retained():
    from pricing.knowledge.assessment.maintenance.value_scope_manifest import build_manifest

    profiles = [
        {'id': 'starter', 'qualities': ['normal']},
        {'id': 'valuable', 'qualities': ['normal']},
    ]
    inventory = {
        'identities': [{'id': 'item'}],
        'occurrences': [{'id': 'historic', 'details': {'historical': True, 'recommended': False}}],
        'configurations': [
            {'id': 'shared', 'profile_ids': ['starter', 'valuable']},
            {'id': 'starter-only', 'profile_ids': ['starter']},
        ],
    }
    excluded = {'use:starter:normal': {'state': 'excluded', 'reason': 'Reviewed generic leveling use.'}}
    result = build_manifest(
        inventory,
        profiles,
        {'rows': [{'id': 'base:normal'}]},
        POLICY,
        excluded_uses=excluded,
        excluded_occurrences={},
        non_item_identities={},
    )
    states = {r['id']: r['state'] for r in result['members']}
    assert states == {
        'identity:item': 'retained',
        'occurrence:historic': 'retained',
        'configuration:shared': 'retained',
        'configuration:starter-only': 'excluded',
        'use:starter:normal': 'excluded',
        'use:valuable:normal': 'retained',
        'base:base:normal': 'retained',
    }


def test_saved_capture_and_evidence_rows_are_scope_members_too():
    matrix, inventory = inputs()
    matrix['rows'].extend(
        [
            {'id': 'capture:unsupported', 'kind': 'observed_capture', 'dimensions': {}},
            {'id': 'evidence:market-gap', 'kind': 'evidence', 'dimensions': {}},
        ]
    )
    result = compile_completion(matrix, inventory, {'complete': True}, value_scope=POLICY)
    members = {row['id']: row for row in result['scope_manifest']['members']}
    assert members['capture:unsupported']['state'] == 'retained'
    assert members['evidence:market-gap']['state'] == 'retained'
