from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def decoded(values):
    return {k: {'status': 'decoded', 'value': v} for k, v in values.items()}


@pytest.mark.parametrize('payload', ['cold', 'ruby', 'ist'])
def test_specialist_shield_preparation_and_verified_completed_setup(payload):
    bundle = build()
    prefix = 'frozen-orb-sorceress' if payload == 'cold' else 'zeal-paladin'
    stem = prefix + '-specialist-shield-' + payload
    roles = {r['id'].removeprefix(stem + '-'): r for r in bundle['profiles'] if r['id'].startswith(stem + '-')}
    assert set(roles) == {'empty', 'filled'}
    klass = 'Sorceress' if payload == 'cold' else 'Paladin'
    base = 'Monarch' if payload == 'cold' else 'Sacred Targe'
    # Native captured block contains base block plus Deflecting's 20 bonus.
    base_block = 22 if base == 'Monarch' else 30
    empty = replace(facts(base, 'magic'), sockets=4, stats=decoded({'20:0': base_block + 20, '102:0': 30}))
    values = {'331:0': 3, '335:0': 3} if payload == 'cold' else {'17:0': 31, '18:0': 31, '93:0': 15}
    filler = next(b for b in metadata()['bases'].values() if b['name'] == ('Ist Rune' if payload == 'ist' else 'Jewel'))
    children = [
        {
            'name': 'Rainbow Facet' if payload == 'cold' else filler['name'],
            'base_code': filler['code'],
            'item_type': filler['type'],
            'unit_id': i + 1,
            'position': i,
            'stats_complete': True,
            'stats': decoded({} if payload == 'ist' else values),
        }
        for i in range(4)
    ]
    totals = {'80:0': 100} if payload == 'ist' else {k: v * 4 for k, v in values.items()}
    filled = replace(empty, socket_contents='filled', socket_items=children, stats={**empty.stats, **decoded(totals)})

    def evaluate(item, stage, player=klass):
        role = roles[stage]
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        ctx = {'player_class': player}
        return StatsEvaluator().evaluate(item, configs, ctx, role_outcomes=assess_role_results(item, [role], ctx))

    assert evaluate(empty, 'empty').annotations
    assert not evaluate(replace(empty, stats=decoded({'20:0': base_block + 19, '102:0': 30})), 'empty').annotations
    assert not evaluate(empty, 'filled').annotations
    assert evaluate(filled, 'filled').annotations
    assert not evaluate(filled, 'empty').annotations
    for patch in (
        {'rarity': 'rare'},
        {'ethereal': True},
        {'sockets': 3},
        {'socket_items': children[:-1]},
        {'socket_items': [{**c, 'unit_id': 1} for c in children]},
        {'socket_items': [{**c, 'position': 0} for c in children]},
    ):
        assert not evaluate(replace(filled, **patch), 'filled').annotations
    assert not evaluate(filled, 'filled', 'Barbarian').annotations
    assert not assess_role_results(
        replace(filled, base_code=facts('Mage Plate').base_code), [roles['filled']], {'player_class': klass}
    )
    if payload != 'ist':
        for altered in (
            {**children[0], 'stats': decoded({})},
            {**children[0], 'stats': {}, 'stats_complete': False},
            {**children[0], 'stats': {**children[0]['stats'], **decoded({'20:0': 1})}},
        ):
            assert not evaluate(replace(filled, socket_items=[altered, *children[1:]]), 'filled').annotations
        if payload == 'ruby':
            # 30 ED is not a Ruby ED jewel, even with 15 IAS.
            bad = {**children[0], 'stats': decoded({'17:0': 30, '18:0': 30, '93:0': 15})}
            assert not evaluate(replace(filled, socket_items=[bad, *children[1:]]), 'filled').annotations
        else:
            assert not evaluate(
                replace(filled, socket_items=[{**c, 'name': 'Jewel'} for c in children]), 'filled'
            ).annotations
    else:
        assert not evaluate(replace(filled, stats={**filled.stats, **decoded({'80:0': 99})}), 'filled').annotations
