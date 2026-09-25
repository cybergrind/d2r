import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_enchant_prebuff_requires_fire_affix_and_both_native_staffmods():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == 'enchant-prebuff-orb-candidate'
    ]
    assert len(configs) == 1
    required = {'188:8': 1, '107:52': 1, '107:61': 1}

    def evaluate(values, **changes):
        item = replace(
            facts('Eldritch Orb', 'magic'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    for ethereal in (False, True, None):
        result = evaluate({**required, '105:0': 20}, ethereal=ethereal)
        assert set(result.annotations) == set(required)
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
        role = result.configurations[0]['role']
        assert role['status'] == 'partial'
        assert any('sockets' in c for c in role['missing'])
    for key in required:
        assert not evaluate({**required, key: 0}).annotations
        assert not evaluate({k: v for k, v in required.items() if k != key}, capture_complete=False).annotations
    for actual, wrong in (('188:8', '188:9'), ('188:8', '83:1'), ('107:52', '97:52'), ('107:61', '107:63')):
        assert not evaluate({(wrong if k == actual else k): v for k, v in required.items()}).annotations
    for changes in (
        {'rarity': 'rare'},
        {'rarity': 'unique'},
        {'item_type': 'staf'},
        {'identified': False},
        {'gaps': ['Duplicate native stat 107:52.']},
    ):
        assert not evaluate(required, **changes).annotations
    assert set(evaluate(dict.fromkeys(required, 3)).annotations) == set(required)
