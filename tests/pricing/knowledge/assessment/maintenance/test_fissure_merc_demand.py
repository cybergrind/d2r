"""The guide distinguishes mercenary physical damage, leech and shared aura use."""

import json
from pathlib import Path

import pytest
from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand


@pytest.mark.parametrize(
    ('word', 'variant'),
    [
        ('Fortitude', 'Standard'),
        ('Fortitude', 'Magic Find'),
        ('Chains of Honor', 'Ubers'),
        ('Flickering Flame', 'Ubers'),
    ],
)
def test_fissure_mercenary_endorsements_retain_variant(word, variant):
    reviews = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    suffix = variant.lower().replace(' ', '-') + '-' + word.lower().replace(' ', '-')
    assert reviews == Contains(
        IsPartialDict(
            profile_id='fissure-merc-' + suffix,
            item=word,
            variant=variant,
            side='merc',
            strength='preferred',
            review_state='reviewed',
            scope='softcore',
        )
    )
    result = compile_demand(reviews, build()['profiles'])
    assert result[word]['contexts'] == Contains(
        IsPartialDict(build='fissure-druid', variant=variant, side='merc', strength='preferred')
    )


def test_flickering_flame_aura_explanation_distinguishes_party_and_wearer_benefits():
    reviews = json.loads(Path('pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    row = next(r for r in reviews if r['role_id'] == 'fissure-merc-ubers-flickering-flame')
    priority = next(p for p in row['priorities'] if p['key'] == '151:100')
    assert 'nearby Druid' in priority['explanation']
    assert 'wearer-only' in priority['explanation']
    assert 'not transferred to the player' not in priority['explanation']
