"""Pinned evidence for embedded uses cannot drift into another item or set."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


def evidence(tmp_path, slot='Helmets'):
    html = (
        f'<h2>Gear Options</h2><table><tr><td>{slot}</td><td>'
        '<span class="d2-planner-tooltip" data-d2-id="p" data-d2-set-id="s" '
        'data-d2-item-id="143"></span></td></tr></table>'
    )
    item = {'base': 'ci3', 'quality': 4, 'sockets': 2, 'socketedItems': ['135', 'r24']}
    planner = {
        'items': {'143': item, '135': {'base': 'jew', 'stats': {'resist': 15}}},
        'profiles': [{'uid': 's', 'name': 'embeds', 'inventory': []}],
    }

    def save(path, content):
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode()
        file.write_bytes(raw)
        return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}

    guide = save('guide.html', html)
    source = save('pricing/raw/mr/planners/p.json', json.dumps({'data': json.dumps({'planner': planner})}))
    reference = section_inventory(html)['embedded_item_refs'][0]
    return {
        'guide': guide,
        'planner': source,
        'reference': reference,
        'expected_context': {'span_index': 0, 'label': '', 'side': 'player', 'slot': slot, 'reference': reference},
        'item_fingerprint': fingerprint(item),
    }


def test_embedded_evidence_preserves_definition_only_item_and_actual_children(tmp_path):
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    row = evidence(tmp_path)
    result = validate_embedded_evidence(row, tmp_path)
    assert result['context']['slot'] == 'Helmets'
    assert result['profile_locator'] == '/profiles/0'
    assert result['item']['socketedItems'] == ['135', 'r24']
    assert result['socket_definitions'] == {'135': {'base': 'jew', 'stats': {'resist': 15}}}
    assert 'review_state' not in result  # Evidence resolution does not approve semantics.


@pytest.mark.parametrize('change', ['hash', 'path', 'context', 'item', 'reference', 'set'])
def test_embedded_evidence_rejects_drift_and_substitution(tmp_path, change):
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    row = deepcopy(evidence(tmp_path))
    if change == 'hash':
        row['planner']['sha256'] = '0' * 64
    elif change == 'path':
        row['planner']['path'] = 'guide.html'
    elif change == 'context':
        row['expected_context']['slot'] = 'Body Armors'
    elif change == 'item':
        row['item_fingerprint'] = '0' * 64
    elif change == 'reference':
        row['reference']['item_id'] = '135'
    else:
        row['reference']['set_id'] = 'other'
    with pytest.raises(ValueError, match=r'[Ee]mbedded'):
        validate_embedded_evidence(row, tmp_path)


@pytest.mark.parametrize('change', ['missing_child', 'cycle', 'bad_children', 'bad_reference', 'duplicate_set'])
def test_embedded_evidence_rejects_invalid_graph_even_with_fresh_hash(tmp_path, change):
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    row = evidence(tmp_path)
    path = tmp_path / row['planner']['path']
    planner = json.loads(json.loads(path.read_text())['data'])['planner']
    if change == 'missing_child':
        del planner['items']['135']
    elif change == 'cycle':
        planner['items']['135']['socketedItems'] = ['143']
    elif change == 'bad_children':
        planner['items']['135']['socketedItems'] = {'0': 'r24'}
    elif change == 'bad_reference':
        planner['items']['135']['socketedItems'] = [True]
    else:
        planner['profiles'].append(deepcopy(planner['profiles'][0]))
    raw = json.dumps(planner).encode()
    path.write_bytes(raw)
    row['planner']['sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match=r'[Ee]mbedded'):
        validate_embedded_evidence(row, tmp_path)
