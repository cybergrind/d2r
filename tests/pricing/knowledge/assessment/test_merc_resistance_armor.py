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
        ('Smoke', 'Mage Plate', 23, 2, {'39:0': 50, '41:0': 50, '43:0': 50, '45:0': 50, '99:0': 20, '32:0': 250}),
        (
            'Duress',
            'Mage Plate',
            29,
            3,
            {
                '136:0': 15,
                '135:0': 33,
                '17:0': 10,
                '18:0': 10,
                '99:0': 40,
                '39:0': 15,
                '41:0': 15,
                '43:0': 45,
                '45:0': 15,
            },
        ),
        ('Rockstopper', 'Sallet', 22, 0, {'36:0': 10, '99:0': 30, '39:0': 20, '41:0': 20, '43:0': 20}),
        (
            'Goldskin',
            'Full Plate Mail',
            11,
            0,
            {'39:0': 35, '41:0': 35, '43:0': 35, '45:0': 35, '16:0': 120, '79:0': 100},
        ),
        ('Venom Ward', 'Breast Plate', 6, 0, {'45:0': 90, '46:0': 15, '110:0': 50, '16:0': 60}),
    ],
)
def test_mercenary_resistance_alternatives_accept_minimum_rolls_and_require_real_recipe(
    name, base, count, sockets, values
):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-merc-resistance-alternative')
    ]
    assert len(roles) == count
    unique = name not in ('Smoke', 'Duress')
    item = replace(
        facts(base, 'unique' if unique else 'normal', name),
        ethereal=True,
        sockets=sockets,
        runeword=None if unique else name,
        socket_contents='empty' if unique else 'filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '3:0': 15, '1:0': 10, '204:72': 18}.items()},
    )
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert set(evaluate(replace(item, ethereal=False)).annotations) == set(values)
        if not unique:
            for quality in ('superior', 'low_quality'):
                assert set(evaluate(replace(item, rarity=quality)).annotations) == set(values)
            assert not evaluate(replace(item, sockets=1)).annotations
            assert not evaluate(replace(item, socket_contents='empty')).annotations
            assert not evaluate(replace(item, rarity='magic')).annotations
        else:
            assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
