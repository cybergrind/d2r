from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'sockets', 'count', 'common', 'extra', 'excluded'),
    [
        (
            'Leaf',
            'Long Staff',
            2,
            3,
            {'126:1': 3, '43:0': 33, '138:0': 2, '214:0': 2},
            {'enchant-sorceress': {'107:37': 3}},
            {'48:0': 5, '49:0': 30},
        ),
        (
            'Obsession',
            'Archon Staff',
            6,
            4,
            {
                '127:0': 4,
                '105:0': 65,
                '99:0': 60,
                '39:0': 70,
                '41:0': 70,
                '43:0': 70,
                '45:0': 70,
                '76:0': 25,
                '27:0': 30,
                '80:0': 30,
                '79:0': 75,
                '1:0': 10,
                '3:0': 10,
            },
            {},
            {'81:0': 1},
        ),
        (
            'Silence',
            'Great Poleaxe',
            6,
            1,
            {
                '127:0': 2,
                '17:0': 200,
                '18:0': 200,
                '62:0': 7,
                '99:0': 20,
                '39:0': 75,
                '41:0': 75,
                '43:0': 75,
                '45:0': 75,
                '80:0': 30,
                '138:0': 2,
                '122:0': 75,
                '124:0': 50,
            },
            {},
            {'93:0': 20, '113:0': 33, '112:0': 25},
        ),
        (
            'Void',
            'Fanged Knife',
            3,
            3,
            {'127:0': 2, '105:0': 40, '357:0': 15, '0:0': 12, '1:0': 12, '2:0': 12, '3:0': 12, '80:0': 30},
            {'abyss-warlock-build-guide': {'97:402': 3}},
            {'54:0': 3},
        ),
        (
            'Plague',
            'Cryptic Sword',
            3,
            3,
            {'127:0': 2, '151:109': 17},
            {
                'echoing-strike-warlock-guide': {'17:0': 320, '18:0': 320, '250:0': 0.375},
                'poison-nova-necromancer': {'336:0': 23},
            },
            {'93:0': 20, '135:0': 25, '134:0': 3},
        ),
        (
            'Crescent Moon',
            'Crystal Sword',
            3,
            4,
            {'334:0': 35, '147:0': 11, '138:0': 2},
            {'lightning-sentry-assassin': {'93:0': 20}},
            {'17:0': 220, '18:0': 220, '115:0': 1, '135:0': 25},
        ),
        (
            'Doom',
            'Cryptic Axe',
            5,
            1,
            {'127:0': 2, '17:0': 370, '18:0': 370, '141:0': 20, '151:114': 12},
            {},
            {'93:0': 45, '135:0': 25, '335:0': 60},
        ),
        (
            'Beast',
            'Berserker Axe',
            5,
            1,
            {'151:122': 9, '0:0': 40, '1:0': 10, '138:0': 2},
            {},
            {'17:0': 270, '18:0': 270, '93:0': 40, '136:0': 20, '135:0': 25},
        ),
    ],
)
def test_caster_words_keep_only_damage_and_speed_effects_for_the_actual_build(
    name, base, sockets, count, common, extra, excluded
):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-word-remainder')]
    assert len(roles) == count
    values = {**common, **excluded}
    for added in extra.values():
        values.update(added)
    item = replace(
        facts(base, 'normal', name),
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        filled_sockets=sockets,
        empty_sockets=0,
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        context = {'player_class': role['must']['all'][0]['value']}

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        expected = set(common) | set(extra.get(role['build'], {}))
        assert set(evaluate(item).annotations) == expected
        assert set(evaluate(replace(item, ethereal=True)).annotations) == expected
        for patch in (
            {'runeword': None},
            {'sockets': sockets - 1},
            {'socket_contents': 'empty'},
            {'base_code': facts('Cap').base_code},
            {'rarity': 'magic'},
        ):
            assert not evaluate(replace(item, **patch)).annotations
