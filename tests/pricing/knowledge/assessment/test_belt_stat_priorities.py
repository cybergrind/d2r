import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'quality', 'values'),
    [
        ('hammer-starter-belt', 'magic', {'99:0': 10, '39:0': 10}),
        ('blizzard-starter-belt', 'magic', {'99:0': 10, '39:0': 10}),
        ('wake-starter-belt', 'magic', {'99:0': 10, '39:0': 10}),
        ('foh-starter-belt', 'magic', {'7:0': 20, '43:0': 10}),
        ('holybolt-starter-belt', 'magic', {'7:0': 20, '43:0': 10}),
        ('fury-starter-belt', 'magic', {'7:0': 20, '39:0': 10}),
        ('poison-starter-belt', 'magic', {'7:0': 20, '39:0': 10}),
        ('goldfind-budget-belt', 'rare', {'99:0': 10, '43:0': 10, '41:0': 10, '79:0': 10}),
    ],
)
def test_belt_markers_require_specific_survival_or_farming_combination(role, quality, values):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1

    def evaluate(values, **changes):
        item = replace(
            facts('Belt', quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    result = evaluate(values)
    assert set(result.annotations) == set(values)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in values:
        assert not evaluate({**values, key: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    assert not evaluate(values, rarity='crafted').annotations
    assert not evaluate(values, ethereal=True).annotations
    assert not evaluate(values, ethereal=None).annotations
    if '7:0' in values:
        assert not evaluate({('6:0' if k == '7:0' else k): v for k, v in values.items()}).annotations
