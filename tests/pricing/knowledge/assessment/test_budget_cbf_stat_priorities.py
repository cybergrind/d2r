import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'name', 'base', 'resists'),
    [
        ('kira', "Kira's Guardian", 'Tiara', [50, 50, 50, 50]),
        ('duriel', "Duriel's Shell", 'Cuirass', [20, 20, 50, 20]),
    ],
)
def test_budget_cbf_alternatives_keep_identity_and_complete_survival_combination(suffix, name, base, resists):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == f'dragon-talon-budget-cbf-{suffix}'
    ]
    assert len(configs) == 1
    values = {'153:0': 1, **dict(zip(('39:0', '41:0', '43:0', '45:0'), resists, strict=True))}
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    item = replace(facts(base, 'unique', name), stats=stats)

    def evaluate(candidate, context=None):
        context = {'player_class': 'Assassin'} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    result = evaluate(item)
    assert set(result.annotations) == set(values)
    assert result.annotations['153:0']['desirability'] == 'desirable'
    assert all(result.annotations[k]['desirability'] == 'supporting' for k in values if k != '153:0')
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    role = result.configurations[0]['role']
    assert role['status'] == 'partial'
    assert any('same slot' in s for s in role['missing'])
    assert any('level 90' in s for s in role['missing'])
    for key in values:
        assert not evaluate(replace(item, stats={**stats, key: {'status': 'decoded', 'value': 0}})).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for changes in (
        {'name': 'Raven Frost'},
        {'name': None},
        {'rarity': 'rare'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'item_type': 'tors' if suffix == 'kira' else 'circ'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(item, context).annotations
    extra = replace(
        item, stats={**stats, '31:0': {'status': 'decoded', 'value': 400}, '7:0': {'status': 'decoded', 'value': 80}}
    )
    assert set(evaluate(extra).annotations) == set(values)
