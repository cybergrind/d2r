from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'index', 'gold', 'attack'),
    [
        ('berserk-barbarian', 1, False, True),
        ('fire-warlock-guide', 2, False, False),
        ('gold-find-barbarian', 1, True, True),
        ('gold-find-barbarian', 2, True, False),
        ('gold-find-barbarian', 3, True, True),
    ],
)
def test_goldwrap_farming_utility_respects_role_and_cast_breakpoint(slug, index, gold, attack):
    bundle = build()
    rid = f'{slug}-{index}-goldwrap'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    item = replace(
        facts('Heavy Belt', 'unique', 'Goldwrap'),
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in [('80:0', 30), ('79:0', 50), ('93:0', 10), ('16:0', 60)]
        },
    )
    ctx = {'player_class': 'Warlock' if slug == 'fire-warlock-guide' else 'Barbarian', 'player_total_fcr': 105}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    wanted = {'80:0', '79:0'} | ({'93:0'} if attack else set())
    result = evaluate()
    assert set(result.annotations) == wanted
    assert result.annotations['79:0']['desirability'] == ('desirable' if gold else 'supporting')
    assert result.annotations['80:0']['desirability'] == ('supporting' if gold else 'desirable')
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    for change in ({'name': 'Other'}, {'rarity': 'magic'}, {'identified': False}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Sorceress', 'player_total_fcr': 105}).annotations
    assert not evaluate(context={}).annotations
    # Legal upgrades keep belt utility; neither upgrade nor ethereal grants a price premium.
    upgraded = replace(item, base_name='Battle Belt', base_code=facts('Battle Belt').base_code)
    assert set(evaluate(upgraded).annotations) == wanted
    if gold and index == 2:
        for fcr in (104, None, '105', True):
            assert not evaluate(context={**ctx, 'player_total_fcr': fcr}).annotations
    summary = bundle['guide_demand']['summaries']['Goldwrap']
    assert {'berserk-barbarian', 'fire-warlock-guide', 'gold-find-barbarian'} <= set(summary['builds'])
    assert summary['distinct_builds'] == len(set(summary['builds']))
