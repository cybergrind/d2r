import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('slot', ['weapon', 'offhand'])
def test_rare_throwing_planner_annotations_require_complete_typed_high_roll_target(slot):
    profiles = build()['profiles']
    role = f'double-throw-rare-planner-{slot}'
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    values = {'17:0': 450, '18:0': 450, '19:0': 250, '93:0': 40, '188:32': 2, '253:0': 10, '198:4225': 5}
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    stats['253:0']['unit'] = 'replenishment_rate'
    stats['198:4225']['unit'] = 'percent_chance'

    def evaluate(item, context=None):
        context = {'player_class': 'Barbarian'} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    for base in ('Ghost Glaive', 'Winged Axe', 'Flying Axe'):
        item = replace(facts(base, 'rare'), ethereal=True, stats=stats)
        result = evaluate(item)
        assert set(result.annotations) == set(values)
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
        assert result.configurations[0]['role']['status'] == 'partial'
        assert any('not automatically worthless' in s for s in result.configurations[0]['role']['missing'])
    for key in stats:
        assert not evaluate(replace(item, stats={**stats, key: {**stats[key], 'value': values[key] - 1}})).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for key in ('253:0', '198:4225'):
        assert not evaluate(replace(item, stats={**stats, key: {**stats[key], 'unit': 'seconds'}})).annotations
    for cold in ('54:0', '55:0'):
        assert not evaluate(replace(item, stats={**stats, cold: {'status': 'decoded', 'value': 1}})).annotations
    assert not evaluate(replace(item, capture_complete=False)).annotations
    for changes in (
        {'rarity': 'magic'},
        {'ethereal': False},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'identified': False},
        {'base_code': facts('Balanced Axe', 'rare').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Amazon'}):
        assert not evaluate(item, context).annotations
