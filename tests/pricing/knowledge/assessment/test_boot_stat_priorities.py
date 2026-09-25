import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_boot_markers_keep_three_resistance_gold_find_and_starter_combinations_separate():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if 'boot' in c.types]
    assert len(configs) == 10
    values = {'96:0': 10, '39:0': 5, '41:0': 5, '43:0': 5, '99:0': 5, '79:0': 5, '80:0': 5, '110:0': 5, '2:0': 5}
    for config in configs:
        required = {'96:0', '39:0'}
        if config.role_id == 'gold-find-budget-boots':
            required |= {'79:0'}
        elif config.role_id != 'nova-starter-boots':
            required |= {'41:0', '43:0'}

        def evaluate(stats, config=config, **changes):
            item = replace(
                facts('Heavy Boots', 'rare'),
                stats={k: {'status': 'decoded', 'value': v} for k, v in stats.items()},
                **changes,
            )
            return StatsEvaluator().evaluate(item, [config], role_outcomes=assess_role_results(item, profiles))

        result = evaluate(values)
        assert {k for k, a in result.annotations.items() if a['desirability'] == 'desirable'} == required
        if config.role_id == 'gold-find-budget-boots':
            assert set(result.annotations) == required | {'99:0'}
        if config.role_id == 'nova-starter-boots':
            assert set(result.annotations) == required
        for key in required:
            assert not evaluate({**values, key: 0}).annotations
            assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
        assert not evaluate(values, rarity='magic').annotations
        assert not evaluate(values, ethereal=True).annotations
        assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
