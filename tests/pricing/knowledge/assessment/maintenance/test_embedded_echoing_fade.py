"""The same armor tooltip denotes two separate wearers' temporary prebuff uses."""

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


def inputs():
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
    rows, links = [], []
    for span, side in ((13, 'player'), (16, 'merc')):
        ref = next(
            ref for ref in guide['embedded_item_refs'] if embedded_guide_context(html, ref)['span_index'] == span
        )
        role = next(p for p in profiles if p['id'] == f'echoing-ubers-{side}-fade-prebuff')
        use = next(u for u in uses if u['profile_id'] == role['id'])
        rows.append(
            {
                'kind': 'echoing_fade',
                'profile_id': role['id'],
                'profile_fingerprint': fingerprint(role),
                'use_fingerprint': fingerprint(use),
                'review_date': '2026-09-28',
                'reason': 'Temporary Fade armor for the quoted wearer; the buff is not presumed active.',
                'recipe_source': pin('third-parties/d2data/json/runes.json'),
                'evidence': {
                    'guide': pin(guide_path),
                    'planner': pin(planner_path),
                    'reference': ref,
                    'expected_context': embedded_guide_context(html, ref),
                    'item_fingerprint': fingerprint(planner['items'][ref['item_id']]),
                },
            }
        )
        links.append({'source_id': guide_path, 'reference': ref})
    return {'schema_version': 1, 'rows': rows}, links, profiles, uses


def test_separate_player_and_mercenary_fade_references_reuse_exact_roles():
    results = compile_embedded_reviews(*inputs(), ROOT)
    assert {r['profile_id'] for r in results} == {
        'echoing-ubers-player-fade-prebuff',
        'echoing-ubers-merc-fade-prebuff',
    }
    assert len({r['id'] for r in results}) == 2
    assert all(r['state'] == 'reviewed' for r in results)


@pytest.mark.parametrize('change', ['class', 'slot', 'wearer', 'priority'])
def test_refreshed_fingerprints_cannot_approve_a_different_prebuff_use(change):
    document, links, profiles, uses = deepcopy(inputs())
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(r for r in uses if r['profile_id'] == row['profile_id'])
    if change == 'class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'slot':
        role['slot'] = 'Body Armor'
    elif change == 'wearer':
        role['side'] = 'merc'
        use['side'] = 'merc'
    else:
        role['important_stats'].append('93:0')
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'[Ee]choing'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)
