import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_fissure_pelts import facet
from tests.pricing.knowledge.assessment.roles.test_fissure_player_helmets import helmet
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'base'),
    [
        ('standard-flickering-flame', 'Antlers'),
        ('standard-flickering-flame', 'Bone Visage'),
        ('standard-flickering-flame', 'Diadem'),
        ('standard-ravenlore', 'Sky Spirit'),
        ('ubers-ravenlore', 'Sky Spirit'),
    ],
)
def test_fissure_helmets_keep_native_skill_identity_and_socket_rules(suffix, base):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == 'fissure-player-' + suffix)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    flame = 'flickering' in suffix
    keys = ['126:1', '333:0', '151:100', '9:0'] if flame else ['188:42', '333:0', '39:0', '41:0', '43:0', '45:0', '1:0']
    if suffix == 'ubers-ravenlore':
        keys.append('329:0')
    stats = {k: {'status': 'decoded', 'value': 10} for k in keys}
    stats.update({'16:0': {'status': 'decoded', 'value': 150}, '107:234': {'status': 'decoded', 'value': 1}})
    item = helmet('Flickering Flame', base, bonus=0) if flame else facts(base, 'unique', 'Ravenlore')
    item = replace(item, stats=stats)
    if suffix == 'ubers-ravenlore':
        item = replace(item, sockets=1, socket_contents='filled', socket_items=[facet()])
    expected = set(keys) | ({'107:234'} if flame and base == 'Antlers' else set())
    context = {'player_class': 'Druid'}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == expected
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    for key in expected:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations
        ) == expected - {key}
    for changes in (
        {'name': None},
        {'name': 'Other'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'rarity': 'magic'},
        {'item_type': 'phlm'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(ctx=ctx).annotations
    if flame:
        assert set(evaluate(replace(item, rarity='low_quality')).annotations) == expected
        for changes in ({'runeword': None}, {'runeword': 'Lore'}, {'sockets': 2}, {'socket_contents': 'empty'}):
            assert not evaluate(replace(item, **changes)).annotations
        assert not result.configurations[0]['role']['preferences']
    elif suffix == 'ubers-ravenlore':
        for changes in ({'socket_items': []}, {'socket_contents': 'empty'}, {'socket_items': [facet(element='cold')]}):
            assert not evaluate(replace(item, **changes)).annotations
