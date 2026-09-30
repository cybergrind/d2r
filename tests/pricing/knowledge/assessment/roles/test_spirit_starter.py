from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('blizzard-starter-spirit-sword', 'Crystal Sword', 'Sorceress'),
    ('lightning-starter-spirit-sword', 'Crystal Sword', 'Sorceress'),
    ('lightning-starter-spirit-shield', 'Monarch', 'Sorceress'),
    ('fissure-starter-spirit-sword', 'Crystal Sword', 'Druid'),
]


@pytest.mark.parametrize(('role_id', 'base', 'player_class'), CASES)
def test_completed_spirit_starter_use_keeps_base_recipe_and_build_requirements(role_id, base, player_class):
    bundle = build()
    role = next((p for p in bundle['profiles'] if p['id'] == role_id), None)
    assert role is not None, f'Missing reviewed role {role_id}'
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role_id
    ]
    assert len(configs) == 1
    keys = {'127:0': 2, '105:0': 25, '99:0': 55, '9:0': 89, '3:0': 22}
    if base == 'Monarch':
        keys.update({'41:0': 35, '43:0': 35, '45:0': 35})
    item = replace(
        facts(base, name='Spirit'),
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in keys.items()},
    )
    context = {'player_class': player_class, 'player_total_fcr': 117}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate().annotations) == set(keys)
    for ethereal in (False, True, None):
        assert set(evaluate(replace(item, ethereal=ethereal)).annotations) == set(keys)
    for quality in ('normal', 'superior'):
        assert set(evaluate(replace(item, rarity=quality)).annotations) == set(keys)
    for key in keys:
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert set(evaluate(missing).annotations) == set(keys) - {key}
    for changes in (
        {'name': 'Other'},
        {'runeword': None},
        {'sockets': 0},
        {'sockets': 3},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'rarity': 'magic'},
        {'identified': False},
        {'base_code': facts('Phase Blade').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={'player_class': 'Barbarian', 'player_total_fcr': 117}).annotations
    assert not evaluate(ctx={}).annotations
    if role_id.startswith('lightning'):
        assert not evaluate(ctx={'player_class': player_class}).annotations
        assert not evaluate(ctx={**context, 'player_total_fcr': 116}).annotations
    # Higher roll is useful but no perfect-roll threshold is inferred from the planner.
    best = replace(item, stats={**item.stats, '105:0': {'status': 'decoded', 'value': 35}})
    assert set(evaluate(best).annotations) == set(keys)
    assert all(v['roll_quality'] == 'unassessed' for v in evaluate(best).annotations.values())


def test_spirit_breadth_counts_builds_not_two_items_or_duplicate_variants():
    demand = build()['guide_demand']['summaries']['Spirit']
    assert {
        'blessed-hammer-paladin',
        'blizzard-sorceress',
        'fissure-druid',
        'fist-of-the-heavens-paladin',
        'lightning-sorceress',
        'meteor-sorceress',
    }.issubset(demand['builds'])
    assert demand['distinct_builds'] >= 6
    assert demand['distinct_builds'] == len(set(demand['builds']))

    assert demand['grade'] == 'Pending'
    assert demand['lower_bound_grade'] == 'High'
