"""A repeated planner item in prose can reuse its reviewed equipment configuration."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from tests.pricing.knowledge.assessment.maintenance.test_player_source_context import run, setup as player_setup


def setup(root):
    role, occurrence, doc = player_setup(root)
    gid = occurrence['source_id']
    raw = root / gid
    raw.parent.mkdir(parents=True, exist_ok=True)
    tag = '<span class="d2planner-item" data-d2planner-profile="planner" data-d2planner-id="7">Test Unique</span>'
    html = '<h2>Gear</h2>' + tag * 162 + '<h2>Summary</h2>Use ' + tag + ' as a budget alternative.'
    raw.write_text(html)
    guide = section_inventory(html)
    cache = root / role['source']['path']
    cache.write_text(json.dumps({'sources': {gid: guide}}))
    digest = hashlib.sha256(cache.read_bytes()).hexdigest()
    prefix = '/sources/' + gid.replace('~', '~0').replace('/', '~1')
    role['source'].update(sha256=digest, locator=prefix + '/item_spans/0')
    occurrence['slot'] = 'unspecified'
    row = doc['rows'][0]
    row.update(kind='player_prose_repeat')
    row['expected_occurrence']['slot'] = 'unspecified'
    row['source'].update(sha256=digest, expected=guide['item_spans'][162])
    row['evidence'].update(sha256=digest, locator=prefix + '/sections/2/text', quote=guide['sections'][2]['text'])
    row['branches'][0]['profile_fingerprint'] = fingerprint(role)
    return role, occurrence, doc


def test_repeated_exact_planner_item_preserves_original_unspecified_slot(tmp_path):
    role, occurrence, doc = setup(tmp_path)
    original = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == original


@pytest.mark.parametrize(
    'change', ['different-item', 'different-planner', 'missing-planner', 'wrong-class', 'wrong-slot', 'wrong-section']
)
def test_name_alone_does_not_prove_the_same_prose_configuration(tmp_path, change):
    role, occurrence, doc = setup(tmp_path)
    row = doc['rows'][0]
    if change in ('different-item', 'different-planner', 'missing-planner'):
        raw = tmp_path / occurrence['source_id']
        replacement = {
            'different-item': 'data-d2planner-id="8"',
            'different-planner': 'data-d2planner-profile="other"',
            'missing-planner': 'data-d2planner-profile=""',
        }[change]
        original = 'data-d2planner-id="7"' if change == 'different-item' else 'data-d2planner-profile="planner"'
        # Modify only the first (reviewed primary) item, preserving the prose span.
        raw.write_text(raw.read_text().replace(original, replacement, 1))
        path = tmp_path / role['source']['path']
        path.write_text(json.dumps({'sources': {occurrence['source_id']: section_inventory(raw.read_text())}}))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        role['source']['sha256'] = row['source']['sha256'] = row['evidence']['sha256'] = digest
    elif change == 'wrong-class':
        role['must']['value'] = 'Sorceress'
    elif change == 'wrong-slot':
        role['slot'] = row['branches'][0]['slot'] = 'unspecified'
    else:
        row['evidence']['locator'] = row['evidence']['locator'].replace('/sections/2/', '/sections/1/')
        row['evidence']['quote'] = 'Test Unique'
    row['branches'][0]['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc)
