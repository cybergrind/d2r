from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def recipe(name, base, sockets, values):
    return replace(
        facts(base, 'normal', name),
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        filled_sockets=sockets,
        empty_sockets=0,
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
            for k, v in values.items()
        },
    )


@pytest.mark.parametrize(('name', 'count'), [('Coven', 1), ('Dream', 2), ('Dragon', 1), ('Phoenix', 3), ('Exile', 1)])
def test_aura_recipes_keep_slot_effects_and_repair_distinct(name, count):
    b = build()
    roles = [r for r in b['profiles'] if r.get('names') == [name] and r['id'].endswith('-aura-recipe')]
    assert len(roles) == count
    for role in roles:
        slot = role['slot']
        if name == 'Coven':
            base, n, values, excluded = (
                'Diadem',
                3,
                {'127:0': 1, '105:0': 20, '16:0': 50, '80:0': 40, '86:0': 5, '39:0': 30, '3:0': 10},
                {},
            )
        elif name == 'Dream':
            base, n, values, excluded = (
                ('Diadem' if slot == 'Helmets' else 'Sacred Targe'),
                3,
                {
                    '151:118': 15,
                    '99:0': 30,
                    '217:0': 0.625,
                    '39:0': 20,
                    '41:0': 20,
                    '43:0': 20,
                    '45:0': 20,
                    '31:0': 220,
                    '16:0': 30,
                    '3:0': 10,
                    '80:0': 25,
                    ('76:0' if slot == 'Helmets' else '7:0'): (5 if slot == 'Helmets' else 50),
                },
                {},
            )
        elif name == 'Dragon':
            base, n, values, excluded = (
                'Mage Plate',
                3,
                {
                    '151:102': 14,
                    '31:0': 360,
                    '32:0': 230,
                    '220:0': 0.375,
                    '0:0': 5,
                    '1:0': 5,
                    '2:0': 5,
                    '3:0': 5,
                    '77:0': 5,
                    '42:0': 5,
                    '34:0': 7,
                },
                {},
            )
        elif name == 'Phoenix':
            base, n, values, excluded = (
                ('Crystal Sword' if slot == 'Weapon' else 'Monarch'),
                4,
                {
                    '333:0': 28,
                    '151:124': 15,
                    '143:0': 21,
                    '32:0': 400,
                    **({'40:0': 10, '42:0': 5, '7:0': 50} if slot == 'Off-Hand' else {}),
                },
                {'17:0': 400, '18:0': 400},
            )
        else:
            base, n, values, excluded = (
                'Sacred Targe',
                4,
                {
                    '151:104': 16,
                    '188:25': 2,
                    '102:0': 30,
                    '16:0': 260,
                    '252:0': 4,
                    '198:5253': 15,
                    '40:0': 5,
                    '44:0': 5,
                    '80:0': 25,
                    '74:0': 7,
                    '39:0': 45,
                    '41:0': 45,
                    '43:0': 45,
                    '45:0': 45,
                },
                {'188:24': 2},
            )
        item = recipe(name, base, n, {**values, **excluded})
        context = {'player_class': role['must']['all'][0]['value']}
        if name == 'Dream':
            context['player_equipment'] = {
                'off_hand' if slot == 'Helmets' else 'head': recipe(
                    'Dream', 'Sacred Targe' if slot == 'Helmets' else 'Diadem', 3, {'151:118': 15}
                )
            }
        configs = [
            configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        expected_eth = name == 'Exile' or (name == 'Phoenix' and slot == 'Weapon')
        assert bool(evaluate(replace(item, ethereal=True)).annotations) == expected_eth
        if name == 'Exile':
            assert not evaluate(
                replace(item, ethereal=True, stats={k: v for k, v in item.stats.items() if k != '252:0'})
            ).annotations
        for patch in (
            {'runeword': None},
            {'sockets': n - 1},
            {'base_code': facts('Cap').base_code},
            {'rarity': 'magic'},
        ):
            assert not evaluate(replace(item, **patch)).annotations


def test_dream_pair_requires_actual_complementary_equipment_not_inventory_names():
    roles = [r for r in build()['profiles'] if r.get('names') == ['Dream'] and r['id'].endswith('-aura-recipe')]
    assert len(roles) == 2
    for role in roles:
        head = role['slot'] == 'Helmets'
        other = 'off_hand' if head else 'head'
        item = recipe('Dream', 'Diadem' if head else 'Sacred Targe', 3, {'151:118': 15})
        context = {'player_class': 'Paladin', 'player_items': ['Dream', 'Dream']}
        assert assess_roles(item, [role], context)[0]['dependencies'][0]['status'] == 'unknown'
        for invalid in (None, item, recipe('Dream', 'Sacred Targe' if head else 'Diadem', 2, {'151:118': 15})):
            assert (
                assess_roles(item, [role], {**context, 'player_equipment': {other: invalid}})[0]['dependencies'][0][
                    'status'
                ]
                != 'true'
            )
