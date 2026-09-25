import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('sword', "Sazabi's Cobalt Redeemer", 'Cryptic Sword', 'Ber Rune', ('93:0', '136:0')),
    ('armor', "Sazabi's Ghost Liberator", 'Balrog Skin', 'Ber Rune', ('7:0', '99:0', '36:0')),
    ('helm', "Sazabi's Mental Sheath", 'Basinet', 'Cham Rune', ('127:0', '39:0', '41:0', '153:0')),
]


@pytest.mark.parametrize(('suffix', 'name', 'base', 'rune', 'keys'), CASES)
def test_sazabi_piece_priorities_require_mercenary_set_and_socket(suffix, name, base, rune, keys):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == 'echoing-ubers-sazabi-' + suffix)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    assert set(role['important_stats']) == set(keys)
    stats = {key: {'status': 'decoded', 'value': 10} for row in CASES for key in row[4]}
    item = replace(
        facts(base, 'set', name),
        stats=stats,
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': rune, 'item_type': 'rune'}],
    )
    companions = [row[1] for row in CASES if row[1] != name]
    context = {'mercenary_type': 'Act 5 Frenzy', 'mercenary_items': companions}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == set(keys)
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
    assert all(
        a['desirability'] == ('supporting' if key in ('93:0', '127:0') else 'desirable')
        for key, a in result.annotations.items()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in keys:
        assert set(evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations) == set(
            keys
        ) - {key}
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'ring'},
        {'identified': False},
        {'stats': {}},
        {'socket_items': []},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'socket_items': [{'name': 'Ist Rune', 'item_type': 'rune'}]},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {**context, 'mercenary_type': 'Act 2 Might'}, {**context, 'mercenary_type': None}):
        assert not evaluate(ctx=ctx).annotations
    for companion in companions:
        assert not evaluate(
            ctx={**context, 'mercenary_items': [v for v in companions if v != companion], 'player_items': companions}
        ).annotations
