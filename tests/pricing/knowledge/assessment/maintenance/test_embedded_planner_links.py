"""Copied planner IDs may share reviewed semantics only when complete definitions agree."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_planner_links import compile_embedded_planner_links
from pricing.knowledge.assessment.maintenance.embedded_reviews import embedded_identity
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_occurrence_links import example as table_example


EMBEDDED = 'pricing/knowledge/assessment/rules/embedded_reviews.json'
GAME = 'pricing/raw/mr/planners/game-data.json'
GUIDE = 'pricing/raw/mr/guides__example.html'


def example(root):
    document, table, _, inventory = table_example(root)
    planner_path = table['rows'][0]['planner_endorsement']['planner']['path']
    planner = json.loads((root / planner_path).read_bytes())
    item = planner['items']['5']
    item['quality'] = 7
    planner['items']['6'] = deepcopy(item)
    planner['profiles'][0].update(name='Standard', uid='uid', mercItems={'head': 6}, merc='6', **{'class': 'war'})
    del planner['profiles'][0]['items']
    for row in inventory['occurrences']:
        row.update(
            side='merc', variant='Standard', source_locator=row['source_locator'].replace('/items/', '/mercItems/')
        )
    parent = inventory['occurrences'][0]
    parent.update(name='Cure', original_label='Cure', category='runeword')
    parent['details'].update(item, container='mercItems', role='mercItems')
    inventory['identities'][0].update(name='Cure', category='runeword')
    role = {
        'id': 'role',
        'build': 'example',
        'variant': 'Standard',
        'side': 'merc',
        'slot': 'Helmet',
        'names': ['Cure'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'},
                {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Prayer'},
            ]
        },
    }
    html = (
        '<div class="_tabsV2_test"><div class="_header_test">Standard</div><div class="_tab_test">'
        '<p>Use Prayer.</p><div class="d2-player" data-d2-id="example" data-d2-set-id="uid"></div></div></div>'
    )
    guide_pin = {'path': GUIDE, 'sha256': hashlib.sha256(html.encode()).hexdigest()}
    evidence = {
        'guide': guide_pin,
        'planner': {'path': planner_path, 'sha256': hashlib.sha256(json.dumps(planner).encode()).hexdigest()},
        'reference': {'profile_id': 'example', 'set_id': 'uid', 'item_id': '5'},
        'item_fingerprint': fingerprint(item),
    }
    review = {
        'kind': 'echoing_cure',
        'profile_id': 'role',
        'profile_fingerprint': fingerprint(role),
        'evidence': evidence,
    }
    identity = embedded_identity({'source_id': GUIDE, 'reference': evidence['reference']})
    embedded = {'schema_version': 1, 'rows': [review]}
    sources = {
        planner_path: planner,
        EMBEDDED: embedded,
        GAME: {'hireling': {'6': [{'act': 2, 'skill2': 99}]}, 'skills': {'99': {'skill': 'Prayer'}}},
        GUIDE: html,
    }
    for name, value in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        document['inputs'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory['sources'][0].update(
        sha256=document['inputs'][planner_path], actual_sha256=document['inputs'][planner_path]
    )
    document['rows'] = [
        {
            'endorsement_occurrence_id': identity,
            'endorsement_sha256': fingerprint(review),
            'profile_index': 0,
            'quote': 'Use Prayer.',
            'parent': {'occurrence_id': 'parent', 'sha256': fingerprint(parent)},
            'children': [{'occurrence_id': 'child', 'sha256': fingerprint(inventory['occurrences'][1])}],
            'reviewed_at': '2026-09-30',
            'reason': 'Exact copied Cure definition, independently bound to selected mercenary.',
        }
    ]
    proofs = [{'id': identity, 'state': 'reviewed', 'profile_id': 'role'}]
    return document, embedded, proofs, inventory, [role]


def test_identical_copy_keeps_selected_parent_context(tmp_path):
    args = example(tmp_path)
    result = compile_embedded_planner_links(*args, tmp_path)
    assert [r['occurrence_id'] for r in result] == ['parent', 'child']
    assert all(r['profile_id'] == 'role' for r in result)


@pytest.mark.parametrize(
    'failure',
    [
        'changed-copy',
        'wrong-merc',
        'wrong-class',
        'wrong-tab',
        'wrong-uid',
        'unreviewed',
        'excluded',
        'unsupported-kind',
        'changed-role',
    ],
)
def test_copy_cannot_borrow_other_item_or_wearer(tmp_path, failure):
    document, embedded, proof, inventory, profiles = example(tmp_path)
    if failure in {'unreviewed', 'excluded'}:
        proof[0]['state'] = 'pending' if failure == 'unreviewed' else 'excluded'
    elif failure == 'changed-role':
        profiles[0]['names'] = ['Other']
    elif failure == 'unsupported-kind':
        embedded['rows'][0]['kind'] = 'equipment'
        (tmp_path / EMBEDDED).write_text(json.dumps(embedded))
        document['inputs'][EMBEDDED] = hashlib.sha256((tmp_path / EMBEDDED).read_bytes()).hexdigest()
        document['rows'][0]['endorsement_sha256'] = fingerprint(embedded['rows'][0])
    elif failure == 'wrong-tab':
        document['rows'][0]['quote'] = 'Different instruction.'
    else:
        pin = embedded['rows'][0]['evidence']['planner']
        path = tmp_path / pin['path']
        data = json.loads(path.read_bytes())
        if failure == 'changed-copy':
            data['items']['6']['defense'] = 999
        else:
            data['profiles'][0][{'wrong-merc': 'merc', 'wrong-class': 'class', 'wrong-uid': 'uid'}[failure]] = 'other'
        path.write_text(json.dumps(data))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document['inputs'][pin['path']] = pin['sha256'] = digest
        inventory['sources'][0].update(sha256=digest, actual_sha256=digest)
        (tmp_path / EMBEDDED).write_text(json.dumps(embedded))
        document['inputs'][EMBEDDED] = hashlib.sha256((tmp_path / EMBEDDED).read_bytes()).hexdigest()
        document['rows'][0]['endorsement_sha256'] = fingerprint(embedded['rows'][0])
    with pytest.raises(ValueError, match='Embedded planner'):
        compile_embedded_planner_links(document, embedded, proof, inventory, profiles, tmp_path)
