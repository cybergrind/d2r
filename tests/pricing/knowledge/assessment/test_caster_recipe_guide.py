from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'sockets', 'count', 'values'),
    [
        (
            'Obsession',
            'Archon Staff',
            6,
            6,
            {
                '127:0': 4,
                '105:0': 65,
                '99:0': 60,
                '39:0': 60,
                '41:0': 60,
                '43:0': 60,
                '45:0': 60,
                '76:0': 15,
                '27:0': 15,
                '80:0': 30,
                '79:0': 75,
                '1:0': 10,
                '3:0': 10,
            },
        ),
        ('Memory', 'Battle Staff', 4, 4, {'83:1': 3, '107:58': 3}),
        (
            'Splendor',
            'Bone Shield',
            2,
            2,
            {'127:0': 1, '105:0': 10, '102:0': 20, '80:0': 20, '79:0': 50, '27:0': 15, '1:0': 10},
        ),
        ('Lore', 'Cap', 2, 6, {'127:0': 1, '41:0': 30, '34:0': 7, '138:0': 2, '1:0': 10}),
        (
            'Stealth',
            'Quilted Armor',
            2,
            6,
            {'96:0': 25, '105:0': 25, '99:0': 25, '45:0': 30, '27:0': 15, '35:0': 3, '2:0': 6},
        ),
        ("Ancients' Pledge", 'Large Shield', 3, 6, {'39:0': 48, '41:0': 48, '43:0': 43, '45:0': 48}),
    ],
)
def test_caster_recipes_distinguish_completion_bases_and_spell_use(name, base, sockets, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-recipe-gear')]
    assert len(roles) == count
    item = replace(
        facts(base, 'normal', name),
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '60:0': 10, '93:0': 20, '81:0': 1}.items()},
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, configs=configs, role=role):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        expected = set(values)
        if name == 'Lore' and role['build'] == 'summoner-warlock-guide':
            expected.remove('138:0')
        assert set(evaluate(item).annotations) == expected
        assert bool(evaluate(replace(item, ethereal=True)).annotations) == (name in ('Obsession', 'Memory'))
        for patch in (
            {'runeword': None},
            {'rarity': 'magic'},
            {'socket_contents': 'empty'},
            {'sockets': sockets - 1},
            {'base_code': facts('Jewel').base_code},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
        if name == 'Memory':
            assert not evaluate(replace(item, base_code=facts('Gnarled Staff').base_code)).annotations
