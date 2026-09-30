from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'slug', 'base', 'count', 'values', 'excluded'),
    [
        (
            'Black',
            'smite-paladin',
            'Flail',
            2,
            {'136:0': 40, '93:0': 15, '35:0': 2, '3:0': 10},
            {'17:0': 120, '18:0': 120, '19:0': 200, '54:0': 3, '55:0': 14},
        ),
        (
            'Black',
            'dragon-talon-assassin',
            'Flail',
            2,
            {'136:0': 40, '93:0': 15, '35:0': 2, '3:0': 10, '19:0': 200, '54:0': 3, '55:0': 14},
            {'17:0': 120, '18:0': 120},
        ),
        (
            'Kingslayer',
            'smite-paladin',
            'Phase Blade',
            1,
            {'136:0': 33, '135:0': 50, '93:0': 30, '0:0': 10},
            {'17:0': 270, '18:0': 270, '119:0': 20, '97:111': 1},
        ),
        (
            'Honor',
            'zeal-paladin',
            'Naga',
            1,
            {
                '17:0': 160,
                '18:0': 160,
                '19:0': 250,
                '141:0': 25,
                '127:0': 1,
                '60:0': 7,
                '0:0': 10,
                '74:0': 10,
                '138:0': 2,
            },
            {},
        ),
        (
            'Mist',
            'strafe-amazon',
            'Matriarchal Bow',
            1,
            {
                '17:0': 375,
                '18:0': 375,
                '127:0': 3,
                '151:113': 12,
                '156:0': 100,
                '93:0': 20,
                '119:0': 20,
                '3:0': 24,
                '39:0': 40,
                '41:0': 40,
                '43:0': 40,
                '45:0': 40,
                '188:0': 3,
            },
            {},
        ),
        (
            'Hand of Justice',
            'dream-paladin',
            'Phase Blade',
            2,
            {'17:0': 330, '18:0': 330, '93:0': 33, '151:102': 16, '333:0': 20, '115:0': 1, '141:0': 20, '60:0': 7},
            {'151:118': 30},
        ),
        (
            'Stone',
            'zeal-paladin',
            'Dusk Shroud',
            1,
            {
                '16:0': 260,
                '32:0': 300,
                '99:0': 60,
                '0:0': 16,
                '3:0': 16,
                '1:0': 10,
                '39:0': 15,
                '41:0': 15,
                '43:0': 15,
                '45:0': 15,
            },
            {},
        ),
        (
            'Strength',
            'strafe-amazon',
            'Partizan',
            1,
            {'17:0': 35, '18:0': 35, '136:0': 25, '60:0': 7, '0:0': 20},
            {'3:0': 10, '138:0': 2},
        ),
        (
            'Malice',
            'echoing-strike-warlock-guide',
            'Mythical Sword',
            1,
            {'135:0': 100, '17:0': 33, '18:0': 33, '19:0': 50, '116:0': 25},
            {'117:0': 1, '74:0': -5},
        ),
    ],
)
def test_source_recipe_uses_distinguish_attack_mode_bearer_and_legal_recipe(name, slug, base, count, values, excluded):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r['build'] == slug and r.get('names') == [name] and r['id'].endswith('-source-recipe')
    ]
    assert len(roles) == count
    for role in roles:
        n = next(c['value'] for c in role['must']['all'] if c.get('field') == 'sockets')
        item = replace(
            facts(base),
            name=name,
            runeword=name,
            sockets=n,
            socket_contents='filled',
            filled_sockets=n,
            ethereal=role['side'] == 'merc',
            stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **excluded}.items()},
        )
        context = {'player_class': role['must']['all'][0]['value']}
        if role['side'] == 'merc':
            context['mercenary_type'] = role['mercenary_type']
        if name == 'Malice':
            context['mercenary_items'] = [
                "Sazabi's Cobalt Redeemer",
                "Sazabi's Ghost Liberator",
                "Sazabi's Mental Sheath",
            ]
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, ctx=context, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        for patch in (
            {'sockets': n - 1},
            {'socket_contents': 'empty'},
            {'rarity': 'magic'},
            {'base_code': facts('Cap').base_code},
            {'runeword': None},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        if role['side'] == 'merc':
            assert not evaluate(item, {**context, 'mercenary_type': 'Act 1 Cold'}).annotations
        else:
            assert not evaluate(replace(item, ethereal=True)).annotations
        if name == 'Strength':
            assert set(evaluate(replace(item, ethereal=False)).annotations) == set(values)
        if name == 'Mist':
            assert not evaluate(replace(item, base_code=facts('Long Battle Bow').base_code)).annotations
