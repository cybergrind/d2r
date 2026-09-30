from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('gold', [False, True])
def test_tal_mercenary_leech_and_gold_socket_require_the_correct_wearer(gold):
    b = build()
    rid = 'gold-find-budget-tal-merc' if gold else 'summoner-starter-tal-merc'
    role = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {
        '60:0': 10,
        '7:0': 60,
        '39:0': 15,
        '41:0': 15,
        '43:0': 15,
        '45:0': 15,
        '62:0': 10,
        '9:0': 30,
        '31:0': 45,
        '79:0': 10,
    }
    item = replace(
        facts('Death Mask', 'set', "Tal Rasha's Horadric Crest"),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
        sockets=1 if gold else 0,
        socket_contents='filled' if gold else 'empty',
        socket_items=[
            {'item_type': 'jewl', 'stats_complete': True, 'stats': {'79:0': {'status': 'decoded', 'value': 10}}}
        ]
        if gold
        else [],
    )
    ctx = {'mercenary_type': 'Act 2 Might'}
    wanted = {'60:0', '7:0', '39:0', '41:0', '43:0', '45:0'} | ({'79:0'} if gold else set())

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for context in ({}, {'mercenary_type': 'Act 3 Fire'}):
        assert not evaluate(context=context).annotations
    for patch in ({'ethereal': True}, {'identified': False}, {'rarity': 'unique'}):
        assert not evaluate(replace(item, **patch)).annotations
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    if gold:
        assert not evaluate(replace(item, socket_items=[])).annotations
        assert not evaluate(replace(item, socket_contents='empty')).annotations
    assert b['guide_demand']['summaries'][item.name]['distinct_builds'] >= 2
    assert b['guide_demand']['summaries'][item.name]['distinct_builds'] == len(
        set(b['guide_demand']['summaries'][item.name]['builds'])
    )
