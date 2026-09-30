"""Independent guide expectations for the two distinct Fissure player helm roles."""

import json
from pathlib import Path

import pytest
from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand


@pytest.mark.parametrize(
    ('word', 'variant', 'strength'),
    [('Lore', 'Starter', 'preferred'), ('Flickering Flame', 'Standard', 'alternative')],
)
def test_fissure_player_helm_endorsements_keep_progression_and_alternative(word, variant, strength):
    reviews = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    result = compile_demand(reviews, build()['profiles'])
    assert result[word]['contexts'] == Contains(
        IsPartialDict(build='fissure-druid', variant=variant, side='player', strength=strength)
    )
