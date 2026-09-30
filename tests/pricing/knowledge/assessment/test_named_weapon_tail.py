from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'count', 'values', 'excluded'),
    [
        (
            "Bartuc's Cut-Throat",
            'Greater Talons',
            'unique',
            2,
            {'83:6': 2, '99:0': 30, '0:0': 20, '2:0': 20, '188:50': 1, '17:0': 200, '60:0': 9},
            {'188:50', '17:0', '60:0'},
        ),
        (
            'Windforce',
            'Hydra Bow',
            'unique',
            1,
            {'17:0': 250, '18:0': 250, '218:0': 3.125, '93:0': 20, '62:0': 8, '81:0': 1, '0:0': 10, '2:0': 5},
            set(),
        ),
        (
            'Eaglehorn',
            'Crusader Bow',
            'unique',
            1,
            {'17:0': 200, '18:0': 200, '219:0': 2, '224:0': 6, '83:0': 1, '2:0': 25, '115:0': 1},
            set(),
        ),
        (
            "M'avina's Caster",
            'Grand Matron Bow',
            'set',
            1,
            {'17:0': 188, '18:0': 188, '93:0': 40, '19:0': 50, '188:0': 2, '52:0': 114},
            {'188:0', '52:0'},
        ),
        (
            'Widowmaker',
            'Ward Bow',
            'unique',
            1,
            {'97:22': 5, '17:0': 200, '18:0': 200, '141:0': 33},
            {'17:0', '18:0', '141:0'},
        ),
        (
            'Tomb Reaver',
            'Cryptic Axe',
            'unique',
            2,
            {
                '17:0': 280,
                '18:0': 280,
                '93:0': 60,
                '194:0': 3,
                '39:0': 50,
                '41:0': 50,
                '43:0': 50,
                '45:0': 50,
                '80:0': 80,
                '86:0': 14,
                '122:0': 230,
                '124:0': 350,
            },
            set(),
        ),
    ],
)
def test_named_weapon_priorities_follow_actual_build_damage_and_durability(
    name, base, quality, count, values, excluded
):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-weapon-tail-alternative')]
    assert len(roles) == count
    item = replace(
        facts(base, quality, name),
        sockets=3 if name == 'Tomb Reaver' else 0,
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
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

        expected = set(values) - excluded
        echoing = name == 'Tomb Reaver' and role['build'] == 'echoing-strike-warlock-guide'
        if echoing:
            expected.remove('93:0')
        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
        eth = replace(item, ethereal=True)
        assert set(evaluate(eth).annotations) == (expected if name == "Bartuc's Cut-Throat" or echoing else set())
        zod = replace(
            eth,
            sockets=max(1, item.sockets),
            stats={**eth.stats, '152:0': {'status': 'decoded', 'value': 1}},
            socket_contents='filled',
        )
        assert set(evaluate(zod).annotations) == (expected if name in ("Bartuc's Cut-Throat", 'Tomb Reaver') else set())
        if name == 'Tomb Reaver':
            for sockets in (1, 2, 3):
                assert set(evaluate(replace(zod, sockets=sockets)).annotations) == expected
            for sockets in (0, 4):
                assert not evaluate(replace(zod, sockets=sockets)).annotations
