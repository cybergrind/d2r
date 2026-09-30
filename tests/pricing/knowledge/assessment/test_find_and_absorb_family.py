from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values'),
    [
        ('Wisp Projector', 'Ring', 9, {'144:0': 10, '80:0': 10}),
        ('Frostburn', 'Gauntlets', 3, {'77:0': 40}),
        ('Chance Guards', 'Chain Gloves', 17, {'80:0': 25}),
        ('Goldwrap', 'Heavy Belt', 18, {'80:0': 30}),
    ],
)
def test_find_and_absorb_gear_does_not_promote_unrelated_attack_or_charge_benefits(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-find-absorb-alternative')]
    assert len(roles) == count
    for role in roles:
        expected = set(values)
        if name in ('Goldwrap', 'Chance Guards') and role['build'] == 'gold-find-barbarian':
            expected.add('79:0')
        if name == 'Goldwrap' and role['build'] in (
            'berserk-barbarian',
            'double-throw-barbarian-guide',
            'dream-paladin',
            'strafe-amazon',
            'mirrored-blades-warlock-guide',
            'fire-blast-assassin',
            'lightning-sentry-assassin',
            'wake-of-fire-assassin',
        ):
            expected.add('93:0')
        item = replace(
            facts(base, 'unique', name),
            stats={
                k: {'status': 'decoded', 'value': v}
                for k, v in {
                    '93:0': 10,
                    '79:0': 200,
                    '17:0': 20,
                    '18:0': 20,
                    '16:0': 30,
                    '204:226': 5,
                    **values,
                }.items()
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
        assert not evaluate(replace(item, ethereal=True)).annotations
        assert not evaluate(replace(item, rarity='rare')).annotations
        assert not evaluate(replace(item, sockets=1)).annotations
