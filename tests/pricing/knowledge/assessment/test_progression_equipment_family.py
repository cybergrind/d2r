from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'sockets', 'values'),
    [
        ('Lore', 'Cap', 13, 2, {'127:0': 1, '41:0': 30, '34:0': 7, '138:0': 2, '1:0': 10}),
        (
            'Stealth',
            'Quilted Armor',
            12,
            2,
            {'96:0': 25, '105:0': 25, '99:0': 25, '45:0': 30, '27:0': 15, '35:0': 3, '2:0': 6},
        ),
        ("Ancients' Pledge", 'Large Shield', 8, 3, {'39:0': 48, '41:0': 48, '43:0': 43, '45:0': 48}),
        ('Ground', 'Crown', 7, 3, {'41:0': 40, '144:0': 10, '76:0': 5, '99:0': 20, '3:0': 10}),
    ],
)
def test_player_progression_alternatives_keep_recipe_and_rune_benefits(name, base, count, sockets, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-progression-equipment')]
    assert len(roles) == count
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        item = replace(
            facts(base, name=name),
            runeword=name,
            sockets=sockets,
            socket_contents='filled',
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        result = StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [role], context)
        )
        assert set(result.annotations) == set(values)


def test_early_ground_mercenary_use_does_not_promote_vitality():
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == ['Ground'] and r['side'] == 'merc' and r['variant'] == 'early'
    ]
    assert len(roles) == 15
    for role in roles:
        assert role['variant'] == 'early'
        assert set(role['important_stats']) == {'41:0', '144:0', '76:0', '99:0'}
        values = {'41:0': 40, '144:0': 10, '76:0': 5, '99:0': 20}
        item = replace(
            facts('Crown', 'low_quality', 'Ground'),
            runeword='Ground',
            sockets=3,
            socket_contents='filled',
            stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '3:0': 10}.items()},
        )
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        result = StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [role], context)
        )
        assert set(result.annotations) == set(values)
