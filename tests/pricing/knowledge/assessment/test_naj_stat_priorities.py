import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


BUILDS = (
    'abyss-warlock-build-guide',
    'double-throw-barbarian-guide',
    'lightning-fury-amazon-guide',
    'strafe-amazon',
    'fissure-druid',
    'summoner-necromancer-guide',
    'lightning-strike-amazon',
    'poison-nova-necromancer',
    'echoing-strike-warlock-guide',
    'dream-paladin',
    'mirrored-blades-warlock-guide',
    'fire-warlock-guide',
    'berserk-barbarian',
)


@pytest.mark.parametrize('build_id', BUILDS)
def test_naj_swap_priorities_require_available_charges_and_equipment(build_id):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == build_id + '-naj-teleport-swap')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    klass = next(p['value'] for p in role['must']['all'] if p.get('field') == 'player_class')
    context = {'player_class': klass, 'player_level': 78, 'player_strength': 44, 'player_dexterity': 37}
    item = replace(facts('Elder Staff', 'set', "Naj's Puzzler"), stats={'204:3467': charged(1)})

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == {'204:3467'}
    assert result.annotations['204:3467']['desirability'] == 'desirable'
    assert result.annotations['204:3467']['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'wand'},
        {'identified': False},
        {'ethereal': True},
        {'ethereal': None},
        {'stats': {}},
        {'stats': {'204:3467': charged(0)}},
        {'stats': {'204:3457': charged(1)}},
        {'stats': {'204:3467': {**charged(1), 'value': 2}}},
        {'gaps': ['Duplicate native stat 204:3467.']},
        {'sockets': 1, 'socket_contents': 'filled'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {**context, 'player_class': 'Sorceress'}, {**context, 'player_level': 77}, {'player_class': klass}):
        assert not evaluate(ctx=ctx).annotations
