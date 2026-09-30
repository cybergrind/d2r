from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'slot', 'base', 'count', 'sockets', 'values'),
    [
        (
            'Spirit',
            'Weapon',
            'Crystal Sword',
            7,
            4,
            {'127:0': 2, '105:0': 25, '99:0': 55, '9:0': 89, '3:0': 22, '147:0': 3, '32:0': 250},
        ),
        (
            'Spirit',
            'Off-Hand',
            'Monarch',
            6,
            4,
            {
                '127:0': 2,
                '105:0': 25,
                '99:0': 55,
                '9:0': 89,
                '3:0': 22,
                '147:0': 3,
                '32:0': 250,
                '41:0': 35,
                '43:0': 35,
                '45:0': 35,
            },
        ),
        (
            'Spirit',
            'Off-Hand-Swap',
            'Monarch',
            7,
            4,
            {
                '127:0': 2,
                '105:0': 25,
                '99:0': 55,
                '9:0': 89,
                '3:0': 22,
                '147:0': 3,
                '32:0': 250,
                '41:0': 35,
                '43:0': 35,
                '45:0': 35,
            },
        ),
        (
            'Heart of the Oak',
            'Weapon',
            'Flail',
            6,
            4,
            {
                '127:0': 3,
                '105:0': 40,
                '77:0': 15,
                '39:0': 30,
                '41:0': 30,
                '43:0': 30,
                '45:0': 30,
                '74:0': 20,
                '2:0': 10,
            },
        ),
        ('Call to Arms', 'Weapon-Swap', 'Crystal Sword', 7, 5, {'97:149': 1, '97:155': 2, '127:0': 1}),
    ],
)
def test_core_caster_words_separate_recipient_and_swap_rules(name, slot, base, count, sockets, values):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == [name] and r['slot'] == slot and r['id'].endswith('-core-caster-word-gear')
    ]
    assert len(roles) == count
    item = replace(
        facts(base, 'normal', name),
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**values, '60:0': 7, '62:0': 7, '93:0': 40, '17:0': 200, '18:0': 200, '48:0': 10}.items()
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

        assert set(evaluate(item).annotations) == set(values)
        for quality in ('superior', 'low_quality'):
            assert set(evaluate(replace(item, rarity=quality)).annotations) == set(values)
        shield = slot.startswith('Off-Hand')
        assert bool(evaluate(replace(item, ethereal=True)).annotations) == (not shield)
        for patch in (
            {'rarity': 'magic'},
            {'runeword': None},
            {'sockets': sockets - 1},
            {'socket_contents': 'empty'},
            {'base_code': facts('Jewel').base_code},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
        if name == 'Spirit':
            other = facts('Crystal Sword' if shield else 'Monarch')
            assert not evaluate(replace(item, base_code=other.base_code, item_type=other.item_type)).annotations
        if name == 'Call to Arms':
            assert not evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != '97:155'})).annotations
            wrong = facts('Matriarchal Bow')
            assert not evaluate(replace(item, base_code=wrong.base_code, item_type=wrong.item_type)).annotations
        if role.get('base_codes'):
            alternative = facts(
                'Broad Sword'
                if name == 'Spirit' and not shield
                else 'Knout'
                if name == 'Heart of the Oak'
                else 'Phase Blade'
                if name == 'Call to Arms'
                else 'Aegis'
            )
            assert not evaluate(
                replace(item, base_code=alternative.base_code, item_type=alternative.item_type)
            ).annotations
