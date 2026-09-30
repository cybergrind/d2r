import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_fissure_andariel import CONTEXT, helmet, jewel


@pytest.mark.parametrize('variant', ['standard', 'magic-find'])
def test_andariel_priorities_require_one_damage_jewel_and_companions(variant):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == f'fissure-merc-{variant}-andariel')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    stats = {
        k: {'status': 'decoded', 'value': v}
        for k, v in [('60:0', 8), ('0:0', 25), ('93:0', 35), ('17:0', 31), ('18:0', 31), ('16:0', 150)]
    }
    item = replace(helmet([jewel(31)]), stats=stats)

    def evaluate(candidate=item, context=CONTEXT):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    expected = set(stats) - {'16:0'}
    for ethereal in (True, False, None):
        result = evaluate(replace(item, ethereal=ethereal))
        assert set(result.annotations) == expected
        assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
        assert result.configurations[0]['role']['status'] == 'partial'
    for key in expected:
        wanted = expected - ({'17:0', '18:0'} if key in ('17:0', '18:0') else {key})
        assert set(evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations) == wanted
    for changes in (
        {'name': None},
        {'name': 'Other'},
        {'rarity': 'rare'},
        {'item_type': 'pelt'},
        {'identified': False},
        {'socket_items': []},
        {'socket_contents': 'empty'},
        {'socket_items': [jewel(30)]},
        {'socket_items': [jewel(41)]},
        {'sockets': 2, 'socket_items': [jewel(31, 0), jewel(0, 15)]},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in (
        {},
        {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'},
        {**CONTEXT, 'mercenary_items': ['Infinity']},
        {**CONTEXT, 'mercenary_items': [], 'player_items': CONTEXT['mercenary_items']},
    ):
        assert not evaluate(context=context).annotations
    assert evaluate(context={**CONTEXT, 'mercenary_type': 'Act 2 Holy Freeze'}).annotations
