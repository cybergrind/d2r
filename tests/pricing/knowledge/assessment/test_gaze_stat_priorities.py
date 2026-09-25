import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_vampire_gaze import IDS, gaze


@pytest.mark.parametrize('role_id', IDS)
def test_gaze_priorities_require_source_socket_mercenary_and_activity(role_id):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    rogue = role_id in IDS[:3]
    mephisto = role_id == IDS[-1]
    context = {'mercenary_type': 'Act 1 Cold' if rogue else 'Act 5 Frenzy'}
    if mephisto:
        context['activity'] = 'Uber Mephisto'
    item = gaze()
    if rogue:
        jewel = {
            'name': 'Scintillating Jewel of Fervor',
            'item_type': 'jewl',
            'stats_complete': True,
            'stats': {f'{k}:0': {'status': 'decoded', 'value': 15} for k in (93, 39, 41, 43, 45)},
        }
        item = replace(item, sockets=1, socket_contents='filled', socket_items=[jewel])
    elif role_id in IDS[-2:]:
        item = replace(
            item, sockets=1, socket_contents='filled', socket_items=[{'name': 'Um Rune', 'item_type': 'rune'}]
        )

    def evaluate(candidate, ctx=None):
        ctx = context if ctx is None else ctx
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, profiles, ctx)
        )

    for ethereal in (True, False, None):
        result = evaluate(replace(item, ethereal=ethereal))
        assert set(result.annotations) == {'60:0', '36:0'}
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
        assert result.configurations[0]['role']['status'] == 'partial'
    for key, minimum in (('60:0', 6), ('36:0', 15)):
        assert not evaluate(
            replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': minimum - 1}})
        ).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in item.stats.items() if k != key}, capture_complete=False)
        ).annotations
    for changes in ({'name': None}, {'name': 'Stealskull'}, {'rarity': 'rare'}, {'identified': False}):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {**context, 'mercenary_type': 'Act 2 Might'}):
        assert not evaluate(item, ctx).annotations
    if mephisto:
        for activity in (None, '', True, 'Uber Diablo', 'Mephisto'):
            assert not evaluate(item, {**context, 'activity': activity}).annotations
    if item.socket_items:
        assert not evaluate(replace(item, socket_items=[])).annotations
        assert not evaluate(replace(item, socket_contents='empty')).annotations
        if not rogue:
            assert not evaluate(replace(item, socket_contents=None)).annotations
        else:
            # A complete child capture proves this existential jewel requirement.
            assert set(evaluate(replace(item, socket_contents=None)).annotations) == {'60:0', '36:0'}
    if rogue:
        # Parent totals or two different jewels cannot prove one compound jewel.
        totals = {**item.stats, **jewel['stats']}
        prepared = evaluate(replace(item, stats=totals))
        assert set(prepared.annotations) == set(totals)
        assert not evaluate(replace(item, socket_items=[], stats=totals)).annotations
        split = [
            {**jewel, 'stats': {'93:0': jewel['stats']['93:0']}},
            {**jewel, 'stats': {k: v for k, v in jewel['stats'].items() if k != '93:0'}},
        ]
        assert not evaluate(replace(item, sockets=2, socket_items=split, stats=totals)).annotations
