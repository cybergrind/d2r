import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    (f"{slug}-starter-set-Sigon's Gage", 'Gauntlets', "Sigon's Gage", klass, companions, '93:0', 30)
    for slug, klass, companions in [
        ('strafe-amazon', 'Amazon', ["Sigon's Visor", "Sigon's Sabot"]),
        ('double-throw-barbarian-guide', 'Barbarian', ["Sigon's Visor", "Sigon's Sabot"]),
        ('berserk-barbarian', 'Barbarian', ["Sigon's Wrap", "Sigon's Sabot"]),
    ]
] + [
    (
        "enchant-sorceress-starter-set-Death's Hand",
        'Leather Gloves',
        "Death's Hand",
        'Sorceress',
        ["Death's Guard"],
        '93:0',
        30,
    ),
    ("enchant-sorceress-starter-set-Death's Guard", 'Sash', "Death's Guard", 'Sorceress', ["Death's Hand"], '153:0', 1),
    ('strafe-amazon-deaths-guard-upgrade', 'Demonhide Sash', "Death's Guard", 'Amazon', [], '153:0', 1),
    (
        'double-throw-barbarian-guide-deaths-guard-upgrade',
        'Demonhide Sash',
        "Death's Guard",
        'Barbarian',
        [],
        '153:0',
        1,
    ),
]


@pytest.mark.parametrize(('role_id', 'base', 'name', 'klass', 'companions', 'key', 'value'), CASES)
def test_starter_priorities_keep_piece_companion_and_upgrade_gates(role_id, base, name, klass, companions, key, value):
    profiles = build()['profiles']
    role = next(p for p in profiles if p['id'] == role_id)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    context = {'player_class': klass, 'player_items': companions}
    item = replace(facts(base, 'set', name), stats={key: {'status': 'decoded', 'value': value}})

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == {key}
    assert result.annotations[key]['desirability'] == 'desirable'
    assert result.annotations[key]['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Other'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'ring'},
        {'identified': False},
        {'stats': {}},
        {'stats': {key: {'status': 'decoded', 'value': 0}}},
        {'gaps': [f'Duplicate native stat {key}.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={}).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Paladin'}).annotations
    for missing in companions:
        assert not evaluate(
            ctx={**context, 'player_items': [v for v in companions if v != missing], 'mercenary_items': companions}
        ).annotations
    if companions:
        assert not evaluate(ctx={'player_class': klass}).annotations
    if role_id.endswith('-upgrade'):
        # CBF remains on an unupgraded belt, but it does not satisfy this full upgrade configuration.
        sash = replace(item, base_code=facts('Sash').base_code, base_name='Sash')
        assert not evaluate(sash).annotations
        assert assess_role_results(sash, [role], context)[0].rule_trace['truth'] == 'true'
