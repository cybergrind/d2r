from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'side', 'base', 'count', 'sockets', 'values'),
    [
        ('Memory', 'player', 'Battle Staff', 4, 4, {'83:1': 3, '107:58': 3}),
        ('Harmony', 'player', "Hunter's Bow", 7, 4, {'151:115': 10}),
        ('Wealth', 'player', 'Mage Plate', 4, 3, {'80:0': 100, '79:0': 300, '2:0': 10, '138:0': 2}),
        ('Wealth', 'merc', 'Mage Plate', 4, 3, {'80:0': 100, '79:0': 300, '2:0': 10}),
        (
            'Splendor',
            'player',
            'Bone Shield',
            5,
            2,
            {'127:0': 1, '105:0': 10, '102:0': 20, '80:0': 20, '79:0': 50, '27:0': 15, '1:0': 10},
        ),
    ],
)
def test_runeword_utility_keeps_completed_recipe_and_wearer_context(name, side, base, count, sockets, values):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == [name] and r['side'] == side and r['id'].endswith('-word-utility-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts(base, 'normal', name),
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

        assert set(evaluate(item).annotations) == set(values)
        if name == 'Wealth':
            for quality in ('superior', 'low_quality'):
                assert set(evaluate(replace(item, rarity=quality)).annotations) == set(values)
        assert bool(evaluate(replace(item, ethereal=True)).annotations) is (side == 'merc' or name == 'Memory')
        for change in ({'runeword': None}, {'sockets': sockets - 1}, {'socket_contents': 'empty'}, {'rarity': 'magic'}):
            assert not evaluate(replace(item, **change)).annotations
        if name == 'Harmony':
            amazon = replace(item, base_code=facts('Grand Matron Bow').base_code, item_type='abow')
            assert bool(evaluate(amazon).annotations) is (context['player_class'] == 'Amazon')
        if name == 'Splendor':
            necro = replace(item, base_code=facts('Preserved Head').base_code, item_type='head')
            assert bool(evaluate(necro).annotations) is (context['player_class'] == 'Necromancer')
            book = next(b for b in metadata()['bases'].values() if b['type'] == 'grim' and b['max_sockets'] >= 2)
            warlock = replace(item, base_code=book['code'], item_type='grim')
            assert bool(evaluate(warlock).annotations) is (context['player_class'] == 'Warlock')


def test_memory_prebuff_template_rejects_non_sorceress_class():
    with pytest.raises(ValueError, match='membership'):
        expand_profile(
            {
                'template': 'player_progression_equipment',
                'item': 'Memory',
                'class': 'Warlock',
                'side': 'player',
                'slot': 'Weapon-Swap',
            }
        )
