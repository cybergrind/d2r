import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.planner_context_reviews import apply_context_reviews
from pricing.knowledge.builds import decode_planner


def evidence():
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/planner_context_reviews.json').read_bytes())
    row = next(r for r in reviews['rows'] if r['kind'] == 'generated_valkyrie_equipment')
    reviews = {'schema_version': 1, 'rows': [row]}
    documents = {row['source']: json.loads((ROOT / row['source']).read_bytes())}
    report = {'planner_reports': {row['source']: {'issues': [deepcopy(row['issue'])], 'reachable': ['keep']}}}
    return report, documents, reviews


def test_generated_valkyrie_context_review_preserves_reachability():
    report, documents, reviews = evidence()
    apply_context_reviews(report, documents, reviews, ROOT)
    entry = report['planner_reports'][reviews['rows'][0]['source']]
    assert entry['issues'] == []
    assert entry['reachable'] == ['keep']
    assert entry['reviewed_contexts'][0]['id'] == reviews['rows'][0]['id']


@pytest.mark.parametrize('change', ['source_hash', 'mechanics_hash', 'skill', 'equipment_reference', 'kind'])
def test_context_review_cannot_hide_changed_or_unrelated_equipment(change):
    report, documents, reviews = evidence()
    row = reviews['rows'][0]
    if change == 'source_hash':
        row['source_sha256'] = 'bad'
    elif change == 'mechanics_hash':
        row['evidence'][0]['sha256'] = 'bad'
    elif change == 'kind':
        row['kind'] = 'all_summons'
    else:
        planner = decode_planner(documents[row['source']])
        summon = planner['summons']['valkyrie']
        if change == 'skill':
            summon['skill'] = 'other'
        else:
            summon['items']['head'] = '1'
        documents[row['source']] = planner
        row['expected_summon'] = deepcopy(summon)
    with pytest.raises(ValueError, match='planner context'):
        apply_context_reviews(report, documents, reviews, ROOT)


@pytest.mark.parametrize(('field', 'value'), [('base', 'other'), ('quality', 3), ('ilvl', 99)])
def test_native_equipment_rules_reject_different_generated_items(field, value):
    from pricing.knowledge.assessment.maintenance.planner_context_reviews import _valkyrie

    _, _, reviews = evidence()
    row = reviews['rows'][0]
    sources = {ref['path']: (ROOT / ref['path']).read_bytes() for ref in row['evidence']}
    summon = row['expected_summon']
    assert _valkyrie(summon, sources)
    summon['items']['head'][field] = value
    assert not _valkyrie(summon, sources)
