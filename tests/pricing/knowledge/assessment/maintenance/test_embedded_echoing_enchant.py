"""Demon Limb's player prebuff does not endorse a mercenary charge activation."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.builds import decode_planner


ROOT = Path(__file__).resolve().parents[5]


def inputs(span=12):
    def read(path):
        return json.loads((ROOT / path).read_text())

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    guide_path = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
    planner_path = 'pricing/raw/mr/planners/ucgz20le.json'
    html = (ROOT / guide_path).read_text()
    guide = section_inventory(html)
    planner = decode_planner(read(planner_path))
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    ref = next(r for r in guide['embedded_item_refs'] if embedded_guide_context(html, r)['span_index'] == span)
    role = next(p for p in profiles if p['id'] == 'echoing-strike-warlock-guide-3-demon-limb-prebuff')
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = {
        'kind': 'echoing_enchant',
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-09-28',
        'reason': (
            'Player equips Demon Limb temporarily for level 23 Enchant charges; '
            'available charges do not establish an active buff. '
            'Mercenary recipient reference remains a separate review.'
        ),
        'native_source': pin('third-parties/d2data/json/uniqueitems.json'),
        'evidence': {
            'guide': pin(guide_path),
            'planner': pin(planner_path),
            'reference': ref,
            'expected_context': embedded_guide_context(html, ref),
            'item_fingerprint': fingerprint(planner['items'][ref['item_id']]),
        },
    }
    return {'schema_version': 1, 'rows': [row]}, [{'source_id': guide_path, 'reference': ref}], profiles, uses


def test_player_enchant_reference_reuses_existing_ubers_prebuff():
    result = compile_embedded_reviews(*inputs(), ROOT)
    assert len(result) == 1
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_id'] == 'echoing-strike-warlock-guide-3-demon-limb-prebuff'


@pytest.mark.parametrize('change', ['merc_reference', 'wearer', 'class', 'charges', 'slot', 'priority'])
def test_prebuff_review_cannot_approve_another_use_with_refreshed_fingerprints(change):
    document, links, profiles, uses = deepcopy(inputs(15 if change == 'merc_reference' else 12))
    row = document['rows'][0]
    role = next(p for p in profiles if p['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'wearer':
        role['side'] = use['side'] = 'merc'
    elif change == 'class':
        role['must']['value'] = 'Sorceress'
    elif change == 'charges':
        role['depends_on'] = []
    elif change == 'slot':
        role['slot'] = 'Weapon'
    elif change == 'priority':
        role['important_stats'].append('17:0')
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Enchant'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['base', 'quality', 'identity', 'skill'])
def test_native_tooltip_identity_and_enchant_charges_are_required(change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_enchant import validate_echoing_enchant
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = inputs()
    row = document['rows'][0]
    role = next(p for p in profiles if p['id'] == row['profile_id'])
    resolved = validate_embedded_evidence(row['evidence'], ROOT)
    item = resolved['item']
    if change == 'base':
        item['base'] = 'wrong'
    elif change == 'quality':
        item['quality'] = 4
    elif change == 'identity':
        item['unique'] = 'unique0'
    else:
        item['stats'].pop('item_charged_skill#52#23')
    with pytest.raises(ValueError, match='Echoing Enchant tooltip'):
        validate_echoing_enchant(row, resolved, role, ROOT)


def recipient_inputs():
    document, links, profiles, uses = inputs(15)
    row = document['rows'][0]
    role = next(p for p in profiles if p['id'] == 'echoing-ubers-mercenary-enchant-prebuff')
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row.update(profile_id=role['id'], profile_fingerprint=fingerprint(role), use_fingerprint=fingerprint(use))
    row['reason'] = 'The player casts Enchant charges on the Act 5 Frenzy mercenary; the mercenary is the recipient.'
    return document, links, profiles, uses


def test_mercenary_reference_has_player_caster_and_distinct_recipient_rule():
    result = compile_embedded_reviews(*recipient_inputs(), ROOT)
    assert result[0]['profile_id'] == 'echoing-ubers-mercenary-enchant-prebuff'
    assert result[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['mercenary', 'caster', 'identified'])
def test_recipient_reference_preserves_caster_and_recipient_requirements(change):
    document, links, profiles, uses = deepcopy(recipient_inputs())
    row = document['rows'][0]
    role = next(p for p in profiles if p['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'mercenary':
        role['must']['all'][1]['value'] = 'Act 2 Might'
    elif change == 'caster':
        role['side'] = use['side'] = 'merc'
    else:
        role['must']['all'].pop()
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Enchant'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)
