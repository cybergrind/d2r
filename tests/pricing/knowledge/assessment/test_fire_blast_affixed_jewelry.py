from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('amulet', [True, False])
def test_fire_blast_jewelry_accepts_required_cast_rate_without_example_roll_minima(amulet):
    bundle = build()
    rid = 'fire-blast-standard-' + ('crafted-amulet' if amulet else 'rare-ring')
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'105:0': 15 if amulet else 10, '39:0': 5, '41:0': 5, '43:0': 5, '45:0': 5}
    values.update({'83:6': 1, '80:0': 5, '19:0': 100} if amulet else {'0:0': 1, '7:0': 5, '19:0': 100, '80:0': 5})
    item = replace(
        facts('Amulet' if amulet else 'Ring', 'crafted' if amulet else 'rare'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    phoenix = replace(facts('Monarch'), runeword='Phoenix')
    ctx = {'player_class': 'Assassin', 'player_total_fcr': 102, 'player_equipment': {'off_hand': phoenix}}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    wanted = set(values) - ({'19:0'} if amulet else {'19:0', '80:0'})
    assert set(evaluate().annotations) == wanted
    assert evaluate().annotations['105:0']['desirability'] == 'desirable'
    # The prose required threshold survives without planner strength/life/skills/MF rolls.
    minimal = replace(item, stats={'105:0': item.stats['105:0']})
    assert set(evaluate(minimal).annotations) == {'105:0'}
    assert not evaluate(
        replace(minimal, stats={'105:0': {'status': 'decoded', 'value': 10 if amulet else 9}})
    ).annotations
    assert not evaluate(replace(minimal, stats={}, capture_complete=False)).annotations
    if amulet:
        partial = replace(item, stats={k: v for k, v in item.stats.items() if k != '41:0'})
        assert set(evaluate(partial).annotations) == {'105:0', '83:6', '80:0'}
    for change in ({'rarity': 'magic'}, {'ethereal': True}, {'identified': False}):
        assert not evaluate(replace(item, **change)).annotations
    for context in (
        {},
        {**ctx, 'player_class': 'Sorceress'},
        {**ctx, 'player_total_fcr': 101},
        {**ctx, 'player_equipment': {}},
        {**ctx, 'player_equipment': {'off_hand': replace(phoenix, runeword='Spirit')}},
    ):
        assert not evaluate(context=context).annotations
    demand = bundle['guide_demand']['summaries']['pattern:' + rid]
    assert demand['scope'] == 'pattern'
    assert demand['distinct_builds'] == 1
