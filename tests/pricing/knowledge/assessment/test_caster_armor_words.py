from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'sockets', 'values'),
    [
        (
            'Enigma',
            3,
            3,
            {
                '127:0': 2,
                '97:54': 1,
                '96:0': 45,
                '31:0': 750,
                '220:0': 0.75,
                '240:0': 1,
                '76:0': 5,
                '36:0': 8,
                '86:0': 14,
            },
        ),
        (
            'Chains of Honor',
            6,
            4,
            {
                '127:0': 2,
                '39:0': 65,
                '41:0': 65,
                '43:0': 65,
                '45:0': 65,
                '16:0': 70,
                '0:0': 20,
                '74:0': 7,
                '36:0': 8,
                '80:0': 25,
            },
        ),
    ],
)
def test_caster_armor_words_use_repairable_armor_and_recipient_stats(name, count, sockets, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-armor-gear')]
    assert len(roles) == count
    item = replace(
        facts('Archon Plate', 'normal', name),
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**values, '60:0': 8, '121:0': 200, '122:0': 100, '114:0': 15}.items()
        },
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, role=role, configs=configs):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        expected = set(values)
        if name == 'Enigma' and role['build'] == 'summoner-warlock-guide':
            expected.remove('86:0')
        assert set(evaluate(item).annotations) == expected
        for patch in (
            {'ethereal': True},
            {'ethereal': None},
            {'rarity': 'magic'},
            {'runeword': None},
            {'sockets': sockets - 1},
            {'socket_contents': 'empty'},
            {'base_code': facts('Jewel').base_code},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
        wrong = facts('Monarch')
        assert not evaluate(replace(item, base_code=wrong.base_code, item_type=wrong.item_type)).annotations
