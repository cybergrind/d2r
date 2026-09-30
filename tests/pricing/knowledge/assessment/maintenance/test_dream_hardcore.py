"""Only the Dream guide's explicitly bounded Hardcore advice leaves Softcore scope."""

import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.hardcore_mentions import compile_hardcore_mentions
from pricing.knowledge.assessment.maintenance.reward_mentions import FIELDS
from tests.pricing.knowledge.assessment.maintenance.test_embedded_dream import ROOT, inputs


def reviews(span):
    document, links, _, _ = inputs(span)
    evidence = document['rows'][0]['evidence']
    path = 'pricing/data/appraisal-guide-sections.json'
    raw = (ROOT / path).read_bytes()
    cache = json.loads(raw)
    guide = evidence['guide']['path']
    sections = cache['sources'][guide]['sections']
    bounds = {
        'start': 49,
        'stop': 52,
        'start_heading': 'Hardcore',
        'stop_heading': 'Summary',
        'quote': sections[49]['text'],
    }
    reason = (
        'Exact Dream Paladin Hardcore gear-change advice, outside Softcore scope. '
        'The Dream identity and all separately reviewed Softcore uses remain scoped.'
    )
    row = {
        'kind': 'hardcore',
        'review_date': '2026-09-30',
        'reason': reason,
        'evidence': evidence,
        'section_range': bounds,
    }
    inventory = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_text())
    occurrence = next(
        r for r in inventory['occurrences'] if r['source_id'] == guide and r['source_locator'] == f'/item-spans/{span}'
    )
    escaped = guide.replace('~', '~0').replace('/', '~1')
    text_row = {
        'id': f'dream-hardcore-prose-span-{span}',
        'occurrence_id': occurrence['id'],
        'review_date': row['review_date'],
        'reason': reason,
        'expected_occurrence': {k: occurrence.get(k) for k in FIELDS},
        'source': {
            'path': path,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'locator': f'/sources/{escaped}/item_spans/{span}',
            'expected': cache['sources'][guide]['item_spans'][span],
        },
        'section_range': bounds,
    }
    return {'schema_version': 1, 'rows': [row]}, links, {'schema_version': 1, 'rows': [text_row]}, [occurrence]


@pytest.mark.parametrize('span', range(191, 200))
def test_dream_hardcore_excludes_only_exact_reference_and_label(span):
    embedded, links, text, occurrences = reviews(span)
    result = compile_embedded_reviews(embedded, links, [], [], ROOT)
    assert result[0]['state'] == 'excluded'
    assert 'profile_id' not in result[0]
    labels = compile_hardcore_mentions(text, occurrences, ROOT)
    assert len(labels) == 1
    assert labels[0]['state'] == 'excluded'
    assert labels[0]['occurrence_id'] == occurrences[0]['id']


@pytest.mark.parametrize('span', [0, 1, 200, 201])
def test_dream_introduction_and_summary_cannot_be_excluded_with_same_hardcore_bounds(span):
    embedded, links, text, occurrences = reviews(span)
    with pytest.raises(ValueError, match='outside reviewed Hardcore section'):
        compile_embedded_reviews(embedded, links, [], [], ROOT)
    with pytest.raises(ValueError, match='outside reviewed Hardcore section'):
        compile_hardcore_mentions(text, occurrences, ROOT)
