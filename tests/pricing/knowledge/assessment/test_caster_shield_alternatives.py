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
        (
            "Que-Hegan's Wisdom",
            'Mage Plate',
            3,
            {'127:0': 1, '105:0': 20, '99:0': 20, '138:0': 3, '35:0': 10, '1:0': 15, '16:0': 160},
            set(),
        ),
        (
            "Death's Fathom",
            'Dimensional Shard',
            1,
            {'83:1': 3, '331:0': 30, '105:0': 20, '39:0': 40, '41:0': 40},
            set(),
        ),
        (
            'Snowclash',
            'Battle Belt',
            1,
            {'107:59': 2, '107:55': 3, '107:60': 2, '149:0': 15, '44:0': 15, '54:0': 13, '55:0': 21},
            {'54:0', '55:0'},
        ),
        (
            "Gerke's Sanctuary",
            'Pavise',
            1,
            {'34:0': 16, '35:0': 18, '20:0': 30, '39:0': 30, '41:0': 30, '43:0': 30, '45:0': 30, '74:0': 15},
            set(),
        ),
        (
            'Herald of Zakarum',
            'Gilded Shield',
            3,
            {
                '83:3': 2,
                '188:24': 2,
                '102:0': 30,
                '20:0': 30,
                '0:0': 20,
                '3:0': 20,
                '39:0': 50,
                '41:0': 50,
                '43:0': 50,
                '45:0': 50,
                '16:0': 200,
                '119:0': 20,
            },
            {'119:0'},
        ),
    ],
)
def test_caster_shields_and_armor_keep_skills_and_defenses_separate_from_attack_damage(
    name, base, count, values, excluded
):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-shield-alternative')
    ]
    assert len(roles) == count
    item = replace(facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})
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
        assert set(evaluate(replace(item, ethereal=True)).annotations) == (
            expected if name == "Death's Fathom" else set()
        )
        assert not evaluate(replace(item, sockets=2)).annotations
        if name == 'Herald of Zakarum':
            assert set(evaluate(replace(item, base_code=facts('Zakarum Shield').base_code)).annotations) == expected
