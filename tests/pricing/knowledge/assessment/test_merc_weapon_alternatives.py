from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'base', 'sockets', 'values', 'excluded'),
    [
        (
            'Obedience',
            1,
            'Thresher',
            5,
            {
                '17:0': 370,
                '18:0': 370,
                '136:0': 40,
                '39:0': 30,
                '41:0': 30,
                '43:0': 30,
                '45:0': 30,
                '31:0': 300,
                '99:0': 40,
                '196:3349': 30,
                '333:0': 25,
            },
            {'333:0'},
        ),
        ('Pride', 3, 'Giant Thresher', 4, {'151:113': 20, '119:0': 300, '141:0': 20, '74:0': 8}, set()),
        (
            'Breath of the Dying',
            3,
            'War Pike',
            6,
            {
                '17:0': 400,
                '18:0': 400,
                '93:0': 60,
                '60:0': 15,
                '0:0': 30,
                '2:0': 30,
                '122:0': 200,
                '1:0': 30,
                '3:0': 30,
                '62:0': 7,
                '117:0': 1,
            },
            {'1:0', '3:0', '62:0', '117:0'},
        ),
        (
            'Faith',
            3,
            'Crusader Bow',
            4,
            {'151:122': 15, '127:0': 2, '17:0': 330, '18:0': 330, '39:0': 15, '41:0': 15, '43:0': 15, '45:0': 15},
            set(),
        ),
    ],
)
def test_mercenary_weapons_keep_bearer_stats_and_type_restrictions(name, count, base, sockets, values, excluded):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-merc-weapon-alternative')]
    assert len(roles) == count
    for role in roles:
        actual = (
            next(b['name'] for b in metadata()['bases'].values() if b['code'] == role['base_codes'][0])
            if role.get('base_codes')
            else base
        )
        item = replace(
            facts(actual, 'normal', name),
            runeword=name,
            sockets=sockets,
            socket_contents='filled',
            stats={
                k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('196:') else {})}
                for k, v in values.items()
            },
        )
        context = {'player_class': role['must']['all'][0]['value'], 'mercenary_type': role['mercenary_type']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, ctx=None, role=role, context=context, configs=configs):
            ctx = context if ctx is None else ctx
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        expected = set(values) - excluded
        assert set(evaluate(item).annotations) == expected
        assert set(evaluate(replace(item, ethereal=True)).annotations) == (set() if name == 'Faith' else expected)
        for change in (
            {'socket_contents': 'empty'},
            {'sockets': sockets - 1},
            {'runeword': None},
            {'base_code': facts('Crystal Sword').base_code},
        ):
            assert not evaluate(replace(item, **change)).annotations
        assert not evaluate(item, {**context, 'mercenary_type': 'Act 5 Frenzy'}).annotations
        if name == 'Faith':
            crossbow = replace(item, base_code=facts('Colossus Crossbow').base_code, item_type='xbow')
            assert not evaluate(crossbow).annotations
