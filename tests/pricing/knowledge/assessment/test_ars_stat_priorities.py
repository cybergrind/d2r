import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('variant', 'rune'), [('standard', 'Um Rune'), ('mf', 'Ist Rune')])
def test_ars_priorities_keep_native_skills_and_variant_socket(variant, rune):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == f'fire-warlock-{variant}-ars-diabolos')
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    required = {'188:58': 2, '105:0': 25, '329:0': 15, '107:401': 3}
    stats = {k: {'status': 'decoded', 'value': v} for k, v in {**required, '138:0': 5, '39:0': 20, '80:0': 25}.items()}
    item = replace(
        facts('Blasphemous Grimoire', 'unique', "Ars Al'Diabolos"),
        stats=stats,
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': rune, 'item_type': 'rune'}],
    )
    context = {'player_class': 'Warlock'}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    expected = set(stats) - ({'80:0'} if variant == 'standard' else set())
    result = evaluate()
    assert set(result.annotations) == expected
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    assert all(
        a['desirability'] == ('supporting' if k in ('138:0', '39:0') else 'desirable')
        for k, a in result.annotations.items()
    )
    assert all(p['status'] == 'false' for p in result.configurations[0]['role']['preferences'])
    perfect = replace(
        item, stats={**stats, '329:0': {'status': 'decoded', 'value': 25}, '107:401': {'status': 'decoded', 'value': 5}}
    )
    assert all(p['status'] == 'true' for p in evaluate(perfect).configurations[0]['role']['preferences'])
    for key, minimum in required.items():
        assert not evaluate(
            replace(item, stats={**stats, key: {'status': 'decoded', 'value': minimum - 1}})
        ).annotations
        assert not evaluate(
            replace(item, stats={k: v for k, v in stats.items() if k != key}, capture_complete=False)
        ).annotations
    for optional in ('138:0', '39:0', '80:0'):
        assert set(
            evaluate(replace(item, stats={k: v for k, v in stats.items() if k != optional})).annotations
        ) == expected - {optional}
    for changes in (
        {'name': None},
        {'name': 'Other'},
        {'rarity': 'rare'},
        {'item_type': 'staf'},
        {'identified': False},
        {'ethereal': True},
        {'ethereal': None},
        {'socket_items': []},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'socket_items': [{'name': 'Ist Rune' if variant == 'standard' else 'Um Rune'}]},
        {'stats': {**{k: v for k, v in stats.items() if k != '188:58'}, '188:57': stats['188:58']}},
        {'gaps': ['Duplicate native stat 107:401.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(ctx=ctx).annotations
