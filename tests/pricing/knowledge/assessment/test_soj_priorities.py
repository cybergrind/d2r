from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'index', 'player_class', 'fcr'),
    [
        ('blizzard-sorceress', 1, 'Sorceress', 105),
        ('enchant-sorceress', 1, 'Sorceress', None),
        ('fissure-druid', 1, 'Druid', 99),
        ('fissure-druid', 2, 'Druid', None),
        ('fissure-druid', 3, 'Druid', None),
        ('lightning-sentry-assassin', 1, 'Assassin', 65),
        ('lightning-sorceress', 1, 'Sorceress', 117),
        ('nova-sorceress-guide', 1, 'Sorceress', 105),
        ('nova-sorceress-guide', 2, 'Sorceress', None),
        ('nova-sorceress-guide', 3, 'Sorceress', None),
        ('poison-nova-necromancer', 1, 'Necromancer', 125),
        ('poison-nova-necromancer', 2, 'Necromancer', 125),
        ('summoner-necromancer-guide', 1, 'Necromancer', 125),
        ('summoner-necromancer-guide', 2, 'Necromancer', 75),
    ],
)
def test_soj_skills_and_mana_preserve_build_context_without_lightning_spell_bonus(slug, index, player_class, fcr):
    bundle = build()
    rid = f'{slug}-{index}-soj'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    item = replace(
        facts('Ring', 'unique', 'The Stone of Jordan'),
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('127:0', 1), ('9:0', 20), ('77:0', 25), ('48:0', 1), ('49:0', 12)]
        },
    )
    ctx = {'player_class': player_class, 'player_total_fcr': fcr}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    wanted = {'127:0', '9:0', '77:0'}
    result = evaluate()
    assert set(result.annotations) == wanted
    assert result.annotations['127:0']['desirability'] == 'desirable'
    assert result.annotations['9:0']['desirability'] == 'supporting'
    assert result.annotations['77:0']['desirability'] == 'supporting'
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    for change in ({'name': 'Other'}, {'rarity': 'rare'}, {'identified': False}, {'ethereal': True}):
        assert not evaluate(replace(item, **change)).annotations
    for context in ({}, {'player_class': 'Barbarian', 'player_total_fcr': 200}):
        assert not evaluate(context=context).annotations
    if fcr:
        for value in (fcr - 1, None, str(fcr), True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
    # Missing breakpoint numbers are not inherited from a different variant.
    else:
        assert set(evaluate(context={**ctx, 'player_total_fcr': 0}).annotations) == wanted
    assert not role.get('preferences')  # Native modifiers are fixed; no invented perfect roll target.
    assert bundle['guide_demand']['summaries']['The Stone of Jordan']['distinct_builds'] >= 9
    assert bundle['guide_demand']['summaries']['The Stone of Jordan']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['The Stone of Jordan']['builds'])
    )

    assert bundle['guide_demand']['summaries']['The Stone of Jordan']['grade'] == 'Pending'
