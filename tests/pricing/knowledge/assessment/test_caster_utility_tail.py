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
            "Death's Web",
            'Unearthed Wand',
            1,
            {'127:0': 2, '188:17': 2, '336:0': 50, '335:0': 50, '86:0': 12, '138:0': 12},
            {'335:0'},
        ),
        (
            "Mang Song's Lesson",
            'Archon Staff',
            3,
            {'127:0': 5, '105:0': 30, '27:0': 10, '333:0': 15, '334:0': 15, '335:0': 15},
            {'334:0', '335:0'},
        ),
        (
            "Ondal's Wisdom",
            'Elder Staff',
            3,
            {'127:0': 4, '105:0': 45, '1:0': 50, '31:0': 550, '85:0': 5, '35:0': 8},
            set(),
        ),
        (
            'Razorswitch',
            'Jo Staff',
            3,
            {
                '127:0': 1,
                '105:0': 30,
                '9:0': 175,
                '7:0': 80,
                '35:0': 15,
                '39:0': 50,
                '41:0': 50,
                '43:0': 50,
                '45:0': 50,
                '78:0': 15,
            },
            {'78:0'},
        ),
        ('Skull Collector', 'Rune Staff', 1, {'127:0': 2, '77:0': 20, '138:0': 20, '240:0': 1}, set()),
        (
            "Ars Al'Diabolos",
            'Blasphemous Grimoire',
            1,
            {'188:58': 2, '105:0': 25, '329:0': 25, '138:0': 10, '39:0': 30, '107:401': 5, '16:0': 200},
            set(),
        ),
        (
            "Ars Dul'Mephistos",
            'Occult Tome',
            1,
            {
                '83:7': 2,
                '105:0': 30,
                '99:0': 30,
                '16:0': 170,
                '80:0': 25,
                '17:0': 115,
                '18:0': 115,
                '119:0': 70,
                '358:0': 20,
            },
            {'17:0', '18:0', '119:0', '358:0'},
        ),
        (
            "Ars Tor'Baalos",
            'Blasphemous Compendium',
            1,
            {
                '188:56': 2,
                '107:374': 3,
                '107:380': 4,
                '107:379': 3,
                '107:381': 3,
                '16:0': 150,
                '216:0': 1.5,
                '36:0': 10,
            },
            set(),
        ),
        ('Entropy Locket', 'Amulet', 2, {'105:0': 10, '41:0': 40, '77:0': 15, '35:0': 12, '357:0': 10}, {'357:0'}),
        ('Sling', 'Ring', 1, {'105:0': 10, '358:0': 5, '1:0': 15, '80:0': 20, '150:0': 15}, {'150:0'}),
        (
            "Gheed's Wager",
            'Troll Belt',
            2,
            {
                '105:0': 20,
                '99:0': 20,
                '96:0': 20,
                '16:0': 150,
                '39:0': 15,
                '41:0': 15,
                '43:0': 15,
                '45:0': 15,
                '79:0': 75,
                '358:0': 7,
            },
            set(),
        ),
        (
            'Wraithstep',
            'Mirrored Boots',
            1,
            {'188:58': 1, '96:0': 30, '99:0': 20, '31:0': 60, '2:0': 15, '1:0': 15},
            set(),
        ),
        (
            'Opalvein',
            'Ring',
            1,
            {'105:0': 10, '39:0': 8, '41:0': 8, '43:0': 8, '45:0': 8, '86:0': 3, '138:0': 3, '357:0': 10},
            {'357:0'},
        ),
    ],
)
def test_caster_utility_priorities_distinguish_damage_types_and_random_skill_tabs(name, base, count, values, excluded):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-utility-alternative')
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
        if name == 'Entropy Locket' and role['build'] == 'echoing-strike-warlock-guide':
            expected.add('357:0')
        if name == "Mang Song's Lesson" and role['build'] != 'fire-warlock-guide':
            expected.remove('333:0')
        if name == "Gheed's Wager" and role['build'] != 'blessed-hammer-paladin':
            expected.remove('358:0')
        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
        assert set(evaluate(replace(item, ethereal=True)).annotations) == (
            expected
            if name in ("Death's Web", "Mang Song's Lesson", "Ondal's Wisdom", 'Razorswitch', 'Skull Collector')
            else set()
        )
        if name == 'Wraithstep':
            for tree in ('188:56', '188:57'):
                other = replace(
                    item,
                    stats={
                        **{k: v for k, v in item.stats.items() if k != '188:58'},
                        tree: {'status': 'decoded', 'value': 1},
                    },
                )
                assert set(evaluate(other).annotations) == expected - {'188:58'}
