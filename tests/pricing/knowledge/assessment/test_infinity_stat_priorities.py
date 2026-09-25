import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_infinity import infinity


@pytest.mark.parametrize(
    ('role_id', 'base', 'priorities'),
    [
        ('nova-standard-infinity-player', 'Scythe', {'334:0': 'desirable'}),
        (
            'nova-hybrid-infinity-merc',
            'Giant Thresher',
            {'151:123': 'desirable', '17:0': 'supporting', '18:0': 'supporting'},
        ),
        (
            'lightning-strike-infinity-player',
            'Matriarchal Spear',
            {'334:0': 'desirable', '17:0': 'supporting', '18:0': 'supporting'},
        ),
    ],
)
def test_infinity_priorities_belong_to_the_specific_beneficiary(role_id, base, priorities):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    item = infinity(base)
    item = replace(item, stats={**item.stats, '18:0': {'status': 'decoded', 'value': 300}})

    def evaluate(candidate, context=None):
        context = {'mercenary_type': 'Act 2 Might'} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    for quality in ('normal', 'superior'):
        result = evaluate(replace(item, rarity=quality))
        assert {k: v['desirability'] for k, v in result.annotations.items()} == priorities
        assert all(v['roll_quality'] == 'unassessed' for v in result.annotations.values())
        assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Insight'},
        {'name': None},
        {'runeword': 'Insight'},
        {'runeword': None},
        {'socket_contents': 'empty'},
        {'socket_contents': 'partial'},
        {'socket_contents': None},
        {'sockets': 3},
        {'sockets': None},
        {'rarity': 'magic'},
        {'identified': False},
        {'stats': {'151:123': {'status': 'decoded', 'value': 11}}},
        {'item_type': 'pole' if base == 'Matriarchal Spear' else 'aspe'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    if role_id == 'nova-hybrid-infinity-merc':
        for context in ({}, {'mercenary_type': 'Act 1 Cold'}, {'mercenary_type': 'Act 2 Blessed Aim'}):
            assert not evaluate(item, context).annotations
        assert set(evaluate(item, {'mercenary_type': 'Act 2 Holy Freeze'}).annotations) == set(priorities)
        assert '334:0' not in evaluate(item).annotations  # Wearer pierce does not support the player's damage.
    for key in ('17:0', '18:0'):
        incomplete = replace(item, stats={k: v for k, v in item.stats.items() if k != key}, capture_complete=False)
        assert not ({'17:0', '18:0'} & set(evaluate(incomplete).annotations))
    if '334:0' in priorities:
        unknown = replace(item, stats={**item.stats, '334:0': {'status': 'unresolved', 'value': 55}})
        assert '334:0' not in evaluate(unknown).annotations
