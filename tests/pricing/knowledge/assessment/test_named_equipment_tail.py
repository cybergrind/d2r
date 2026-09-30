from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'count', 'sockets', 'values', 'excluded'),
    [
        ("Immortal King's Will", 'Avenger Guard', 'set', 3, 2, {'188:34': 2, '79:0': 37, '80:0': 40}, set()),
        (
            "Arreat's Face",
            'Slayer Guard',
            'unique',
            2,
            0,
            {
                '83:4': 2,
                '188:32': 2,
                '99:0': 30,
                '119:0': 20,
                '0:0': 20,
                '2:0': 20,
                '39:0': 30,
                '41:0': 30,
                '43:0': 30,
                '45:0': 30,
                '60:0': 6,
            },
            set(),
        ),
        (
            "Nightwing's Veil",
            'Spired Helm',
            'unique',
            1,
            0,
            {'127:0': 2, '331:0': 15, '2:0': 20, '149:0': 9, '118:0': 1},
            set(),
        ),
        (
            'Ravenlore',
            'Sky Spirit',
            'unique',
            1,
            0,
            {'188:42': 3, '333:0': 20, '39:0': 25, '41:0': 25, '43:0': 25, '45:0': 25, '1:0': 30, '107:221': 7},
            {'107:221'},
        ),
        ('Valkyrie Wing', 'Winged Helm', 'unique', 1, 0, {'83:0': 2, '96:0': 20, '99:0': 20, '138:0': 4}, set()),
        ('Giant Skull', 'Bone Visage', 'unique', 2, 2, {'81:0': 1, '136:0': 10, '0:0': 35, '194:0': 2}, set()),
        ("Sander's Taboo", 'Heavy Gloves', 'set', 2, 0, {'93:0': 20, '7:0': 40}, set()),
        (
            'Nightsmoke',
            'Belt',
            'unique',
            2,
            0,
            {'39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10, '9:0': 20, '114:0': 50, '34:0': 2},
            set(),
        ),
        (
            'Credendum',
            'Mithril Coil',
            'set',
            1,
            0,
            {'0:0': 10, '2:0': 10, '39:0': 15, '41:0': 15, '43:0': 15, '45:0': 15},
            set(),
        ),
        ("Trang-Oul's Guise", 'Bone Visage', 'set', 1, 0, {'99:0': 25, '9:0': 150, '74:0': 5}, set()),
        (
            "Trang-Oul's Scales",
            'Chaos Armor',
            'set',
            1,
            0,
            {'188:18': 2, '96:0': 40, '45:0': 40, '32:0': 100, '41:0': 50, '36:0': 25},
            {'41:0', '36:0'},
        ),
        (
            "M'avina's True Sight",
            'Diadem',
            'set',
            1,
            0,
            {'93:0': 30, '9:0': 25, '74:0': 10, '127:0': 1, '119:0': 50, '39:0': 25},
            {'127:0', '119:0', '39:0'},
        ),
        ("M'avina's Embrace", 'Kraken Shell', 'set', 1, 0, {'188:1': 2, '35:0': 12, '31:0': 350, '99:0': 30}, {'99:0'}),
        (
            "M'avina's Icy Clutch",
            'Battle Gauntlets',
            'set',
            1,
            0,
            {'0:0': 10, '2:0': 15, '118:0': 1, '54:0': 6, '55:0': 18, '331:0': 20},
            {'331:0'},
        ),
        ("M'avina's Tenet", 'Sharkskin Belt', 'set', 1, 0, {'96:0': 20, '62:0': 5, '39:0': 25}, {'39:0'}),
        ('Infernostride', 'Demonhide Boots', 'unique', 1, 0, {'79:0': 70, '96:0': 20, '39:0': 30, '40:0': 10}, set()),
        ('Lava Gout', 'Battle Gauntlets', 'unique', 1, 0, {'93:0': 20, '39:0': 24, '118:0': 1, '198:3338': 2}, set()),
        ('Manald Heal', 'Ring', 'unique', 1, 0, {'62:0': 7, '74:0': 8, '7:0': 20, '27:0': 20, '105:0': 10}, set()),
        (
            'Homunculus',
            'Heirophant Trophy',
            'unique',
            1,
            0,
            {
                '83:2': 2,
                '188:16': 2,
                '102:0': 30,
                '20:0': 40,
                '1:0': 20,
                '27:0': 33,
                '138:0': 5,
                '39:0': 40,
                '41:0': 40,
                '43:0': 40,
                '45:0': 40,
            },
            set(),
        ),
        (
            'Darkforce Spawn',
            'Bloodlord Skull',
            'unique',
            1,
            0,
            {'188:17': 3, '188:16': 3, '188:18': 3, '105:0': 30, '77:0': 10},
            set(),
        ),
    ],
)
def test_named_equipment_keeps_native_stats_separate_from_conditional_set_and_skill_effects(
    name, base, quality, count, sockets, values, excluded
):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-equipment-tail-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts(base, quality, name),
        sockets=sockets,
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
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
        if name == "Arreat's Face" and role['build'] == 'berserk-barbarian':
            expected.remove('60:0')
        assert set(evaluate(item).annotations) == expected
        for changes in ({'ethereal': True}, {'sockets': 3}, {'base_code': facts('Cap').base_code}):
            assert not evaluate(replace(item, **changes)).annotations
        if name == 'Giant Skull':
            one = replace(item, sockets=1, stats={**item.stats, '194:0': {'status': 'decoded', 'value': 1}})
            assert set(evaluate(one).annotations) == expected
        if name == 'Manald Heal':
            legacy = replace(item, stats={k: v for k, v in item.stats.items() if k != '105:0'})
            assert set(evaluate(legacy).annotations) == expected - {'105:0'}
        if name == 'Darkforce Spawn':
            annotations = evaluate(item).annotations
            assert annotations['188:17']['desirability'] == 'desirable'
            assert annotations['188:16']['desirability'] == 'supporting'
            assert annotations['188:18']['desirability'] == 'supporting'
