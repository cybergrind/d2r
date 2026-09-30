import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('standard', 'magefist'),
    ('magic-find', 'magefist'),
    ('ubers', 'magefist'),
    ('standard', 'war-traveler'),
    ('magic-find', 'war-traveler'),
]


@pytest.mark.parametrize(('variant', 'kind'), CASES)
def test_fissure_accessory_priorities_preserve_upgrades_and_native_skill(variant, kind):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == f'fissure-player-{variant}-{kind}')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    gloves = kind == 'magefist'
    name = 'Magefist' if gloves else 'War Traveler'
    bases = (
        ['Light Gauntlets', 'Battle Gauntlets', 'Crusader Gauntlets'] if gloves else ['Battle Boots', 'Mirrored Boots']
    )
    values = {'126:1': 1, '105:0': 20, '27:0': 25} if gloves else {'80:0': 30, '96:0': 25, '0:0': 10, '3:0': 10}
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    context = {'player_class': 'Druid'}

    def evaluate(candidate, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    for base in bases:
        item = replace(facts(base, 'unique', name), stats=stats)
        result = evaluate(item)
        if variant == 'ubers' and base != 'Crusader Gauntlets':
            assert not result.annotations
            continue
        assert set(result.annotations) == set(values)
        assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
        assert all(
            a['desirability'] == ('desirable' if k in ('126:1', '105:0', '80:0') else 'supporting')
            for k, a in result.annotations.items()
        )
        assert result.configurations[0]['role']['status'] == 'partial'
        for key in values:
            assert set(evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations) == set(
                values
            ) - {key}
        for changes in (
            {'name': 'Other'},
            {'name': None},
            {'rarity': 'rare'},
            {'item_type': 'ring'},
            {'base_code': None},
            {'identified': False},
            {'ethereal': True},
            {'ethereal': None},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        for ctx in ({}, {'player_class': 'Sorceress'}):
            assert not evaluate(item, ctx).annotations
        if gloves:
            wrong_skill = {k: v for k, v in stats.items() if k != '126:1'}
            wrong_skill['126:2'] = stats['126:1']
            assert '126:2' not in evaluate(replace(item, stats=wrong_skill)).annotations
        else:
            assert (
                '80:0'
                in evaluate(replace(item, stats={**stats, '80:0': {'status': 'decoded', 'value': 50}})).annotations
            )
