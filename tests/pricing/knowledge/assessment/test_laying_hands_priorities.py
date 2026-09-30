from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('berserk-barbarian', 4, 'Barbarian'),
    ('dream-paladin', 0, 'Paladin'),
    ('dream-paladin', 1, 'Paladin'),
    ('mirrored-blades-warlock-guide', 1, 'Warlock'),
    ('mirrored-blades-warlock-guide', 2, 'Warlock'),
    ('strafe-amazon', 1, 'Amazon'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls'), MEMBERS)
def test_laying_hands_keeps_attack_setup_and_demon_damage_scope(slug, index, cls):
    bundle = build()
    rid = f'{slug}-{index}-laying-hands'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Bramble Mitts', 'set', 'Laying of Hands'),
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in {'93:0': 20, '121:0': 350, '39:0': 50, '17:0': 350}.items()
        },
    )
    ctx = {'player_class': cls}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'93:0', '121:0', '39:0'}
    assert evaluate().annotations['93:0']['desirability'] == 'desirable'
    assert evaluate().annotations['121:0']['desirability'] == 'desirable'
    assert evaluate().annotations['39:0']['desirability'] == 'supporting'
    assert any('demons' in c.lower() for c in role['conditions'])
    for change in ({'rarity': 'unique'}, {'ethereal': True}, {'identified': None}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    if slug == 'strafe-amazon':
        assert any('Fanaticism' in c and 'Hustle' in c for c in role['conditions'])
    if slug == 'dream-paladin' and index == 0:
        assert any('Weapon-Swap' in c for c in role['conditions'])
        assert evaluate(context={**ctx, 'player_total_fcr': 0}).annotations


def test_laying_hands_breadth_and_variant_exclusion():
    bundle = build()
    summary = bundle['guide_demand']['summaries'].get('Laying of Hands')
    assert summary is not None
    assert {
        'berserk-barbarian',
        'dream-paladin',
        'mirrored-blades-warlock-guide',
        'strafe-amazon',
        'zeal-paladin',
    } <= set(summary['builds'])
    assert summary['distinct_builds'] == len(set(summary['builds']))
    assert summary['grade'] == 'Pending'
    assert summary['lower_bound_grade'] == 'High'
    assert not any(p['id'] == 'dream-paladin-2-laying-hands' for p in bundle['profiles'])
