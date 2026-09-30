"""Reviewed reuse must prove the exact guide context and native recipe."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


ROOT = Path(__file__).resolve().parents[5]


def inputs():
    packet = json.loads((ROOT / 'pricing/knowledge/assessment/planning/ABYSS_EMBEDDED_RECIPE_REVIEW.json').read_text())
    roles = json.loads((ROOT / 'pricing/knowledge/assessment/rules/roles/abyss-warlock-build-guide.json').read_text())[
        'profiles'
    ]
    uses = json.loads((ROOT / 'pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    rows, links = [], []
    for entry in packet['rows']:
        role = next(r for r in roles if r['id'] == entry['candidate_profile_id'])
        use = next(u for u in uses if u['profile_id'] == role['id'])
        row = {
            'kind': 'abyss_recipe',
            'evidence': {
                'guide': packet['sources'][0],
                'planner': packet['sources'][1],
                'reference': entry['reference'],
                'expected_context': entry['raw_context'],
                'item_fingerprint': entry['item_fingerprint'],
            },
            'recipe_source': packet['sources'][2],
            'recipe': entry['native_recipe_name'],
            'section': entry['section'],
            'profile_id': role['id'],
            'profile_fingerprint': fingerprint(role),
            'use_fingerprint': fingerprint(use),
            'review_date': '2026-09-28',
            'reason': 'Exact recipe example reuses the reviewed wearer-specific contribution; maxima are not minimums.',
        }
        rows.append(row)
        links.append({'source_id': packet['sources'][0]['path'], 'reference': entry['reference']})
    return (
        {'schema_version': 1, 'rows': rows},
        links,
        roles,
        [u for u in uses if u['profile_id'] in {row['profile_id'] for row in rows}],
    )


def test_nine_exact_abyss_recipe_contexts_reuse_existing_rules():
    document, links, roles, uses = inputs()
    results = compile_embedded_reviews(document, links, roles, uses, ROOT)
    assert len(results) == 9
    assert all(row['state'] == 'reviewed' for row in results)
    assert len({row['profile_id'] for row in results}) == 5
    assert len({row['id'] for row in results}) == 9


@pytest.mark.parametrize(
    'change',
    [
        'recipe',
        'section',
        'wearer',
        'class',
        'socket_count',
        'contents',
        'base',
        'runes',
        'priorities',
        'type',
        'ethereal',
    ],
)
def test_context_recipe_or_role_substitution_is_rejected(change):
    from pricing.knowledge.assessment.maintenance.embedded_abyss_recipes import validate_abyss_recipe

    document, _, roles, _ = inputs()
    review = deepcopy(document['rows'][1])  # Player Ancients' Pledge, not a mercenary Insight.
    role = deepcopy(next(r for r in roles if r['id'] == review['profile_id']))
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'recipe':
        review['recipe'] = 'Insight'
    elif change == 'section':
        review['section']['text'] = 'Hardcore advice'
    elif change == 'wearer':
        role['side'] = 'merc'
    elif change == 'class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'socket_count':
        resolved['item']['sockets'] = 4
    elif change == 'contents':
        role['must']['all'] = [p for p in role['must']['all'] if p.get('field') != 'socket_contents']
    elif change == 'base':
        resolved['item']['base'] = 'crs'
    elif change == 'priorities':
        role['important_stats'] = []
    elif change == 'type':
        role['types'] = ['pole']
    elif change == 'ethereal':
        resolved['item']['ethereal'] = True
    else:
        resolved['item']['socketedItems'].reverse()
    with pytest.raises(ValueError, match=r'[Aa]byss'):
        validate_abyss_recipe(review, resolved, role, ROOT)
