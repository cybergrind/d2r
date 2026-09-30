"""A reviewed carried Cube token cannot discharge neighboring equipment or identity work."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.carried_cube_reviews import (
    compile_carried_cube_reviews,
    occurrence_fingerprint,
)
from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.coverage_matrix import DIMENSIONS


NATIVE = 'third-parties/d2data/json/misc.json'
PLANNER = 'pricing/raw/mr/planners/abc123.json'


def fixture(tmp_path):
    documents = {
        NATIVE: {
            'box': {
                'name': 'Horadric Cube',
                'code': 'box',
                'type': 'ques',
                'quest': 10,
                'useable': 1,
                'gemsockets': 0,
                'spelldescstr': 'OpenHoradricCube',
            }
        },
        PLANNER: {'data': json.dumps({'profiles': [{'name': 'Test', 'inventory': ['box']}], 'items': {}})},
    }
    inputs = {}
    for name, doc in documents.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        inputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    row = {
        'id': 'cube',
        'identity_id': 'cube-identity',
        'name': 'Horadric Cube',
        'original_label': 'Horadric Cube',
        'kind': 'demand',
        'category': 'misc',
        'base_code': 'box',
        'side': 'player',
        'slot': '0',
        'source_id': PLANNER,
        'source_locator': '/profiles/0/inventory/0',
        'source_status': 'verified',
        'identity_status': 'resolved',
        'details': {
            'base': 'box',
            'item_ref': 'box',
            'canonical_id': 'box',
            'container': 'inventory',
            'role': 'inventory',
        },
    }
    inventory = {
        'occurrences': [row],
        'identities': [{'id': 'cube-identity', 'name': 'Horadric Cube', 'category': 'misc'}],
        'sources': [
            {
                'id': PLANNER,
                'path': PLANNER,
                'status': 'verified',
                'sha256': inputs[PLANNER],
                'actual_sha256': inputs[PLANNER],
            }
        ],
    }
    review = {
        'schema_version': 1,
        'scope': 'carried_horadric_cube_only',
        'inputs': inputs,
        'rows': [
            {
                'occurrence_id': 'cube',
                'occurrence_sha256': occurrence_fingerprint(row),
                'reviewed_at': '2026-09-30',
                'reason': 'Native usable Cube carried in inventory; no equipment or socket use is asserted.',
            }
        ],
    }
    return inventory, review


def test_exact_carried_cube_review_preserves_identity_and_final_work(tmp_path):
    inventory, review = fixture(tmp_path)
    original = deepcopy(inventory)
    result = compile_carried_cube_reviews(review, inventory, tmp_path)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['occurrence_id'] == 'cube'
    matrix = {
        'rows': [
            {
                'id': 'identity:cube-identity',
                'kind': 'identity',
                'category': 'misc',
                'dimensions': {d: {'state': 'pending', 'reason': 'Still needs review'} for d in DIMENSIONS},
            }
        ]
    }
    completed = compile_completion(
        matrix, inventory, {'complete': True}, source_root=tmp_path, carried_cube_reviews=review
    )
    ids = {r['id'] for r in completed['queue']}
    assert 'occurrence:cube' not in ids
    assert 'identity:cube-identity/discovery' in ids
    assert 'final:verification' in ids
    assert not completed['complete']
    assert inventory == original


@pytest.mark.parametrize('mutation', ['side', 'slot', 'label', 'base', 'container', 'locator', 'status', 'identity'])
def test_rehashed_unsupported_context_cannot_be_reviewed(tmp_path, mutation):
    inventory, review = fixture(tmp_path)
    row = inventory['occurrences'][0]
    if mutation == 'container':
        row['details']['container'] = 'equipped'
    else:
        key, value = {
            'side': ('side', 'merc'),
            'slot': ('slot', 'head'),
            'label': ('original_label', 'Cube with item'),
            'base': ('base_code', 'other'),
            'locator': ('source_locator', '/profiles/0/equipment/0'),
            'status': ('source_status', 'changed'),
            'identity': ('identity_status', 'unresolved'),
        }[mutation]
        row[key] = value
    review['rows'][0]['occurrence_sha256'] = occurrence_fingerprint(row)
    with pytest.raises(ValueError, match=r'Cube|Planner'):
        compile_carried_cube_reviews(review, inventory, tmp_path)


@pytest.mark.parametrize('failure', ['stale', 'missing', 'decorated', 'native', 'duplicate', 'changed-occurrence'])
def test_source_and_occurrence_proof_is_required(tmp_path, failure):
    inventory, review = fixture(tmp_path)
    path = tmp_path / PLANNER
    if failure == 'stale':
        path.write_text('{}')
    elif failure == 'missing':
        path.unlink()
    elif failure == 'decorated':
        path.write_text(json.dumps({'profiles': [{'inventory': [{'base': 'box', 'stats': {'bonus': 1}}]}]}))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        review['inputs'][PLANNER] = digest
        inventory['sources'][0].update(sha256=digest, actual_sha256=digest)
    elif failure == 'native':
        (tmp_path / NATIVE).write_text('{}')
    elif failure == 'duplicate':
        review['rows'].append(deepcopy(review['rows'][0]))
    else:
        inventory['occurrences'][0]['variant'] = 'Changed'
    with pytest.raises(ValueError, match=r'Cube|Planner'):
        compile_carried_cube_reviews(review, inventory, tmp_path)


def test_unreviewed_neighbor_and_narrative_remain_required(tmp_path):
    inventory, review = fixture(tmp_path)
    for name, locator in [('neighbor', '/profiles/0/inventory/1'), ('narrative', '/guide/item-span/0')]:
        row = deepcopy(inventory['occurrences'][0])
        row.update(id=name, source_locator=locator)
        inventory['occurrences'].append(row)
    result = compile_completion(
        {'rows': []}, inventory, {'complete': True}, source_root=tmp_path, carried_cube_reviews=review
    )
    ids = {row['id'] for row in result['queue']}
    assert 'occurrence:cube' not in ids
    assert {'occurrence:neighbor', 'occurrence:narrative', 'identity:cube-identity'} <= ids


@pytest.mark.parametrize('mutation', ['missing-identity', 'wrong-identity', 'duplicate-source', 'unpin', 'path-escape'])
def test_inventory_binding_is_required(tmp_path, mutation):
    inventory, review = fixture(tmp_path)
    if mutation == 'missing-identity':
        inventory['identities'] = []
    elif mutation == 'wrong-identity':
        inventory['identities'][0]['name'] = 'Other'
    elif mutation == 'duplicate-source':
        inventory['sources'].append(deepcopy(inventory['sources'][0]))
    elif mutation == 'unpin':
        del review['inputs'][PLANNER]
    else:
        inventory['occurrences'][0]['source_id'] = '../outside.json'
        review['rows'][0]['occurrence_sha256'] = occurrence_fingerprint(inventory['occurrences'][0])
    with pytest.raises(ValueError, match='Cube'):
        compile_carried_cube_reviews(review, inventory, tmp_path)
