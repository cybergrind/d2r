import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_smite_belt_marks_open_wounds_and_survival_without_claiming_sustain():
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == 'smite-starter-crafted-belt')
    assert '60:0' not in profile['important_stats']
    assert all(p['when'].get('key') != '60:0' for p in profile['preferences'])
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == profile['id']]
    assert len(configs) == 1
    values = {'99:0': 10, '60:0': 1, '135:0': 5, '7:0': 10}

    def evaluate(values, **changes):
        item = replace(
            facts('Mesh Belt', 'crafted'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        roles = assess_role_results(item, [profile])
        return StatsEvaluator().evaluate(item, configs, role_outcomes=roles)

    result = evaluate(values)
    assert set(result.annotations) == {'99:0', '135:0', '7:0'}
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    role = result.configurations[0]['role']
    assert role['status'] == 'partial'
    assert any('Life Tap' in condition for condition in role['missing'])
    assert set(evaluate({**values, '60:0': 3}).annotations) == set(result.annotations)
    for key in values:
        assert not evaluate({**values, key: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    for changes in ({'ethereal': True}, {'ethereal': None}, {'rarity': 'rare'}, {'identified': False}):
        assert not evaluate(values, **changes).annotations
    assert not evaluate({('6:0' if k == '7:0' else k): v for k, v in values.items()}).annotations
