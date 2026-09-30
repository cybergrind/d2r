"""An exact Ubers ring reference retains its player and companion semantics."""

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


def inputs(span=10):
    def read(path):
        return json.loads((ROOT / path).read_text())

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    guide_path = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
    planner_path = 'pricing/raw/mr/planners/ucgz20le.json'
    html = (ROOT / guide_path).read_text()
    ref = next(
        r
        for r in section_inventory(html)['embedded_item_refs']
        if embedded_guide_context(html, r)['span_index'] == span
    )
    planner = decode_planner(read(planner_path))
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    role_id = 'echoing-ubers-hellwarden' if span == 9 else 'echoing-ubers-sling-magic-pierce'
    role = next(p for p in profiles if p['id'] == role_id)
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = {
        'kind': 'echoing_pairing',
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-09-28',
        'reason': (
            'Exact Ubers Sling reference, native unique415 Ring; player Warlock pairing with Hellwarden '
            'and Renewed Black Cleft. Magic pierce3-5 and FCR10 support the role; perfect5 is preferred, '
            'not required. Companion names do not verify their rolls or the entire setup.'
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


def test_sling_tooltip_reuses_the_exact_ubers_pairing():
    result = compile_embedded_reviews(*inputs(), ROOT)
    assert len(result) == 1
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_id'] == 'echoing-ubers-sling-magic-pierce'


@pytest.mark.parametrize('change', ['class', 'side', 'companion', 'priority', 'perfect_only', 'socketed'])
def test_refreshed_review_cannot_change_pairing_semantics(change):
    document, links, profiles, uses = deepcopy(inputs())
    row = document['rows'][0]
    role = next(p for p in profiles if p['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'class':
        role['must']['all'][0]['value'] = 'Paladin'
    elif change == 'side':
        role['side'] = use['side'] = 'merc'
    elif change == 'companion':
        role['depends_on'].pop()
    elif change == 'priority':
        role['important_stats'].append('80:0')
    elif change == 'socketed':
        next(p for p in role['must']['all'] if p['field'] == 'sockets')['value'] = 1
    else:
        role['must']['all'].append({'op': 'stat_at_least', 'key': '358:0', 'value': 5, 'absent_is_zero': True})
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing pairing'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['identity', 'ethereal', 'sockets', 'pierce'])
def test_sling_reference_requires_native_legal_identity_and_rolls(change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_pairing import validate_echoing_pairing
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = inputs()
    review = document['rows'][0]
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    item = resolved['item']
    if change == 'identity':
        item['unique'] = 'unique0'
    elif change == 'ethereal':
        item['ethereal'] = True
    elif change == 'sockets':
        item['sockets'] = 1
    else:
        item['stats']['passive_mag_pierce'] = 8
    with pytest.raises(ValueError, match='Echoing pairing tooltip'):
        validate_echoing_pairing(review, resolved, role, ROOT)


def helmet_inputs():
    document, links, profiles, uses = inputs(9)
    document['rows'][0]['reason'] = (
        'Exact Ubers Hellwarden reference, native unique419 Death Mask with linked unique425 Guardian Light. '
        'The planner parent8 and jewel10 are separate rolls, not a captured total8. '
        'Require Warlock player, Sling, Renewed Black Cleft and the jewel; '
        'native helmet perfection excludes socket bonuses. '
        'Planner omits ethereal status; actual-item applicability separately requires nonethereal.'
    )
    return document, links, profiles, uses


def test_helmet_reference_preserves_native_roll_and_linked_jewel():
    result = compile_embedded_reviews(*helmet_inputs(), ROOT)
    assert result[0]['profile_id'] == 'echoing-ubers-hellwarden'
    assert result[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['socket_requirement', 'companion', 'total_roll', 'class', 'priority'])
def test_helmet_review_cannot_drop_pairing_or_count_jewel_as_helmet_roll(change):
    document, links, profiles, uses = deepcopy(helmet_inputs())
    review = document['rows'][0]
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'socket_requirement':
        role['required_socket_item'] = "Guardian's Thunder"
    elif change == 'companion':
        role['depends_on'].pop()
    elif change == 'total_roll':
        role['preferences'][0]['when']['op'] = 'stat_at_least'
    elif change == 'class':
        role['must']['all'][0]['value'] = 'Paladin'
    else:
        role['important_stats'].append('93:0')
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing pairing'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['missing', 'wrong_identity', 'impossible_roll'])
def test_linked_jewel_is_checked_independently_of_the_parent(change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_pairing import validate_echoing_pairing
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = helmet_inputs()
    review = document['rows'][0]
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'missing':
        resolved['socket_definitions'].clear()
    elif change == 'wrong_identity':
        resolved['socket_definitions']['161']['unique'] = 'unique421'
    else:
        resolved['socket_definitions']['161']['stats']['passive_mag_pierce'] = 11
    with pytest.raises(ValueError, match='Echoing pairing'):
        validate_echoing_pairing(review, resolved, role, ROOT)
