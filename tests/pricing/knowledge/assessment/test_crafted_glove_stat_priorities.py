import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role_id', 'values', 'required', 'supporting'),
    [
        (
            'double-throw-standard-gloves',
            {'93:0': 20, '81:0': 1, '0:0': 5, '39:0': 10},
            {'93:0', '81:0'},
            {'0:0', '39:0'},
        ),
        (
            'smite-high-investment-gloves',
            {'93:0': 20, '136:0': 5, '60:0': 3, '62:0': 3, '7:0': 10, '41:0': 10},
            {'93:0', '136:0'},
            {'7:0', '41:0'},
        ),
        (
            'dragon-talon-budget-gloves',
            {'188:50': 2, '93:0': 20, '136:0': 5, '60:0': 1, '7:0': 10},
            {'188:50', '93:0', '136:0', '60:0'},
            {'7:0'},
        ),
    ],
)
def test_crafted_glove_priorities_do_not_pool_incompatible_combinations(role_id, values, required, supporting):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1

    def evaluate(stats, **changes):
        item = replace(
            facts('Heavy Gloves', 'crafted'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in stats.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    result = evaluate(values)
    assert set(result.annotations) == required | supporting
    assert all(result.annotations[k]['desirability'] == 'desirable' for k in required)
    assert all(result.annotations[k]['desirability'] == 'supporting' for k in supporting)
    for key in required:
        assert not evaluate({**values, key: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    assert not evaluate(values, rarity='rare').annotations
    assert not evaluate(values, ethereal=True).annotations
