import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('damage', 'pierce'), [(3, 3), (3, 5), (5, 3), (5, 5)])
def test_fire_facet_priorities_keep_low_rolls_and_recipient_advice(damage, pierce):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == 'hydra-standard-fire-facet')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        stats={
            '329:0': {'status': 'decoded', 'value': damage},
            '333:0': {'status': 'decoded', 'value': pierce},
        },
    )
    context = {'player_class': 'Sorceress', 'player_total_fcr': 105}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == {'329:0', '333:0'}
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    outcome = result.configurations[0]['role']
    assert outcome['status'] == 'partial'
    assert any('recipient' in text for text in outcome['missing'])
    assert [p['status'] for p in outcome['preferences']] == [
        'true' if pierce == 5 else 'false',
        'true' if damage == 5 else 'false',
    ]
    for key in item.stats:
        for value in (2, 6):
            assert not evaluate(
                replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value}})
            ).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in item.stats.items() if k != key}, capture_complete=False)
        ).annotations
    for changes in (
        {'name': None},
        {'name': 'Other'},
        {'rarity': 'rare'},
        {'item_type': 'ring'},
        {'identified': False},
        {'stats': {'330:0': {'status': 'decoded', 'value': 5}, '334:0': {'status': 'decoded', 'value': 5}}},
        {'gaps': ['Duplicate native stat 333:0.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in (
        {},
        {**context, 'player_class': 'Druid'},
        {**context, 'player_total_fcr': None},
        {**context, 'player_total_fcr': 104},
    ):
        assert not evaluate(ctx=ctx).annotations
