import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_fissure_player_helmets import helmet


@pytest.mark.parametrize('bonus', [1, 2, 3])
def test_lore_skill_support_does_not_require_planner_maximum(bonus):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == 'fissure-player-starter-lore'
    ]
    assert len(configs) == 1
    item = helmet(bonus=bonus)
    item = replace(item, stats={**item.stats, '127:0': {'status': 'decoded', 'value': 1}})

    def evaluate(candidate, context=None):
        context = {'player_class': 'Druid'} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    for quality in ('normal', 'superior'):
        result = evaluate(replace(item, rarity=quality))
        assert set(result.annotations) == {'107:234', '127:0'}
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
    # An identified recipe does not invent a missing decoded stat line.
    assert set(evaluate(helmet(bonus=bonus)).annotations) == {'107:234'}
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'runeword': None},
        {'runeword': 'Nadir'},
        {'sockets': 0},
        {'sockets': None},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'ethereal': True},
        {'ethereal': None},
        {'rarity': 'magic'},
        {'identified': False},
        {'item_type': 'helm'},
        {'stats': {'127:0': {'status': 'decoded', 'value': 1}}},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(replace(item, stats={}, capture_complete=False)).annotations
    for context in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(item, context).annotations
