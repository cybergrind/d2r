from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'sockets', 'count', 'values', 'excluded'),
    [
        ('Principle', 'Mage Plate', 3, 2, {'83:3': 2, '7:0': 150, '39:0': 30, '46:0': 5, '122:0': 50}, {'122:0'}),
        ('Peace', 'Mage Plate', 3, 2, {'83:0': 2, '99:0': 20, '43:0': 30, '97:9': 2}, set()),
        (
            'Hearth',
            'Bone Visage',
            3,
            2,
            {'153:0': 1, '43:0': 60, '148:0': 15, '76:0': 5, '16:0': 100, '99:0': 20, '3:0': 10, '149:0': 15},
            {'149:0'},
        ),
        ('Enlightenment', 'Mage Plate', 3, 1, {'83:1': 2, '97:37': 1, '39:0': 30, '34:0': 7, '16:0': 30}, set()),
        (
            'Authority',
            'Mage Plate',
            3,
            1,
            {'83:7': 2, '99:0': 20, '39:0': 30, '17:0': 60, '18:0': 60},
            {'17:0', '18:0'},
        ),
        ('Rain', 'Mage Plate', 3, 1, {'83:5': 2, '9:0': 150, '41:0': 30, '35:0': 7, '114:0': 15}, set()),
        (
            'Bramble',
            'Archon Plate',
            4,
            1,
            {
                '332:0': 50,
                '99:0': 50,
                '31:0': 300,
                '86:0': 13,
                '45:0': 100,
                '39:0': 30,
                '44:0': 5,
                '77:0': 5,
                '27:0': 15,
                '151:103': 21,
            },
            {'151:103'},
        ),
        (
            'Bone',
            'Mage Plate',
            3,
            1,
            {'83:2': 2, '9:0': 150, '39:0': 30, '41:0': 30, '43:0': 30, '45:0': 30, '34:0': 7},
            set(),
        ),
        (
            'Sanctuary',
            'Monarch',
            3,
            2,
            {
                '39:0': 70,
                '41:0': 70,
                '43:0': 70,
                '45:0': 70,
                '20:0': 20,
                '102:0': 20,
                '99:0': 20,
                '16:0': 160,
                '32:0': 250,
                '2:0': 20,
                '35:0': 7,
            },
            set(),
        ),
    ],
)
def test_support_runeword_roles_keep_native_bonuses_separate_from_unrelated_damage(
    name, base, sockets, count, values, excluded
):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-support-word-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts(base),
        name=name,
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
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

        assert set(evaluate(item).annotations) == set(values) - excluded
        for change in (
            {'ethereal': True},
            {'sockets': sockets - 1},
            {'socket_contents': 'empty'},
            {'rarity': 'magic'},
            {'runeword': None},
            {'base_code': facts('Phase Blade').base_code},
        ):
            assert not evaluate(replace(item, **change)).annotations
