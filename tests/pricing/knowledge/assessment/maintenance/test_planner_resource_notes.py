import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.planner_context_reviews import apply_context_reviews


def evidence():
    document = json.loads((ROOT / 'pricing/knowledge/assessment/rules/planner_context_reviews.json').read_bytes())
    row = next(r for r in document['rows'] if r['id'] == 'abyss-resource-planner-notes')
    documents = {row['source']: json.loads((ROOT / row['source']).read_bytes())}
    report = {
        'planner_reports': {row['source']: {'issues': [{'kind': 'notes_require_review'}], 'reachable': ['keep']}},
        'source_hashes': {},
    }
    return report, documents, {'schema_version': 1, 'rows': [row]}


def test_all_note_parts_are_reviewed_without_excluding_item_definitions():
    report, documents, reviews = evidence()
    apply_context_reviews(report, documents, reviews, ROOT)
    row = reviews['rows'][0]
    result = report['planner_reports'][row['source']]
    assert result['issues'] == []
    assert result['reachable'] == ['keep']
    assert len(result['reviewed_contexts'][0]['parts']) == 4
    assert row['role_reference']['path'] in report['source_hashes']


@pytest.mark.parametrize('change', ['omit_potions', 'wrong_role', 'stale_role', 'different_note'])
def test_changed_or_incomplete_note_review_is_rejected(change):
    report, documents, reviews = evidence()
    row = reviews['rows'][0]
    if change == 'omit_potions':
        del row['parts'][2]
    elif change == 'wrong_role':
        row['role_reference']['id'] = 'abyss-starter-dagger'
    elif change == 'stale_role':
        row['role_reference']['fingerprint'] = 'stale'
    else:
        row['expected_notes'] = deepcopy(row['expected_notes'])
        row['expected_notes']['root']['children'].append({'text': 'Buy another item', 'type': 'text'})
    with pytest.raises(ValueError, match=r'(planner context|resource note)'):
        apply_context_reviews(report, documents, reviews, ROOT)
