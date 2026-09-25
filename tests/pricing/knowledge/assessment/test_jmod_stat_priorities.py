import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


GROUPS = {
    'Sorceress': [
        'blizzard-sorceress-main-shield-jmod-base',
        'blizzard-sorceress-main-swap-jmod-base',
        'blizzard-sorceress-standard-swap-jmod-base',
        'lightning-sorceress-main-shield-jmod-base',
    ],
    'Amazon': [
        'lightning-fury-amazon-guide-main-shield-jmod-base',
        'lightning-fury-amazon-guide-ubers-shield-jmod-base',
        'lightning-strike-amazon-main-shield-jmod-base',
    ],
    'Druid': ['fissure-druid-main-shield-jmod-base', 'fissure-druid-magic-find-shield-jmod-base'],
    'Necromancer': ['poison-nova-necromancer-main-shield-jmod-base'],
    'Assassin': ['lightning-sentry-assassin-main-shield-jmod-base', 'lightning-sentry-assassin-main-swap-jmod-base'],
}


@pytest.mark.parametrize(('klass', 'roles'), GROUPS.items())
def test_jmod_markers_require_both_block_modifiers_and_four_empty_sockets(klass, roles):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id in roles]
    assert {c.role_id for c in configs} == set(roles)
    stats = {'20:0': {'status': 'decoded', 'value': 20}, '102:0': {'status': 'decoded', 'value': 30}}
    item = replace(facts('Monarch', 'magic'), sockets=4, socket_contents='empty', stats=stats)

    def evaluate(item, context=None):
        context = {'player_class': klass} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    result = evaluate(item)
    assert set(result.annotations) == set(stats)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    for config in result.configurations:
        assert config['role']['status'] == 'partial'
        payload = 'Ist' if config['role']['id'] == 'fissure-druid-magic-find-shield-jmod-base' else 'Rainbow Facets'
        assert any(payload in c for c in config['role']['missing'])
    for key in stats:
        assert not evaluate(
            replace(item, stats={**stats, key: {'status': 'decoded', 'value': stats[key]['value'] - 1}})
        ).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for sockets in (0, 1, 3, None):
        assert not evaluate(replace(item, sockets=sockets)).annotations
    for contents in ('filled', 'partial', None):
        assert not evaluate(replace(item, socket_contents=contents)).annotations
    for changes in (
        {'rarity': 'rare'},
        {'rarity': 'normal'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'base_code': facts('Kite Shield', 'magic').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(item, context).annotations
