import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    'role_id',
    [
        'strafe-amazon-1-demon-limb-prebuff',
        'echoing-strike-warlock-guide-1-demon-limb-prebuff',
        'echoing-strike-warlock-guide-3-demon-limb-prebuff',
        'dream-paladin-2-demon-limb-prebuff',
    ],
)
def test_demon_limb_priorities_preserve_charge_and_alternative_conditions(role_id):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == role_id)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    context = {'player_class': role['must']['value'], 'player_items': []}
    item = replace(
        facts('Tyrant Club', 'unique', 'Demon Limb'),
        stats={
            '204:3351': charged(1),
            '17:0': {'status': 'decoded', 'value': 230},
        },
    )

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    for ethereal in (False, True, None):
        result = evaluate(replace(item, ethereal=ethereal))
        assert set(result.annotations) == {'204:3351'}
        assert result.annotations['204:3351']['desirability'] == 'desirable'
        assert result.annotations['204:3351']['roll_quality'] == 'unassessed'
        assert result.configurations[0]['role']['status'] == 'partial'
        assert any('Ethereal' in line for line in result.configurations[0]['role']['missing'])
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'rare'},
        {'item_type': 'staf'},
        {'identified': False},
        {'stats': {}},
        {'stats': {'204:3351': charged(0)}},
        {'stats': {'204:3467': charged(1)}},
        {'stats': {'204:3351': {**charged(1), 'value': 2}}},
        {'gaps': ['Duplicate native stat 204:3351.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {'player_class': 'Sorceress', 'player_items': []}):
        assert not evaluate(ctx=ctx).annotations
    if role_id.startswith('strafe'):
        for ctx in ({'player_class': 'Amazon'}, {**context, 'player_items': ['Lava Gout']}):
            assert not evaluate(ctx=ctx).annotations
        assert evaluate(ctx={**context, 'player_items': ['Laying of Hands']}).annotations
