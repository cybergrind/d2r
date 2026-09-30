"""Legacy Dream equipment references endorse a slot component, not every variant."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


ROOT = Path(__file__).resolve().parents[5]


def inputs(span):
    inventory = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_text())
    bundle = json.loads((ROOT / 'pricing/data/appraisal-build-profiles.json').read_text())
    path = 'pricing/raw/mr/guides__dream-paladin.html'
    html = (ROOT / path).read_text()
    links = [r for r in inventory['embedded_item_links'] if r['source_id'] == path]
    link = next(r for r in links if embedded_guide_context(html, r['reference'])['span_index'] == span)
    context = embedded_guide_context(html, link['reference'])
    slot = 'helmets' if span == 73 else 'off-hand'
    role = next(r for r in bundle['profiles'] if r['id'] == f'dream-paladin-dream-{slot}-aura-recipe')
    use = next(u for u in bundle['guide_demand']['uses'] if u['profile_id'] == role['id'])

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    row = {
        'kind': 'dream_equipment',
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-09-29',
        'reason': 'Dream equipment-table component; paired setup requires verified complementary equipped Dream. '
        'Example rolls are not minimum requirements and no planner variant is inferred.',
        'recipe_source': pin('third-parties/d2data/json/runes.json'),
        'base_source': pin('third-parties/d2data/json/armor.json'),
        'evidence': {
            'guide': pin(path),
            'planner': pin(link['planner_source_id']),
            'reference': link['reference'],
            'expected_context': context,
            'item_fingerprint': fingerprint(link['item_definition']),
        },
    }
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import FIELDS

    row['occurrence_links'] = [
        {key: occurrence[key] for key in FIELDS}
        for occurrence in inventory['occurrences']
        if occurrence['source_id'] == path and occurrence['source_locator'] == f'/item-spans/{span}'
    ]
    return {'schema_version': 1, 'rows': [row]}, links, [role], [use]


@pytest.mark.parametrize('span', [65, 73])
def test_legacy_dream_equipment_review(span):
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import compile_embedded_occurrence_links

    document, links, roles, uses = inputs(span)
    result = compile_embedded_reviews(document, links, roles, uses, ROOT)
    assert result[0]['state'] == 'reviewed'
    occurrences = document['rows'][0]['occurrence_links']
    occurrences = [{**row, 'source_status': 'verified'} for row in occurrences]
    linked = compile_embedded_occurrence_links(document, result, occurrences, roles)
    assert len(linked) == 1
    assert linked[0]['occurrence_id'] == occurrences[0]['id']
    assert linked[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['slot', 'class', 'ethereal', 'pair', 'aura', 'life', 'family'])
def test_fresh_fingerprints_do_not_approve_changed_dream_semantics(change):
    document, links, roles, uses = deepcopy(inputs(65))
    role, use, review = roles[0], uses[0], document['rows'][0]
    if change == 'slot':
        role['slot'] = 'Helmets'
    elif change == 'class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'ethereal':
        role['must']['all'][-1]['value'] = True
    elif change == 'pair':
        role['depends_on'][0]['when'] = {'op': 'context_contains', 'field': 'player_items', 'value': 'Dream'}
    elif change == 'family':
        role['types'] = ['swor']
    elif change == 'aura':
        role['important_stats'].remove('151:118')
    else:
        role['important_stats'].remove('7:0')
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Dream'):
        compile_embedded_reviews(document, links, roles, uses, ROOT)


def test_dream_prose_is_not_approved_by_the_equipment_policy():
    with pytest.raises(ValueError, match='Dream'):
        compile_embedded_reviews(*inputs(1), ROOT)


def test_legacy_evidence_requires_explicit_opt_in_and_has_no_profile_locator():
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, _, _ = inputs(65)
    evidence = document['rows'][0]['evidence']
    with pytest.raises(ValueError, match='embedded profile'):
        validate_embedded_evidence(evidence, ROOT)
    resolved = validate_embedded_evidence(evidence, ROOT, allow_legacy=True)
    assert resolved['profile_locator'] is None


@pytest.mark.parametrize('change', ['base', 'recipe', 'runes', 'ethereal', 'socket_count'])
def test_dream_native_equipment_semantics_reject_substitutions(change):
    from pricing.knowledge.assessment.maintenance.embedded_dream import validate_dream_equipment
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, roles, _ = inputs(65)
    row = document['rows'][0]
    resolved = validate_embedded_evidence(row['evidence'], ROOT, allow_legacy=True)
    item = resolved['item']
    if change == 'base':
        item['base'] = 'unknown'
    elif change == 'recipe':
        item['unique'] = 'other-recipe'
    elif change == 'runes':
        item['socketedItems'] = list(reversed(item['socketedItems']))
    elif change == 'ethereal':
        item['ethereal'] = True
    else:
        item['sockets'] = 2
    with pytest.raises(ValueError, match='Dream native'):
        validate_dream_equipment(row, resolved, roles[0], ROOT)
