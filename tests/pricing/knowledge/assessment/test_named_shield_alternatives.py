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
        (
            "Moser's Blessed Circle",
            'Round Shield',
            5,
            2,
            {'39:0': 25, '41:0': 25, '43:0': 25, '45:0': 25, '20:0': 25, '102:0': 30},
        ),
        ('Lidless Wall', 'Grim Shield', 17, 0, {'127:0': 1, '105:0': 20, '77:0': 10, '1:0': 10, '138:0': 3}),
    ],
)
def test_shield_alternatives_preserve_native_sockets_and_player_durability(name, base, count, sockets, values):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-shield-utility-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts(base, 'unique', name),
        sockets=sockets,
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, configs=configs, context=context):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        for changes in (
            {'ethereal': True},
            {'sockets': 3},
            {'base_code': facts('Buckler').base_code},
            {'rarity': 'rare'},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        if name == "Moser's Blessed Circle":
            assert set(evaluate(replace(item, socket_contents='filled')).annotations) == set(values)
            assert set(evaluate(replace(item, base_code=facts('Luna').base_code)).annotations) == set(values)
            assert not evaluate(replace(item, sockets=0)).annotations
