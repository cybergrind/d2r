"""An exact validated tooltip can cover its own visible label, not nearby uses."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_fade import ROOT, inputs


FIELDS = (
    'id',
    'name',
    'original_label',
    'kind',
    'source_id',
    'source_locator',
    'build',
    'class',
    'variant',
    'side',
    'slot',
    'category',
    'identity_id',
    'identity_status',
)


@pytest.fixture(
    scope='module',
    params=[
        'fade',
        'enchant',
        'pairing',
        'helmet',
        'malice',
        'insight',
        'insight_overview',
        'insight_progression',
        'cure_progression',
        'enigma_late',
    ],
)
def evidence(request):
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_cure import cure_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_enchant import inputs as enchant_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_enigma import enigma_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_insight import insight_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_malice import malice_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import (
        helmet_inputs,
        inputs as pairing_inputs,
    )

    document, links, profiles, uses = {
        'cure_progression': lambda: cure_inputs(155),
        'enigma_late': enigma_inputs,
        'fade': inputs,
        'enchant': enchant_inputs,
        'pairing': pairing_inputs,
        'helmet': helmet_inputs,
        'malice': malice_inputs,
        'insight': insight_inputs,
        'insight_overview': lambda: insight_inputs(127),
        'insight_progression': lambda: insight_inputs(130),
    }[request.param]()
    inventory = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_text())
    for row in document['rows']:
        source = row['evidence']
        occurrence = next(
            o
            for o in inventory['occurrences']
            if o['source_id'] == source['guide']['path']
            and o['source_locator'] == f'/item-spans/{source["expected_context"]["span_index"]}'
        )
        row['occurrence_links'] = [{key: occurrence.get(key) for key in FIELDS}]
    dispositions = compile_embedded_reviews(document, links, profiles, uses, ROOT)
    return document, dispositions, inventory, profiles, uses


def test_completion_closes_only_the_reviewed_labels(evidence):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion

    document, _, inventory, profiles, uses = evidence
    result = compile_completion(
        {'rows': []}, inventory, {}, profiles=profiles, uses=uses, embedded_reviews=document, source_root=ROOT
    )
    queued = {r['id'] for r in result['queue']}
    for row in document['rows']:
        assert 'occurrence:' + row['occurrence_links'][0]['id'] not in queued
    untouched = next(
        o
        for o in inventory['occurrences']
        if o['source_id'] == document['rows'][0]['evidence']['guide']['path']
        and o['source_locator'] == '/item-spans/15'
    )
    assert 'occurrence:' + untouched['id'] in queued  # Demon Limb still needs its own review.
    assert 'final:verification' in queued
    assert not result['complete']


@pytest.mark.parametrize(
    'change', ['span', 'identity', 'class', 'duplicate', 'excluded', 'missing_review', 'unsupported_kind']
)
def test_links_cannot_launder_unreviewed_or_different_occurrences(evidence, change):
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import compile_embedded_occurrence_links

    document, dispositions, inventory, profiles, _ = deepcopy(evidence)
    review = document['rows'][0]
    link = review['occurrence_links'][0]
    occurrence = next(o for o in inventory['occurrences'] if o['id'] == link['id'])
    if change in ('span', 'identity', 'class'):
        key, value = {
            'span': ('source_locator', '/item-spans/16'),
            'identity': ('name', 'Spirit'),
            'class': ('class', 'Paladin'),
        }[change]
        link[key] = occurrence[key] = value  # Fresh matching evidence is not enough.
    elif change == 'duplicate':
        review['occurrence_links'].append(deepcopy(link))
    elif change == 'excluded':
        dispositions[0]['state'] = 'excluded'
    elif change == 'missing_review':
        dispositions.clear()
    else:
        review['kind'] = 'equipment'
    with pytest.raises(ValueError, match=r'[Ee]mbedded occurrence'):
        compile_embedded_occurrence_links(document, dispositions, inventory['occurrences'], profiles)
