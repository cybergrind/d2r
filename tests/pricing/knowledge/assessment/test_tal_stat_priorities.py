import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('armor', "Tal Rasha's Guardianship", 'Lacquered Plate', ('80:0', '105:0', '39:0', '41:0', '43:0')),
    ('belt', "Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', ('80:0', '105:0')),
    ('amulet', "Tal Rasha's Adjudication", 'Amulet', ('41:0',)),
]


@pytest.mark.parametrize(('suffix', 'name', 'base', 'keys'), CASES)
def test_three_piece_tal_priorities_preserve_piece_bonus_and_full_loadout(suffix, name, base, keys):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == 'lightning-mf-tal-' + suffix)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role['id']]
    assert len(configs) == 1
    stats = {
        key: {'status': 'decoded', 'value': 10} for key in ('80:0', '105:0', '39:0', '41:0', '43:0', '45:0', '31:0')
    }
    item = replace(facts(base, 'set', name), stats=stats)
    if suffix == 'armor':
        item = replace(
            item, sockets=1, socket_contents='filled', socket_items=[{'name': 'Ist Rune', 'item_type': 'rune'}]
        )
    companions = [row[1] for row in CASES if row[1] != name]
    context = {'player_class': 'Sorceress', 'player_items': companions, 'player_total_fcr': 117}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == set(keys)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    for key in keys:
        reduced = evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key}))
        assert set(reduced.annotations) == set(keys) - {key}
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'ring'},
        {'identified': False},
        {'stats': {}},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in (
        {},
        {**context, 'player_class': 'Amazon'},
        {**context, 'player_total_fcr': 116},
        {**context, 'player_total_fcr': None},
    ):
        assert not evaluate(ctx=ctx).annotations
    for companion in companions:
        assert not evaluate(
            ctx={**context, 'player_items': [v for v in companions if v != companion], 'mercenary_items': companions}
        ).annotations
    if suffix == 'armor':
        for changes in (
            {'socket_items': []},
            {'socket_contents': 'empty'},
            {'socket_contents': None},
            {'socket_items': [{'name': 'Perfect Topaz'}]},
        ):
            assert not evaluate(replace(item, **changes)).annotations
