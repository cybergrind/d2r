"""A validated equipment endorsement can cover only its exact parent and rune payload."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_planner_occurrence_links


PLANNER = 'pricing/raw/mr/planners/example.json'
TABLE = 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json'
NATIVE = 'third-parties/d2data/json/misc.json'


def example(root):
    item = {'base': 'test-base', 'unique': 'test-unique', 'quality': 6, 'sockets': 1, 'socketedItems': ['test-rune']}
    planner = {'items': {'5': item}, 'profiles': [{'name': 'Endgame', 'uid': 'uid', 'items': {'head': 5}}]}
    table = {
        'schema_version': 1,
        'rows': [
            {
                'occurrence_id': 'guide',
                'profile_id': 'role',
                'canonical_name': 'Test Unique',
                'planner_endorsement': {
                    'coverage': 'player_rune_socket_component',
                    'planner': {'path': PLANNER, 'sha256': hashlib.sha256(json.dumps(planner).encode()).hexdigest()},
                    'profile_index': 0,
                    'profile_name': 'Endgame',
                    'profile_uid': 'uid',
                    'slot': 'head',
                    'item_id': '5',
                    'expected_item': item,
                },
            }
        ],
    }
    sources = {
        PLANNER: planner,
        TABLE: table,
        NATIVE: {'test-rune': {'name': 'Test Rune', 'code': 'test-rune', 'type': 'rune'}},
    }
    inputs = {}
    for name, document in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document))
        inputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    common = {
        'kind': 'demand',
        'source_id': PLANNER,
        'source_status': 'verified',
        'identity_status': 'resolved',
        'side': 'player',
        'slot': 'head',
        'variant': 'Endgame',
    }
    parent = {
        **common,
        'id': 'parent',
        'identity_id': 'unique',
        'name': 'Test Unique',
        'original_label': 'Test Unique',
        'category': 'unique',
        'base_code': 'test-base',
        'source_locator': '/profiles/0/items/head',
        'details': {**item, 'role': 'items', 'container': 'items', 'canonical_id': 'test-unique'},
    }
    child = {
        **common,
        'id': 'child',
        'identity_id': 'rune',
        'name': 'Test Rune',
        'original_label': 'Test Rune',
        'category': 'misc',
        'base_code': 'test-rune',
        'source_locator': '/profiles/0/items/head/socketedItems/0',
        'details': {
            'base': 'test-rune',
            'canonical_id': 'test-rune',
            'role': 'socket_filler',
            'container': 'socketedItems',
        },
    }
    inventory = {
        'occurrences': [parent, child],
        'identities': [
            {'id': 'unique', 'name': 'Test Unique', 'category': 'unique'},
            {'id': 'rune', 'name': 'Test Rune', 'category': 'misc'},
        ],
        'sources': [
            {
                'id': PLANNER,
                'path': PLANNER,
                'sha256': inputs[PLANNER],
                'actual_sha256': inputs[PLANNER],
                'status': 'verified',
            }
        ],
    }
    proof = [{'occurrence_id': 'guide', 'profile_id': 'role', 'state': 'reviewed'}]
    link = {
        'endorsement_occurrence_id': 'guide',
        'endorsement_sha256': fingerprint(table['rows'][0]),
        'parent': {'occurrence_id': 'parent', 'sha256': fingerprint(parent)},
        'children': [{'occurrence_id': 'child', 'sha256': fingerprint(child)}],
        'reviewed_at': '2026-09-30',
        'reason': 'Reviewed exact equipment and complete rune payload.',
    }
    document = {'schema_version': 1, 'inputs': inputs, 'rows': [link]}
    return document, table, proof, inventory


def test_links_only_exact_parent_and_complete_payload(tmp_path):
    document, table, proof, inventory = example(tmp_path)
    before = deepcopy(inventory)
    result = compile_planner_occurrence_links(document, table, proof, inventory, tmp_path)
    assert [r['occurrence_id'] for r in result] == ['parent', 'child']
    assert all(r['state'] == 'reviewed' and r['profile_id'] == 'role' for r in result)
    assert inventory == before


@pytest.mark.parametrize(
    'failure',
    [
        'unreviewed',
        'wrong-role',
        'stale',
        'missing',
        'neighbor',
        'payload',
        'duplicate',
        'partial-review',
        'missing-child',
        'changed-identity',
    ],
)
def test_links_cannot_borrow_or_expand_endorsement(tmp_path, failure):
    document, table, proof, inventory = example(tmp_path)
    if failure == 'unreviewed':
        proof[0]['state'] = 'pending'
    elif failure == 'wrong-role':
        proof[0]['profile_id'] = 'other'
    elif failure == 'stale':
        (tmp_path / PLANNER).write_text('{}')
    elif failure == 'missing':
        (tmp_path / PLANNER).unlink()
    elif failure == 'duplicate':
        document['rows'].append(deepcopy(document['rows'][0]))
    elif failure == 'missing-child':
        document['rows'][0]['children'] = []
    elif failure == 'changed-identity':
        inventory['identities'][1]['name'] = 'Different Rune'
    elif failure == 'partial-review':
        table['rows'][0]['planner_endorsement']['coverage'] = 'intrinsic_component'
        path = tmp_path / TABLE
        path.write_text(json.dumps(table))
        document['inputs'][TABLE] = hashlib.sha256(path.read_bytes()).hexdigest()
        document['rows'][0]['endorsement_sha256'] = fingerprint(table['rows'][0])
    else:
        child = inventory['occurrences'][1]
        child['source_locator' if failure == 'neighbor' else 'base_code'] = 'other'
        document['rows'][0]['children'][0]['sha256'] = fingerprint(child)
    with pytest.raises(ValueError, match='Planner link'):
        compile_planner_occurrence_links(document, table, proof, inventory, tmp_path)
