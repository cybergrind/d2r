"""Negative tooltip references cannot establish positive build demand."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


def negative_inputs():
    document, links, _, _ = inputs(11)
    review = document['rows'][0]
    for key in ('profile_id', 'profile_fingerprint', 'use_fingerprint'):
        review.pop(key)
    review.update(
        kind='echoing_gheed_removal',
        reason="Explicit Ubers removal of Gheed's Fortune; Standard/Magic Find uses and item value remain in scope.",
    )
    return document, links, [], []


def test_explicit_ubers_removal_is_excluded_without_endorsing_magic_find_tooltip():
    result = compile_embedded_reviews(*negative_inputs(), ROOT)
    assert len(result) == 1
    assert result[0]['state'] == 'excluded'
    assert 'profile_id' not in result[0]


@pytest.mark.parametrize('change', ['span', 'section', 'name', 'identity', 'base', 'quality', 'endorsement'])
def test_negative_reference_cannot_be_reused_for_other_contexts(change):
    from pricing.knowledge.assessment.maintenance.embedded_negative import validate_gheed_removal

    document, _, _, _ = negative_inputs()
    review = deepcopy(document['rows'][0])
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'span':
        resolved['context']['span_index'] = 121
    elif change == 'section':
        review['evidence']['reference']['section_locator'] = '/sections/25'
    elif change == 'name':
        resolved['context']['label'] = 'Sling'
    elif change == 'endorsement':
        review['profile_id'] = 'invented-positive-role'
    else:
        key, value = {'identity': ('unique', 'unique415'), 'base': ('base', 'rin'), 'quality': ('quality', 4)}[change]
        resolved['item'][key] = value
    with pytest.raises(ValueError, match='Gheed removal'):
        validate_gheed_removal(review, resolved, ROOT)


def test_removal_sentence_is_required_even_after_source_is_revalidated(monkeypatch):
    from pricing.knowledge.assessment.maintenance import embedded_negative

    document, _, _, _ = negative_inputs()
    review = document['rows'][0]
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    original = embedded_negative._read_pin

    def changed(pin, root):
        text = original(pin, root)
        return text.replace('Make sure to replace a ', 'Make sure to keep a ')

    monkeypatch.setattr(embedded_negative, '_read_pin', changed)
    with pytest.raises(ValueError, match='Gheed removal'):
        embedded_negative.validate_gheed_removal(review, resolved, ROOT)


def label_inputs():
    import json

    from pricing.knowledge.assessment.maintenance.embedded_occurrences import FIELDS

    document, links, profiles, uses = negative_inputs()
    inventory = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_text())
    occurrence = next(r for r in inventory['occurrences'] if r['id'] == 'cc6e26196a4e047f39245526')
    occurrence['details']['recommended'] = False
    document['rows'][0]['occurrence_links'] = [{k: occurrence.get(k) for k in FIELDS}]
    dispositions = compile_embedded_reviews(document, links, profiles, uses, ROOT)
    return document, dispositions, [occurrence], profiles


def test_negative_label_links_only_after_runtime_demand_is_corrected():
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import compile_embedded_occurrence_links

    args = label_inputs()
    result = compile_embedded_occurrence_links(*args)
    assert len(result) == 1
    assert result[0]['state'] == 'excluded'
    assert 'profile_id' not in result[0]
    args[2][0]['details']['recommended'] = True
    with pytest.raises(ValueError, match='negative demand'):
        compile_embedded_occurrence_links(*args)


@pytest.mark.parametrize(
    ('field', 'value'), [('source_locator', '/item-spans/121'), ('name', 'Sling'), ('class', 'Paladin')]
)
def test_negative_label_cannot_exclude_another_use_even_with_updated_expected_fields(field, value):
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import compile_embedded_occurrence_links

    args = label_inputs()
    args[2][0][field] = value
    args[0]['rows'][0]['occurrence_links'][0][field] = value
    with pytest.raises(ValueError, match='negative demand'):
        compile_embedded_occurrence_links(*args)
