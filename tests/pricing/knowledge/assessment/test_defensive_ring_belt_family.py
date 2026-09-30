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
        ('Dwarf Star', 'Ring', 12, {'142:0': 15, '35:0': 12, '7:0': 40}),
        ("Verdungo's Hearty Cord", 'Mithril Coil', 17, {'36:0': 10, '3:0': 30, '99:0': 10, '74:0': 10}),
        ('String of Ears', 'Demonhide Sash', 7, {'36:0': 10, '35:0': 10}),
        ("Thundergod's Vigor", 'War Belt', 12, {'42:0': 10, '145:0': 20, '0:0': 20, '3:0': 20}),
    ],
)
def test_defensive_alternatives_preserve_native_units_and_build_specific_benefits(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-defensive-alternative')]
    assert len(roles) == count
    for role in roles:
        expected = set(values)
        if name == 'String of Ears' and role['build'] in (
            'double-throw-barbarian-guide',
            'dragon-talon-assassin',
            'dream-paladin',
        ):
            expected.add('60:0')
        if name == 'Dwarf Star' and role['build'] == 'gold-find-barbarian':
            expected.add('79:0')
        if name == "Thundergod's Vigor":
            if role['build'] == 'lightning-fury-amazon-guide':
                expected.add('107:35')
            if role['build'] == 'lightning-strike-amazon':
                expected.add('107:34')
        extras = {'60:0': 6, '79:0': 100, '107:34': 3, '107:35': 3, '16:0': 200}
        item = replace(
            facts(base, 'unique', name),
            stats={k: {'status': 'decoded', 'value': v} for k, v in {**extras, **values}.items()},
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
        assert not evaluate(replace(item, sockets=1)).annotations
