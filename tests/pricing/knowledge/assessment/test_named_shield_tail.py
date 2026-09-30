from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'slug', 'values'),
    [
        (
            "Griswold's Honor",
            'Vortex Shield',
            'zeal-paladin',
            {'31:0': 108, '102:0': 65, '20:0': 20, '39:0': 45, '41:0': 45, '43:0': 45, '45:0': 45, '80:0': 75},
        ),
        (
            "Trang-Oul's Wing",
            'Cantor Trophy',
            'poison-nova-necromancer',
            {'188:17': 2, '31:0': 125, '0:0': 25, '2:0': 15, '39:0': 45, '45:0': 40, '20:0': 30, '336:0': 25},
        ),
        (
            "Trang-Oul's Wing",
            'Cantor Trophy',
            'summoner-necromancer-guide',
            {'188:17': 2, '31:0': 125, '0:0': 25, '2:0': 15, '39:0': 45, '45:0': 40, '20:0': 30},
        ),
    ],
)
def test_named_shields_preserve_fillers_partial_sets_and_skill_tree(name, base, slug, values):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r['build'] == slug and r['id'].endswith('-named-shield-tail') and r.get('names') == [name]
    ]
    assert len(roles) == 1
    role = roles[0]
    context = {
        'player_class': 'Paladin' if name.startswith('Griswold') else 'Necromancer',
        'player_items': ["Trang-Oul's Claws", "Trang-Oul's Girth"],
    }
    item = replace(facts(base, 'set', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})
    if name.startswith('Griswold'):
        code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Ist Rune')
        children = [{'name': 'Ist Rune', 'base_code': code, 'unit_id': i + 1, 'position': i} for i in range(3)]
        item = replace(
            item, sockets=3, socket_contents='filled', filled_sockets=3, empty_sockets=0, socket_items=children
        )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]

    def evaluate(candidate, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(replace(item, ethereal=True)).annotations
    assert not evaluate(replace(item, rarity='unique')).annotations
    assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
    if name.startswith('Griswold'):
        assert not evaluate(replace(item, socket_items=children[:2])).annotations
        assert not evaluate(replace(item, socket_items=[children[0]] * 3)).annotations
        assert not evaluate(replace(item, socket_contents='empty')).annotations
    elif slug == 'poison-nova-necromancer':
        for companions in ([], ["Trang-Oul's Claws"] * 2, [name, "Trang-Oul's Claws"]):
            assert not evaluate(item, {**context, 'player_items': companions}).annotations
        assert not evaluate(item, {'player_class': 'Necromancer'}).annotations
    else:
        assert set(evaluate(item, {'player_class': 'Necromancer'}).annotations) == set(values)
        extra = replace(
            item,
            stats={
                **item.stats,
                '188:18': {'status': 'decoded', 'value': 2},
                '336:0': {'status': 'decoded', 'value': 25},
            },
        )
        assert set(evaluate(extra).annotations) == set(values)


def test_gargoyles_bite_sustains_throws_but_charges_are_not_a_passive_bonus():
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == ["Gargoyle's Bite"] and r['id'].endswith('-named-throwing-alternative')
    ]
    assert len(roles) == 2
    values = {'17:0': 230, '18:0': 230, '60:0': 15, '253:0': 30, '57:0': 300 / 256, '58:0': 300 / 256}
    item = replace(
        facts('Winged Harpoon', 'unique', "Gargoyle's Bite"),
        ethereal=True,
        stats={
            k: {
                'status': 'decoded',
                'value': v,
                **(
                    {'unit': 'replenishment_rate'}
                    if k == '253:0'
                    else {'unit': 'damage_per_frame'}
                    if k in ('57:0', '58:0')
                    else {}
                ),
            }
            for k, v in values.items()
        },
    )
    context = {'player_class': 'Barbarian'}
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert set(evaluate(replace(item, ethereal=False)).annotations) == set(values)
        assert not evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != '253:0'})).annotations
        assert not evaluate(replace(item, sockets=1)).annotations
        wrong = replace(item, stats={**item.stats, '253:0': {'status': 'decoded', 'value': 30, 'unit': 'seconds'}})
        assert not evaluate(wrong).annotations
