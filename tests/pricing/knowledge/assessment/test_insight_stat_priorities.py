import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role_id', 'merc'),
    [
        ('lightning-starter-insight-merc', 'Act 2 Holy Freeze'),
        ('nova-starter-insight-merc', 'Act 2 Holy Freeze'),
        ('nova-standard-insight-merc', 'Act 2 Might'),
        ('nova-mf-insight-merc', 'Act 2 Holy Freeze'),
        ('blizzard-starter-insight-merc', 'Act 2 Might'),
        ('blizzard-mf-insight-merc', 'Act 2 Might'),
        ('poison-starter-insight-merc', 'Act 2 Might'),
        ('poison-budget-insight-merc', 'Act 2 Might'),
        ('hammer-starter-insight-merc', 'Act 2 Holy Freeze'),
        ('hammer-standard-insight-merc', 'Act 2 Holy Freeze'),
        ('hammer-mf-insight-merc', 'Act 2 Holy Freeze'),
        ('hammer-ubers-insight-merc', 'Act 2 Holy Freeze'),
    ],
)
def test_insight_mana_priority_preserves_identity_recipe_and_merc_conditions(role_id, merc):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    stats = {
        '151:120': {'status': 'decoded', 'value': 12},
        '17:0': {'status': 'decoded', 'value': 230},
        '18:0': {'status': 'decoded', 'value': 230},
    }
    item = replace(facts('Bill', name='Insight'), runeword='Insight', sockets=4, socket_contents='filled', stats=stats)

    def evaluate(candidate, context=None):
        context = {'mercenary_type': merc} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, profiles, context)
        )

    for quality in ('normal', 'superior'):
        result = evaluate(replace(item, rarity=quality))
        assert set(result.annotations) == {'151:120'}
        assert result.annotations['151:120']['desirability'] == 'desirable'
        assert result.annotations['151:120']['roll_quality'] == 'unassessed'
        assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Infinity'},
        {'name': None},
        {'runeword': 'Infinity'},
        {'runeword': None},
        {'socket_contents': 'empty'},
        {'socket_contents': 'partial'},
        {'socket_contents': None},
        {'sockets': 3},
        {'sockets': None},
        {'rarity': 'magic'},
        {'item_type': 'bow'},
        {'identified': False},
        {'stats': {}},
        {'stats': {'151:120': {'status': 'decoded', 'value': 11}}},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'mercenary_type': 'Act 1 Cold'}):
        assert not evaluate(item, context).annotations
    assert (
        evaluate(replace(item, stats={'151:120': {'status': 'decoded', 'value': 17}})).annotations['151:120'][
            'roll_quality'
        ]
        == 'unassessed'
    )


def test_saved_insight_bill_supplies_native_aura_when_mercenary_context_is_known():
    from pricing.knowledge.assessment.engine import assess
    from pricing.knowledge.assessment.maintenance.replay import replay

    saved = replay('insight_bill')
    assert not saved['assessment']['stat_evaluation']['annotations']
    assessed = assess(saved['extraction'], loadout={'mercenary_type': 'Act 2 Might'})
    annotations = assessed['stat_evaluation']['annotations']
    assert set(annotations) == {'151:120'}
    assert annotations['151:120']['desirability'] == 'desirable'
    assert assessed['facts']['stats']['151:120']['value'] == 12
