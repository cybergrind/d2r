"""Each Dream pairing claim binds both source items without endorsing Hardcore variants."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
from pricing.knowledge.assessment.maintenance.embedded_occurrences import FIELDS, compile_embedded_occurrence_links
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_dream import ROOT, inputs


PAIRS = {0: 1, 1: 0, 13: 14, 14: 13, 200: 201, 201: 200}


def prose_inputs(span, partner=None):
    head = span in (0, 13, 191, 200)
    document, links, roles, uses = inputs(73 if head else 65)
    row = document['rows'][0]
    html = (ROOT / row['evidence']['guide']['path']).read_text()
    contexts = [
        (link, embedded_guide_context(html, link['reference']))
        for link in links
        if link['reference']['item_id'] in ('6', '7')
    ]

    def evidence(index):
        link, context = next((link, context) for link, context in contexts if context['span_index'] == index)
        return {
            **row['evidence'],
            'reference': link['reference'],
            'expected_context': context,
            'item_fingerprint': fingerprint(link['item_definition']),
        }

    original = evidence(span)
    companion = evidence(PAIRS.get(span, 192) if partner is None else partner)
    row.update(
        kind='dream_pair_prose',
        review_date='2026-09-30',
        evidence=original,
        companion_evidence=companion,
        reason='Exact paired Dream instruction; a single piece does not establish level 30 Holy Shock. '
        'Use the complementary equipped-item requirement; no skill synergies or price inferred.',
    )
    inventory = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_text())
    row['occurrence_links'] = [
        {key: occurrence[key] for key in FIELDS}
        for occurrence in inventory['occurrences']
        if occurrence['source_id'] == row['evidence']['guide']['path']
        and occurrence['source_locator'] == f'/item-spans/{span}'
    ]
    return document, links, roles, uses


@pytest.mark.parametrize('span', PAIRS)
def test_each_softcore_pair_reference_and_qualified_label_gets_its_own_review(span):
    document, links, roles, uses = prose_inputs(span)
    results = compile_embedded_reviews(document, links, roles, uses, ROOT)
    row = document['rows'][0]
    occurrences = [{**r, 'source_status': 'verified'} for r in row['occurrence_links']]
    resolved = compile_embedded_occurrence_links(document, results, occurrences, roles)
    assert len(resolved) == 1
    assert resolved[0]['state'] == 'reviewed'
    assert resolved[0]['occurrence_id'] == occurrences[0]['id']
    assert resolved[0]['resolved_identity']['name'] == 'Dream'
    assert resolved[0]['resolved_identity']['slot'] == roles[0]['slot']
    assert occurrences[0]['identity_status'] == 'unresolved'  # Preserve original extraction evidence.


@pytest.mark.parametrize(('span', 'partner'), [(191, 192), (0, 0), (0, 14)])
def test_hardcore_same_piece_and_cross_section_partners_are_not_softcore_pair_reviews(span, partner):
    with pytest.raises(ValueError, match='Dream'):
        compile_embedded_reviews(*prose_inputs(span, partner), ROOT)


def test_refreshed_role_cannot_replace_equipped_companion_with_inventory_name():
    document, links, roles, uses = deepcopy(prose_inputs(1))
    roles[0]['depends_on'][0]['when'] = {'op': 'context_contains', 'field': 'player_items', 'value': 'Dream'}
    row = document['rows'][0]
    uses[0]['profile_fingerprint'] = row['profile_fingerprint'] = fingerprint(roles[0])
    row['use_fingerprint'] = fingerprint(uses[0])
    with pytest.raises(ValueError, match='Dream paired'):
        compile_embedded_reviews(document, links, roles, uses, ROOT)


def test_pair_claim_must_still_be_present_in_the_pinned_section(monkeypatch):
    from pricing.knowledge.assessment.maintenance import embedded_dream_prose as module

    document, links, roles, uses = prose_inputs(13)
    original = module._read_pin

    def changed(pin, root):
        text = original(pin, root)
        return text.replace('Level 30', 'Level 15') if pin['path'].endswith('.html') else text

    monkeypatch.setattr(module, '_read_pin', changed)
    with pytest.raises(ValueError, match='joint-equipment claim'):
        compile_embedded_reviews(document, links, roles, uses, ROOT)


@pytest.mark.parametrize('field', ['source_locator', 'category', 'slot'])
def test_qualified_alias_cannot_consume_a_different_occurrence(field):
    from pricing.knowledge.assessment.maintenance.embedded_dream_prose import dream_label_links

    document, _, _, _ = prose_inputs(1)
    review = document['rows'][0]
    expected = review['occurrence_links'][0]
    expected[field] = {'source_locator': '/item-spans/192', 'category': 'runeword', 'slot': 'Helmets'}[field]
    occurrence = {**expected, 'source_status': 'verified'}
    disposition = {'id': 'test', 'state': 'reviewed', 'profile_id': review['profile_id']}
    with pytest.raises(ValueError, match='qualified occurrence'):
        dream_label_links(review, disposition, {occurrence['id']: occurrence}, FIELDS)
