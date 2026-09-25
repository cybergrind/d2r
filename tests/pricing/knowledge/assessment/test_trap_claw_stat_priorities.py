import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'skill', 'utility'),
    [
        ('wake-of-fire-claw-candidate', 262, 251),
        ('lightning-sentry-claw-candidate', 271, 276),
    ],
)
def test_trap_claws_require_matching_affix_staffmod_pair_before_supporting_stats(role, skill, utility):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    required = {'188:48': 1, f'107:{skill}': 1}
    supporting = {'93:0': 20, '107:263': 1, f'107:{utility}': 1}

    def evaluate(values, **changes):
        item = replace(
            facts('Greater Talons', 'magic'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    result = evaluate(required | supporting)
    assert set(result.annotations) == set(required | supporting)
    assert all(result.annotations[k]['desirability'] == 'desirable' for k in required)
    assert all(result.annotations[k]['desirability'] == 'supporting' for k in supporting)
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    assert result.configurations[0]['role']['status'] == 'partial'
    assert set(evaluate(required).annotations) == set(required)
    for key in required:
        assert not evaluate({**required, **supporting, key: 0}).annotations
        assert not evaluate(
            {k: v for k, v in (required | supporting).items() if k != key}, capture_complete=False
        ).annotations
    for key in supporting:
        assert set(evaluate({**required, **supporting, key: 0}).annotations) == set(required | supporting) - {key}
    for actual, wrong in (
        ('188:48', '83:6'),
        (f'107:{skill}', f'97:{skill}'),
        (f'107:{skill}', f'107:{271 if skill == 262 else 262}'),
    ):
        assert not evaluate({(wrong if k == actual else k): v for k, v in (required | supporting).items()}).annotations
    for changes in (
        {'rarity': 'rare'},
        {'rarity': 'normal'},
        {'item_type': 'h2h'},
        {'identified': False},
        {'gaps': [f'Duplicate native stat 107:{skill}.']},
    ):
        assert not evaluate(required | supporting, **changes).annotations
