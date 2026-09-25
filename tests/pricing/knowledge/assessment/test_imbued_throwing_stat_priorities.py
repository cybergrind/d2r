import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('kind', 'slot', 'base', 'values'),
    [
        ('axe', 'weapon', 'Flying Axe', {'17:0': 150, '18:0': 150, '253:0': 10, '93:0': 20, '188:32': 2, '39:0': 20}),
        ('axe', 'offhand', 'Flying Axe', {'17:0': 150, '18:0': 150, '253:0': 10, '93:0': 20, '188:32': 2, '39:0': 20}),
        (
            'knife',
            'weapon',
            'Flying Knife',
            {'17:0': 200, '18:0': 200, '253:0': 10, '19:0': 121, '188:32': 2, '198:4225': 5, '62:0': 6},
        ),
        (
            'knife',
            'offhand',
            'Flying Knife',
            {'17:0': 200, '18:0': 200, '253:0': 10, '19:0': 121, '188:32': 2, '198:4225': 5, '62:0': 6},
        ),
        (
            'harpoon',
            'weapon',
            'Winged Harpoon',
            {'17:0': 200, '18:0': 200, '253:0': 10, '93:0': 20, '188:32': 2, '60:0': 9},
        ),
    ],
)
def test_imbue_example_requires_its_distinct_stat_combination(kind, slot, base, values):
    profiles = build()['profiles']
    role = f'double-throw-imbue-{kind}-{slot}'
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    stats['253:0']['unit'] = 'replenishment_rate'
    if '198:4225' in stats:
        stats['198:4225']['unit'] = 'percent_chance'

    def evaluate(item, context=None):
        context = {'player_class': 'Barbarian'} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    item = replace(facts(base, 'rare'), ethereal=True, stats=stats)
    result = evaluate(item)
    assert set(result.annotations) == set(values)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    assert any('does not guarantee an imbue outcome' in s for s in result.configurations[0]['role']['missing'])
    for key in stats:
        assert not evaluate(replace(item, stats={**stats, key: {**stats[key], 'value': values[key] - 1}})).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for key in (k for k in ('253:0', '198:4225') if k in stats):
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
    # Extra modifiers do not leak a different example's priorities into this one.
    unrelated = {'39:0', '60:0', '62:0', '93:0', '198:4225'} - set(values)
    extra = {k: {'status': 'decoded', 'value': 100} for k in unrelated}
    assert set(evaluate(replace(item, stats={**stats, **extra})).annotations) == set(values)
