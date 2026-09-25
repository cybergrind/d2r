import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_fissure_pelts import facet, pelt, prepared


@pytest.mark.parametrize('variant', ['standard', 'magic-find'])
def test_pelt_annotations_preserve_skill_and_verified_socket_requirements(variant):
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == f'fissure-{variant}-pelt')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == profile['id']]
    assert len(configs) == 1

    def evaluate(item, context=None):
        context = {'player_class': 'Druid'} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [profile], context)
        )

    item = prepared()
    result = evaluate(item)
    assert set(result.annotations) == {'188:42', '107:234'}
    assert result.configurations[0]['role']['status'] == 'partial'
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    extra = {'107:250': {'status': 'decoded', 'value': 1}, '107:247': {'status': 'decoded', 'value': 1}}
    result = evaluate(replace(item, stats={**item.stats, **extra}))
    assert set(result.annotations) == {'188:42', '107:234'} | (set(extra) if variant == 'standard' else set())
    if variant == 'standard':
        assert all(result.annotations[k]['desirability'] == 'supporting' for k in extra)
    for key in item.stats:
        assert not evaluate(replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': 2}})).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in item.stats.items() if k != key}, capture_complete=False)
        ).annotations
    for invalid in (
        pelt(),
        replace(item, sockets=1),
        replace(item, socket_items=[facet(), facet()]),
        replace(item, socket_items=[item.socket_items[0], facet(element='cold')]),
        replace(item, socket_items=[item.socket_items[0]], stats={**item.stats, **facet()['stats']}),
        replace(item, socket_items=[item.socket_items[0], {'name': 'Rainbow Facet', 'item_type': 'jewl'}]),
    ):
        assert not evaluate(invalid).annotations
    for changes in ({'rarity': 'rare'}, {'ethereal': True}, {'ethereal': None}, {'identified': False}):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(item, context).annotations
