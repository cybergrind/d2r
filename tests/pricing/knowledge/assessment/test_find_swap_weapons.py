from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'key', 'value'),
    [
        ('Gull', 'Dagger', 8, '80:0', 100),
        ('Blade of Ali Baba', 'Tulwar', 13, '240:0', 8),
    ],
)
def test_find_weapons_retain_passive_ethereal_and_socket_choices(name, base, count, key, value):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-find-weapon-alternative')]
    assert len(roles) == count
    for role in roles:
        expected = {key}
        if role['build'] == 'gold-find-barbarian':
            expected.add('239:0')
        sockets = 2 if name == 'Blade of Ali Baba' else 0
        item = replace(
            facts(base, 'unique', name),
            ethereal=True,
            sockets=sockets,
            stats={
                key: {'status': 'decoded', 'value': value},
                '239:0': {'status': 'decoded', 'value': 20},
                '17:0': {'status': 'decoded', 'value': 120},
            },
        )
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == expected
        assert set(evaluate(replace(item, ethereal=False)).annotations) == expected
        assert set(evaluate(replace(item, sockets=max(1, sockets), socket_contents='filled')).annotations) == expected
        assert not evaluate(replace(item, sockets=3)).annotations
        assert not evaluate(replace(item, rarity='rare')).annotations
        assert any('active weapon' in c for c in role['conditions'])
        assert any('attacks' in c for c in role['conditions'])
