"""Reviewed empty slots must not become items; uncertain or mixed sources stay open."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.coverage_matrix import DIMENSIONS


SOURCE = 'pricing/data/wp-a-builds.json'


def inputs(tmp_path):
    path = tmp_path / SOURCE
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {'fissure-druid': {'merc': {'Shield': {'early': ['N/A'], 'mid': ['N/A'], 'end': ['Spirit Monarch']}}}}
        )
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    occurrences = [
        {
            'id': stage,
            'identity_id': 'empty',
            'name': 'N/A',
            'original_label': 'N/A',
            'category': None,
            'kind': 'demand',
            'source_id': SOURCE,
            'source_locator': f'/fissure-druid/merc/Shield/{stage}/0',
            'build': 'fissure-druid',
            'side': 'merc',
            'slot': 'Shield',
            'variant': stage,
            'source_status': 'verified',
            'identity_status': 'unresolved',
        }
        for stage in ('early', 'mid')
    ]
    inventory = {
        'identities': [
            {
                'id': 'empty',
                'name': 'N/A',
                'category': 'unresolved',
                'catalog_ids': [],
                'occurrence_ids': ['early', 'mid'],
            }
        ],
        'occurrences': occurrences,
        'sources': [{'id': SOURCE, 'path': SOURCE, 'sha256': digest, 'actual_sha256': digest, 'status': 'verified'}],
        'source_conflicts': [],
        'planner_source_gaps': [],
    }
    matrix = {
        'rows': [
            {
                'id': 'identity:empty',
                'kind': 'identity',
                'name': 'N/A',
                'category': 'unresolved',
                'catalog_ids': [],
                'dimensions': {d: {'state': 'pending', 'reason': 'Unresolved'} for d in DIMENSIONS},
            }
        ]
    }
    return matrix, inventory


def test_source_checked_empty_shields_are_accounted_without_item_assessment(tmp_path):
    matrix, inventory = inputs(tmp_path)
    result = compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)
    queue = {r['id'] for r in result['queue']}
    assert not any(key.startswith(('identity:empty/', 'occurrence:')) for key in queue)
    assert {r['id'] for r in result['non_item_identity_dispositions']} == {'empty'}
    assert {r['id'] for r in result['occurrence_dispositions']} == {'early', 'mid'}
    assert 'final:verification' in queue
    assert not result['complete']
    assert inventory['identities'][0]['occurrence_ids'] == ['early', 'mid']


@pytest.mark.parametrize('mutation', ['narrative', 'real-label', 'unverified', 'different-slot', 'different-build'])
def test_unreviewed_neighbor_preserves_identity_work(tmp_path, mutation):
    matrix, inventory = inputs(tmp_path)
    row = inventory['occurrences'][0]
    if mutation == 'narrative':
        row['source_locator'] = '/fissure-druid/notes/0'
    elif mutation == 'real-label':
        row['original_label'] = 'N/A or Spirit Monarch'
    elif mutation == 'unverified':
        row['source_status'] = 'changed'
    elif mutation == 'different-slot':
        row['slot'] = 'Weapon'
    else:
        row['build'] = 'other-build'
    result = compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)
    queue = {r['id'] for r in result['queue']}
    assert 'identity:empty/discovery' in queue
    assert 'occurrence:early' in queue


def test_catalog_identity_cannot_be_excluded_as_a_placeholder(tmp_path):
    matrix, inventory = inputs(tmp_path)
    inventory['identities'][0].update(category='unique', catalog_ids=['unique1'])
    result = compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)
    assert 'identity:empty/discovery' in {r['id'] for r in result['queue']}


@pytest.mark.parametrize('mutation', ['bytes', 'hash', 'missing'])
def test_stale_empty_slot_evidence_cannot_close_work(tmp_path, mutation):
    matrix, inventory = inputs(tmp_path)
    if mutation == 'bytes':
        (tmp_path / SOURCE).write_text('{}')
    elif mutation == 'hash':
        inventory['sources'][0]['sha256'] = 'incorrect'
    else:
        (tmp_path / SOURCE).unlink()
    with pytest.raises(ValueError, match='empty-slot source'):
        compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)


def test_missing_or_conflicting_identity_links_do_not_close_work(tmp_path):
    matrix, inventory = inputs(tmp_path)
    original = deepcopy(inventory)
    for links in ([], ['early'], ['early', 'mid', 'missing']):
        inventory = deepcopy(original)
        inventory['identities'][0]['occurrence_ids'] = links
        result = compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)
        assert 'identity:empty/discovery' in {r['id'] for r in result['queue']}


def test_changed_source_cell_is_not_hidden_by_refreshed_source_hash(tmp_path):
    matrix, inventory = inputs(tmp_path)
    path = tmp_path / SOURCE
    document = json.loads(path.read_text())
    document['fissure-druid']['merc']['Shield']['early'][0] = 'Spirit Monarch'
    path.write_text(json.dumps(document))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory['sources'][0].update(sha256=digest, actual_sha256=digest)
    with pytest.raises(ValueError, match='empty-slot source'):
        compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)


def test_non_item_review_cannot_hide_conflicting_matrix_identity(tmp_path):
    matrix, inventory = inputs(tmp_path)
    matrix['rows'][0]['catalog_ids'] = ['unique1']
    with pytest.raises(ValueError, match='conflicting coverage row'):
        compile_completion(matrix, inventory, {'complete': True}, source_root=tmp_path)
