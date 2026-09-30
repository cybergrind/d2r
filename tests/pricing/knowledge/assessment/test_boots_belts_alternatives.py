from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'count', 'values'),
    [
        ("Natalya's Soul", 'Mesh Boots', 'set', 5, {'96:0': 40, '41:0': 15, '43:0': 15}),
        ("Sander's Riprap", 'Heavy Boots', 'set', 2, {'96:0': 40, '0:0': 5, '2:0': 10, '19:0': 100}),
        ("Trang-Oul's Girth", 'Troll Belt', 'set', 3, {'153:0': 1, '7:0': 66, '9:0': 25, '74:0': 5}),
        (
            "Nosferatu's Coil",
            'Vampirefang Belt',
            'unique',
            4,
            {'93:0': 10, '60:0': 5, '0:0': 15, '138:0': 2, '150:0': 10},
        ),
        ('Razortail', 'Sharkskin Belt', 'unique', 4, {'156:0': 33, '2:0': 15, '22:0': 10}),
        ('Goblin Toe', 'Light Plated Boots', 'unique', 4, {'136:0': 25, '34:0': 1, '35:0': 1}),
        ('Gore Rider', 'War Boots', 'unique', 5, {'136:0': 15, '135:0': 10, '96:0': 30, '141:0': 15}),
    ],
)
def test_attack_and_movement_alternatives_keep_native_benefits_and_skill_exceptions(name, base, quality, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-boots-belts-alternative')]
    assert len(roles) == count
    item = replace(facts(base, quality, name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        expected = set(values)
        if name == 'Gore Rider' and role['build'] == 'smite-paladin':
            expected.remove('141:0')
        assert set(evaluate(item).annotations) == expected
        for changes in (
            {'ethereal': True},
            {'sockets': 1},
            {'socket_contents': 'filled'},
            {'base_code': facts('Cap').base_code},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        if name == 'Gore Rider':
            assert set(evaluate(replace(item, base_code=facts('Myrmidon Greaves').base_code)).annotations) == expected
