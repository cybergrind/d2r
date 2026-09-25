import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'quality', 'skills', 'minimum', 'support'),
    [
        ('poison-nova-standard-circlet', 'rare', '83:2', 2, '7:0'),
        ('foh-tribrid-circlet', 'rare', '83:3', 2, '2:0'),
        ('abyss-standard-circlet', 'rare', '83:7', 2, '96:0'),
        ('berserk-mobility-circlet', 'rare', '83:4', 2, '7:0'),
        ('enchant-standard-circlet', 'magic', '188:8', 3, '96:0'),
        ('enchant-prebuff-circlet', 'magic', '188:8', 3, None),
    ],
)
def test_circlet_markers_preserve_skill_identity_quality_and_prebuff_role(role, quality, skills, minimum, support):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1

    def evaluate(values, **changes):
        item = replace(
            facts('Diadem', quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    values = {skills: minimum, '105:0': 20, '96:0': 30}
    if support:
        values[support] = 5
    result = evaluate(values)
    assert result.annotations[skills]['desirability'] == 'desirable'
    if quality == 'rare':
        assert result.annotations['105:0']['desirability'] == 'desirable'
        assert not evaluate({**values, '105:0': 10}).annotations
    else:
        assert '105:0' not in result.annotations
    if support:
        assert result.annotations[support]['desirability'] == 'supporting'
    else:
        assert '96:0' not in result.annotations
    assert not evaluate({**values, skills: minimum - 1}).annotations
    assert not evaluate({k: v for k, v in values.items() if k != skills}, capture_complete=False).annotations
    assert not evaluate(values, rarity='crafted').annotations
    assert not evaluate(values, ethereal=True).annotations
    assert not evaluate(values, ethereal=None).annotations
