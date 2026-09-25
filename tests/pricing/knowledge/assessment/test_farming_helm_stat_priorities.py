import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_mercenary_farming_helms import CASES
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('role_id', 'name', 'base', 'rune', 'leech'), CASES)
def test_farming_helmet_stats_require_prepared_socket_and_source_setup(role_id, name, base, rune, leech):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    crown = name == 'Crown of Thieves'
    farming = '79:0' if crown else '80:0'
    values = {'60:0': leech, farming: 130 if crown else 55}
    if not crown:
        values['93:0'] = 10
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    stats['16:0'] = {'status': 'decoded', 'value': 200}
    item = replace(
        facts('Corona' if crown else base, 'unique', name),
        ethereal=True,
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': rune, 'item_type': 'rune'}],
        stats=stats,
    )
    merc = 'Act 2 Holy Freeze' if role_id.startswith('hammer-') else 'Act 2 Might'

    def evaluate(candidate, context=None):
        context = {'mercenary_type': merc} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    for ethereal in (True, False, None):
        result = evaluate(replace(item, ethereal=ethereal))
        assert set(result.annotations) == set(values)
        assert result.annotations[farming]['desirability'] == 'desirable'
        assert result.annotations['60:0']['desirability'] == 'supporting'
        assert result.configurations[0]['role']['status'] == 'partial'
        assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    for key in values:
        assert not evaluate(replace(item, stats={**stats, key: {'status': 'decoded', 'value': 0}})).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for changes in (
        {'socket_items': []},
        {'socket_contents': None},
        {'socket_contents': 'empty'},
        {'sockets': None},
        {'socket_items': [{'name': 'Tal Rune', 'item_type': 'rune'}]},
        {'name': None},
        {'name': 'Vampire Gaze'},
        {'rarity': 'rare'},
        {'identified': False},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'mercenary_type': 'Act 1 Cold'}):
        assert not evaluate(item, context).annotations
    if crown:
        assert not evaluate(replace(item, base_code=facts('Grand Crown').base_code)).annotations
