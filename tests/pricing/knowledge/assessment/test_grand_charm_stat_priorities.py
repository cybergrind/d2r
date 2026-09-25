import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'tree', 'suffix'),
    [
        ('blizzard-standard-life-skiller', 10, {'7:0': 20}),
        ('fury-standard-life-skiller', 2, {'7:0': 20}),
        ('hammer-standard-life-skiller', 24, {'7:0': 20}),
        ('hammer-standard-fhr-skiller', 24, {'99:0': 12}),
        ('nova-standard-life-skiller', 9, {'7:0': 20}),
        ('poison-starter-skiller', 17, {}),
        ('poison-standard-life-skiller', 17, {'7:0': 20}),
        ('lightning-starter-skiller', 9, {}),
        ('lightning-standard-life-skiller', 9, {'7:0': 20}),
        ('lightning-standard-fhr-skiller', 9, {'99:0': 12}),
    ],
)
def test_grand_charm_markers_require_exact_tree_and_role_combination(role, tree, suffix):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    key = f'188:{tree}'
    values = {key: 1, **suffix}

    def evaluate(values, **changes):
        item = replace(
            facts('Grand Charm', 'magic'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    result = evaluate(values)
    assert set(result.annotations) == set(values)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    for required in values:
        assert not evaluate({**values, required: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != required}, capture_complete=False).annotations
    assert not evaluate({f'188:{tree + 1}': 1, **suffix}).annotations
    if '99:0' in suffix:
        assert not evaluate({key: 1, '99:0': 11}).annotations
        assert not evaluate({key: 1, '7:0': 45}).annotations
    if '7:0' in suffix:
        assert not evaluate({key: 1, '6:0': 20}).annotations
        assert not evaluate({key: 1, '99:0': 12}).annotations
    if not suffix:
        assert set(evaluate({key: 1, '7:0': 20}).annotations) == {key}
    for changes in ({'rarity': 'rare'}, {'ethereal': True}, {'ethereal': None}, {'identified': False}):
        assert not evaluate(values, **changes).annotations
