import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'klass', 'key', 'bonus', 'qualities'),
    [
        ('double-throw-barbarian-guide-berserker-magus', 'Barbarian', '83:4', 2, ('magic', 'rare')),
        ('berserk-barbarian-berserker-magus', 'Barbarian', '83:4', 2, ('magic', 'rare')),
        ('wake-of-fire-assassin-cunning-magus', 'Assassin', '188:48', 3, ('magic',)),
        ('lightning-sentry-assassin-cunning-magus', 'Assassin', '188:48', 3, ('magic',)),
    ],
)
def test_magus_circlet_stat_combinations_preserve_class_quality_and_thresholds(role, klass, key, bonus, qualities):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    values = {key: bonus, '105:0': 20}

    def evaluate(values, context=None, **changes):
        context = {'player_class': klass} if context is None else context
        item = replace(
            facts('Diadem', 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    for quality in qualities:
        result = evaluate(values, rarity=quality)
        assert set(result.annotations) == set(values)
        assert result.configurations[0]['role']['status'] == 'partial'
        assert any('Socket' in c for c in result.configurations[0]['role']['missing'])
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
    for key in values:
        assert not evaluate({**values, key: values[key] - 1}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(values, context).annotations
    for changes in ({'ethereal': True}, {'ethereal': None}, {'rarity': 'unique'}, {'identified': False}):
        assert not evaluate(values, **changes).annotations
    if klass == 'Assassin':
        assert not evaluate(values, rarity='rare').annotations
        assert not evaluate({'83:6': 3, '105:0': 20}).annotations
