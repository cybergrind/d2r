from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'variant', 'base', 'values', 'excluded'),
    [
        (
            'Demon Machine',
            'Main alternatives',
            'Demon Crossbow',
            {'156:0': 66, '158:0': 6, '19:0': 632, '9:0': 36, '31:0': 321},
            {'17:0': 123, '18:0': 123, '22:0': 66},
        ),
        (
            'Kuko Shakaku',
            'Budget',
            'Cedar Bow',
            {'156:0': 50, '158:0': 7, '48:0': 40, '49:0': 180, '93:0': 20},
            {'188:0': 3, '107:27': 3, '17:0': 180, '18:0': 180},
        ),
        (
            "Butcher's Pupil",
            'Gear alternatives',
            'Small Crescent',
            {'17:0': 200, '18:0': 200, '93:0': 30, '141:0': 35, '135:0': 25},
            {},
        ),
        (
            'Hand of Blessed Light',
            'Main alternatives',
            'Divine Scepter',
            {'83:3': 2, '107:101': 4, '107:121': 2, '27:0': 15, '31:0': 50},
            {'17:0': 160, '18:0': 160, '119:0': 100},
        ),
        (
            'Hand of Blessed Light',
            'Holy Bolt Support',
            'Divine Scepter',
            {
                '83:3': 2,
                '107:101': 4,
                '107:121': 2,
                '27:0': 15,
                '31:0': 50,
                '99:0': 7,
                '39:0': 40,
                '41:0': 10,
                '43:0': 10,
                '45:0': 10,
                '114:0': 12,
            },
            {'17:0': 160, '18:0': 160},
        ),
        (
            "Heaven's Light",
            'Tri-Brid',
            'Mighty Scepter',
            {'83:3': 3, '93:0': 60, '136:0': 33, '194:0': 2},
            {'17:0': 300, '18:0': 300, '116:0': 33},
        ),
    ],
)
def test_delivery_modes_reject_irrelevant_damage_and_preserve_source_preparation(name, variant, base, values, excluded):
    b = build()
    roles = [
        r
        for r in b['profiles']
        if r.get('names') == [name] and r['variant'] == variant and r['id'].endswith('-delivery-weapon')
    ]
    assert len(roles) == 1
    role = roles[0]
    item = replace(
        facts(base, 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **excluded}.items()},
    )
    if name == 'Kuko Shakaku':
        item = replace(item, sockets=1, socket_contents='filled', filled_sockets=1, empty_sockets=0)
    if name == "Heaven's Light":
        item = replace(item, sockets=2, socket_contents='filled', filled_sockets=2, empty_sockets=0)
    if variant == 'Holy Bolt Support':
        keys = ('99:0', '39:0', '41:0', '43:0', '45:0', '114:0')
        child = {
            'name': 'Rare Jewel',
            'item_type': 'jewl',
            'unit_id': 1,
            'position': 0,
            'stats_complete': True,
            'stats': {k: item.stats[k] for k in keys},
        }
        item = replace(
            item,
            ethereal=True,
            sockets=1,
            socket_contents='filled',
            filled_sockets=1,
            empty_sockets=0,
            socket_items=[child],
        )
    context = {'player_class': role['must']['all'][0]['value']}
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == role['id']]

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, roles, context)
        )

    assert set(evaluate(item).annotations) == set(values)
    if name == 'Demon Machine':
        assert set(evaluate(replace(item, base_code=facts('Chu-Ko-Nu').base_code)).annotations) == set(values)
    if name == "Butcher's Pupil":
        assert (
            assess_roles(replace(item, base_code=facts('Cleaver').base_code), roles, context)[0]['dependencies'][0][
                'status'
            ]
            == 'false'
        )
    if name in ('Kuko Shakaku', "Heaven's Light"):
        low = replace(item, stats={**item.stats, '93:0': {'status': 'decoded', 'value': values['93:0'] - 1}})
        assert not evaluate(low).annotations
    if name == "Heaven's Light":
        better = replace(
            item,
            sockets=3,
            filled_sockets=3,
            stats={
                **item.stats,
                '93:0': {'status': 'decoded', 'value': 65},
                '194:0': {'status': 'decoded', 'value': 3},
            },
        )
        assert set(evaluate(better).annotations) == set(values)
    if variant == 'Holy Bolt Support':
        weaker = {**child, 'stats': {**child['stats'], '39:0': {'status': 'decoded', 'value': 39}}}
        assert not evaluate(replace(item, socket_items=[weaker])).annotations
        assert not evaluate(replace(item, ethereal=False)).annotations
    elif name != 'Hand of Blessed Light':
        assert not evaluate(replace(item, ethereal=True)).annotations
    for patch in ({'base_code': facts('Cap').base_code}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **patch)).annotations
