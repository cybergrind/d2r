from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('prefix', 'player_class'),
    [
        ('blizzard-standard', 'Sorceress'),
        ('blizzard-mf', 'Sorceress'),
        ('blizzard-set', 'Sorceress'),
        ('meteor-standard', 'Sorceress'),
        ('meteor-mf', 'Sorceress'),
        ('meteor-set', 'Sorceress'),
        ('meteor-ubers', 'Sorceress'),
        ('lightning-standard', 'Sorceress'),
        ('lightning-mf', 'Sorceress'),
        ('lightning-ubers', 'Sorceress'),
        ('abyss-warlock-build-guide-1', 'Warlock'),
        ('berserk-barbarian-1', 'Barbarian'),
        ('blessed-hammer-paladin-1', 'Paladin'),
        ('dragon-talon-assassin-1', 'Assassin'),
        ('fissure-druid-1', 'Druid'),
        ('lightning-fury-amazon-guide-1', 'Amazon'),
        ('poison-nova-necromancer-1', 'Necromancer'),
    ],
)
def test_annihilus_native_minimum_rolls_remain_useful(prefix, player_class):
    bundle = build()
    rid = prefix + '-annihilus'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = dict.fromkeys(('0:0', '1:0', '2:0', '3:0', '39:0', '41:0', '43:0', '45:0'), 10)
    values.update({'127:0': 1, '85:0': 5, '80:0': 50})
    item = replace(
        facts('Small Charm', 'unique', 'Annihilus'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': player_class}
    wanted = set(values) - {'80:0'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    for change in (
        {'name': 'Other'},
        {'rarity': 'magic'},
        {'identified': False},
        {'base_code': facts('Grand Charm').base_code},
    ):
        assert not evaluate(replace(item, **change)).annotations
    for context in ({}, {'player_class': 'Barbarian' if player_class == 'Sorceress' else 'Sorceress'}):
        assert not evaluate(context=context).annotations
    assert all(a['roll_quality'] == 'unassessed' for a in evaluate().annotations.values())
    demand = bundle['guide_demand']['summaries']['Annihilus']
    assert demand['distinct_builds'] >= 26
    assert demand['distinct_builds'] == len(set(demand['builds']))

    assert demand['builds'].count(role['build']) == 1
    assert demand['grade'] == 'Pending'
