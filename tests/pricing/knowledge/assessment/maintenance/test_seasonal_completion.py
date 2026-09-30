"""Known definition ambiguity must survive an otherwise reviewed completion scope."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.seasonal_named_audit import BASE, OVERLAY, build
from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs


def native_sources(root):
    ordinary = {'121': {'*ID': 121, 'index': 'Manald Heal', 'code': 'rin', 'prop1': 'regen-mana', 'min1': 20}}
    seasonal = deepcopy(ordinary)
    seasonal['121'].update(firstLadderSeason=15, prop2='cast2', min2=10, max2=10)
    for name, data in ((BASE, ordinary), (OVERLAY, seasonal)):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    return build(root)


def compile_audit(root, document):
    matrix, inventory = inputs()
    return compile_completion(matrix, inventory, {'complete': True}, seasonal_audit=document, source_root=root)


def test_conflicts_are_required_non_ladder_correctness_work(tmp_path):
    result = compile_audit(tmp_path, native_sources(tmp_path))
    task = next(row for row in result['queue'] if row['id'] == 'seasonal_definition:121')
    assert task['dimension'] == 'source_review'
    assert task['state'] == 'pending'
    assert 'Manald Heal' in task['reason']
    assert 'Non-Ladder' in task['reason']
    assert not result['complete']


def test_real_definition_scope_requires_the_audit():
    matrix, inventory = inputs()
    inventory['sources'] = [{'path': 'pricing/data/appraisal-definitions.json'}]
    result = compile_completion(matrix, inventory, {'complete': True})
    assert any(row['id'] == 'seasonal_definition:missing' and row['state'] == 'blocked' for row in result['queue'])


@pytest.mark.parametrize('mutation', ['removed', 'state', 'new_source', 'complete_flag'])
def test_forged_or_stale_audit_cannot_close_definition_work(tmp_path, mutation):
    document = native_sources(tmp_path)
    if mutation == 'removed':
        document['rows'].clear()
    elif mutation == 'state':
        document['rows'][0]['state'] = 'reviewed'
    elif mutation == 'complete_flag':
        document['complete'] = True
    else:
        path = tmp_path / OVERLAY
        value = json.loads(path.read_text())
        value['121']['min2'] = 11
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='seasonal definition audit'):
        compile_audit(tmp_path, document)


def test_identical_definitions_do_not_create_phantom_conflicts(tmp_path):
    native_sources(tmp_path)
    (tmp_path / OVERLAY).write_bytes((tmp_path / BASE).read_bytes())
    result = compile_audit(tmp_path, build(tmp_path))
    assert not any(row['id'].startswith('seasonal_definition:') for row in result['queue'])


def test_definition_conflicts_are_members_of_the_scope_manifest(tmp_path):
    from pricing.knowledge.assessment.maintenance.value_scope import SCOPE

    matrix, inventory = inputs()
    result = compile_completion(
        matrix,
        inventory,
        {'complete': True},
        seasonal_audit=native_sources(tmp_path),
        source_root=tmp_path,
        value_scope={'schema_version': 1, 'scope': SCOPE, 'uses': [], 'migration_status': 'partial'},
    )
    member = next(row for row in result['scope_manifest']['members'] if row['id'] == 'seasonal_definition:121')
    assert member['kind'] == 'definition_conflict'
    assert member['state'] == 'retained'
    assert member['exclusion'] is None
