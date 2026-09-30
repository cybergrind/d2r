from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values', 'excluded'),
    [
        ("Atma's Scarab", 'Amulet', 2, {'198:4226': 5, '119:0': 20, '45:0': 75}, set()),
        (
            "Astreon's Iron Ward",
            'Caduceus',
            1,
            {'188:24': 4, '34:0': 7, '17:0': 290, '18:0': 290, '93:0': 10, '136:0': 33, '111:0': 85},
            {'17:0', '18:0', '93:0', '136:0', '111:0'},
        ),
        (
            'Azurewrath',
            'Phase Blade',
            1,
            {
                '127:0': 1,
                '93:0': 30,
                '151:119': 13,
                '17:0': 270,
                '18:0': 270,
                '52:0': 250,
                '53:0': 500,
                '54:0': 250,
                '55:0': 500,
                '0:0': 10,
                '1:0': 10,
                '2:0': 10,
                '3:0': 10,
            },
            set(),
        ),
        (
            'Lightsabre',
            'Phase Blade',
            1,
            {'93:0': 20, '144:0': 25, '62:0': 7, '17:0': 200, '18:0': 200, '115:0': 1},
            set(),
        ),
        (
            'Fleshripper',
            'Fanged Knife',
            1,
            {'136:0': 25, '135:0': 50, '150:0': 20, '17:0': 300, '18:0': 300, '141:0': 33, '116:0': 50, '117:0': 1},
            {'17:0', '18:0', '141:0', '116:0', '117:0'},
        ),
    ],
)
def test_attack_utility_matches_actual_attack_or_spell_damage(name, base, count, values, excluded):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-attack-utility-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts(base, 'unique', name),
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k == '198:4226' else {})}
            for k, v in values.items()
        },
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
        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
        eth = replace(item, ethereal=True)
        assert set(evaluate(eth).annotations) == (expected if name == "Astreon's Iron Ward" else set())
        if name == 'Fleshripper':
            durable = replace(
                eth,
                sockets=1,
                socket_contents='filled',
                stats={**eth.stats, '152:0': {'status': 'decoded', 'value': 1}},
            )
            assert set(evaluate(durable).annotations) == expected
        if name == "Atma's Scarab":
            assert not evaluate(replace(item, sockets=1)).annotations
            bad = replace(
                item, stats={**item.stats, '198:4226': {'status': 'decoded', 'value': 5, 'unit': 'skill_level'}}
            )
            assert set(evaluate(bad).annotations) == expected - {'198:4226'}
