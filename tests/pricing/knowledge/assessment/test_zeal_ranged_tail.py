from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'values', 'excluded'),
    [
        ('Leviathan', 'Kraken Shell', {'36:0': 25, '0:0': 50, '16:0': 200, '31:0': 150}, set()),
        (
            'Steelrend',
            'Ogre Gauntlets',
            {'17:0': 60, '18:0': 60, '136:0': 10, '0:0': 20, '31:0': 210, '93:0': 20},
            {'93:0'},
        ),
        ("Magnus' Skin", 'Sharkskin Gloves', {'93:0': 20, '19:0': 100, '39:0': 15, '16:0': 50}, set()),
        (
            "Razor's Edge",
            'Tomahawk',
            {'17:0': 225, '18:0': 225, '93:0': 40, '116:0': 33, '141:0': 50, '135:0': 50},
            set(),
        ),
        (
            'Alma Negra',
            'Sacred Rondache',
            {'83:3': 2, '102:0': 30, '20:0': 20, '35:0': 9, '119:0': 75, '17:0': 75, '18:0': 75, '16:0': 210},
            set(),
        ),
        (
            'Buriza-Do Kyanon',
            'Ballista',
            {
                '156:0': 100,
                '93:0': 80,
                '17:0': 200,
                '18:0': 200,
                '218:0': 2.5,
                '2:0': 35,
                '54:0': 32,
                '55:0': 196,
                '134:0': 3,
            },
            set(),
        ),
    ],
)
def test_zeal_and_ranged_gear_keep_native_base_damage_and_repairability(name, base, values, excluded):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-zeal-ranged-tail')]
    assert len(roles) == 1
    role = roles[0]
    context = {'player_class': role['must']['all'][0]['value']}
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(
        facts(base, 'set' if name == "Magnus' Skin" else 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(values) - excluded
    assert set(evaluate(replace(item, ethereal=True)).annotations) == (set())
    for change in ({'base_code': facts('Cap').base_code}, {'sockets': 3}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **change)).annotations
