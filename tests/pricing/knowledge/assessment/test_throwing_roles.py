from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('hand', ['weapon', 'offhand'])
def test_rare_throwing_planner_target_requires_sustain_and_correct_proc(hand):
    profile = next((p for p in build()['profiles'] if p['id'] == f'double-throw-rare-planner-{hand}'), None)
    assert profile is not None
    native = [(17, 0, 450), (18, 0, 450), (19, 0, 250), (93, 0, 40), (188, 32, 2), (253, 0, 10), (198, 4225, 5)]
    rows, _, unresolved = decode_stats([{'id': s, 'layer': layer, 'raw': v} for s, layer, v in native])
    assert not unresolved
    stats = {f'{r["memory_stat"]["id"]}:{r["memory_stat"]["layer"]}': r for r in rows if 'memory_stat' in r}
    # ED is displayed as one row but both native components remain assessment facts.
    stats.update({f'{s}:0': {'status': 'decoded', 'value': 450} for s in (17, 18)})
    context = {'player_class': 'Barbarian'}
    for base in ('Ghost Glaive', 'Winged Axe', 'Flying Axe'):
        item = replace(facts(base, 'rare'), ethereal=True, stats=stats)
        assert assess_roles(item, [profile], context)[0]['rule_trace']['truth'] == 'true'
    for key in stats:
        changed = replace(item, stats={k: v for k, v in stats.items() if k != key})
        expected = 'partial' if key in ('253:0', '198:4225') else 'failed'
        assert assess_roles(changed, [profile], context)[0]['status'] == expected
    for key, value in [('17:0', 449), ('93:0', 39), ('253:0', 0), ('198:4225', 4)]:
        changed = replace(item, stats={**stats, key: {**stats[key], 'value': value}})
        assert assess_roles(changed, [profile], context)[0]['status'] == 'failed'
    wrong_unit = replace(item, stats={**stats, '253:0': {**stats['253:0'], 'unit': 'seconds'}})
    assert assess_roles(wrong_unit, [profile], context)[0]['status'] == 'partial'
    assert assess_roles(replace(item, ethereal=False), [profile], context)[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='magic'), [profile], context)


def axe():
    return replace(
        facts('Balanced Axe', 'crafted'),
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('83:4', 1), ('93:0', 10), ('17:0', 80), ('18:0', 80), ('60:0', 4), ('7:0', 20)]
        },
    )


@pytest.mark.parametrize('hand', ['weapon', 'offhand'])
def test_double_throw_crafted_axe_keeps_planner_combination_and_cold_exclusion(hand):
    profile = next((p for p in build()['profiles'] if p['id'] == f'double-throw-starter-crafted-{hand}'), None)
    assert profile is not None
    item = axe()
    context = {'player_class': 'Barbarian'}
    result = assess_roles(item, [profile], context)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert all(p['status'] == 'true' for p in result['preferences'])
    for key in item.stats:
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert assess_roles(changed, [profile], context)[0]['status'] == 'failed'
    cold = replace(item, stats={**item.stats, '54:0': {'status': 'decoded', 'value': 1}})
    assert assess_roles(cold, [profile], context)[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='rare'), [profile], context)
    assert assess_roles(item, [profile], {'player_class': 'Amazon'})[0]['status'] == 'failed'
    assert assess_roles(replace(item, ethereal=True), [profile], context)[0]['status'] == 'failed'


@pytest.mark.parametrize('hand', ['weapon', 'offhand'])
def test_double_throw_cruel_elite_weapon_requires_magic_tier_and_native_damage(hand):
    profile = next((p for p in build()['profiles'] if p['id'] == f'double-throw-starter-cruel-{hand}'), None)
    assert profile is not None
    context = {'player_class': 'Barbarian'}
    for base in (
        'Winged Axe',
        'Winged Knife',
        'Ghost Glaive',
        'Hyperion Javelin',
        'Stygian Pilum',
        'Balrog Spear',
        'Flying Axe',
        'Flying Knife',
        'Winged Harpoon',
    ):
        item = replace(facts(base, 'magic'), stats={f'{s}:0': {'status': 'decoded', 'value': 201} for s in (17, 18)})
        assert assess_roles(item, [profile], context)[0]['rule_trace']['truth'] == 'true'
    for value in (200, 301):
        changed = replace(item, stats={f'{s}:0': {'status': 'decoded', 'value': value} for s in (17, 18)})
        assert assess_roles(changed, [profile], context)[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='rare'), [profile], context)
    ordinary = replace(facts('Balanced Axe', 'magic'), stats=item.stats)
    assert assess_roles(ordinary, [profile], context)[0]['status'] == 'failed'
    assert assess_roles(replace(item, ethereal=True), [profile], context)[0]['status'] == 'failed'
    missing = replace(item, stats={'17:0': item.stats['17:0']})
    assert assess_roles(missing, [profile], context)[0]['status'] == 'failed'
