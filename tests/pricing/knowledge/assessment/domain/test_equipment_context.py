from dataclasses import replace

import pytest

from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.roles.predicates import evaluate, native_keys, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {
    'op': 'equipped_item_matches',
    'field': 'player_equipment',
    'slot': 'amulet',
    'when': {
        'all': [
            {'op': 'fact_eq', 'field': 'item_type', 'value': 'amul'},
            {'op': 'fact_eq', 'field': 'rarity', 'value': 'crafted'},
            {'op': 'fact_eq', 'field': 'identified', 'value': True},
            {'op': 'stat_at_least', 'key': '105:0', 'value': 12, 'absent_is_zero': True},
        ]
    },
}


def amulet(value=12, **changes):
    return replace(facts('Amulet', 'crafted'), stats={'105:0': {'status': 'decoded', 'value': value}}, **changes)


def check(equipment, rule=RULE):
    return evaluate(rule, facts('Ring'), {'player_equipment': equipment}).truth


def test_equipped_combination_matches_one_slot_and_cannot_pool_items():
    assert check({'amulet': amulet()}) == 'true'
    assert check({'amulet': amulet(11)}) == 'false'
    assert check({'amulet': amulet(11), 'ring_left': amulet(20)}) == 'false'
    assert check({'amulet': amulet(20, rarity='rare'), 'ring_left': amulet()}) == 'false'
    assert check({'amulet': amulet(identified=False)}) == 'false'
    assert check({'amulet': replace(amulet(), item_type='ring')}) == 'false'
    assert list(native_keys(RULE)) == ['105:0']


def test_equipment_missing_empty_partial_and_malformed_have_distinct_truth():
    assert check({'amulet': None}) == 'false'
    for unknown in (None, {}, [], 'Amulet', {'amulet': 'Amulet'}, {'amulet': {}}, {'amulet': {'stats': []}}):
        assert check(unknown) == 'unknown'
    assert check({'amulet': replace(amulet(), stats={}, capture_complete=False)}) == 'unknown'
    assert check({'amulet': replace(amulet(), stats={})}) == 'false'
    for value in (True, '12', None, float('nan')):
        assert check({'amulet': amulet(value)}) == 'unknown'
    assert check({'amulet': replace(amulet(), gaps=['Duplicate native stat 105:0.'])}) == 'unknown'
    # A name list, total, hovered item or mercenary/swap amulet cannot prove the player's equipped amulet.
    for context in (
        {'player_items': ['Caster Amulet'], 'player_total_fcr': 200},
        {'mercenary_equipment': {'amulet': amulet()}},
        {'player_swap_equipment': {'amulet': amulet()}},
    ):
        assert evaluate(RULE, amulet(), context).truth == 'unknown'


def test_equipment_snapshot_copies_serializable_facts_and_freezes_nested_stats():
    raw = {'amulet': amulet().to_dict()}
    ctx = AssessmentContext.from_input({'player_equipment': raw})
    raw['amulet']['stats']['105:0']['value'] = 0
    assert evaluate(RULE, facts('Ring'), ctx).truth == 'true'
    with pytest.raises(TypeError):
        ctx.player_equipment['amulet'].value.stats['105:0']['value'] = 0


@pytest.mark.parametrize(
    'change',
    [
        {'field': 'player_items'},
        {'slot': 'inventory'},
        {'extra': 1},
        {'when': {'op': 'context_eq', 'field': 'player_class', 'value': 'Assassin'}},
        {'when': RULE},
        {'when': {'op': 'stat_at_least', 'key': 'invalid', 'value': 12}},
    ],
)
def test_invalid_equipment_predicates_fail_publication_validation(change):
    with pytest.raises(ValueError, match=r'Invalid equipped item|Equipment condition|Invalid native stat'):
        validate({**RULE, **change})


def test_equipment_maps_cannot_use_scalar_or_name_collection_operators():
    for op in ('context_eq', 'context_contains', 'context_count_at_least'):
        rule = {'op': op, 'field': 'player_equipment', 'value': 'Amulet'}
        if op == 'context_count_at_least':
            rule['count'] = 1
        with pytest.raises(ValueError, match=r'equipment snapshots|Membership requires|Invalid item count'):
            validate(rule)


def test_context_replacement_preserves_equipped_snapshot():
    context = AssessmentContext.from_input({'player_equipment': {'amulet': amulet(), 'ring_left': None}})
    copied = replace(context, player_class='Assassin')
    assert evaluate(RULE, facts('Ring'), copied).truth == 'true'
    assert evaluate({**RULE, 'slot': 'ring_left'}, facts('Ring'), copied).truth == 'false'


def test_equipped_socket_conditions_use_linked_jewel_not_totals_or_other_slots():
    jewel = {
        'item_type': facts('Jewel', 'magic').item_type,
        'stats_complete': True,
        'stats': {'93:0': {'status': 'decoded', 'value': 15}},
    }
    helmet = replace(facts('Casque', 'unique', 'Stealskull'), sockets=1, socket_contents='filled', socket_items=[jewel])
    rule = {
        **RULE,
        'slot': 'head',
        'when': {
            'all': [
                {'op': 'fact_eq', 'field': 'name', 'value': 'Stealskull'},
                {'op': 'socket_jewel_stat_at_least', 'key': '93:0', 'value': 15},
            ]
        },
    }
    assert check({'head': helmet}, rule) == 'true'
    assert list(native_keys(rule)) == ['93:0']
    assert check({'head': facts('Casque', 'unique', 'Stealskull')}, rule) == 'false'
    totals_only = replace(helmet, socket_items=[], stats=jewel['stats'])
    assert check({'head': totals_only, 'body': helmet}, rule) == 'unknown'
    assert check({'head': replace(helmet, sockets=0)}, rule) == 'unknown'
    assert check({'head': None}, rule) == 'false'
    assert check({}, rule) == 'unknown'
    context = AssessmentContext.from_input({'player_equipment': {'head': helmet.to_dict()}})
    assert evaluate(rule, facts('Ring'), context).truth == 'true'
    assert evaluate(rule, facts('Ring'), replace(context, player_class='Amazon')).truth == 'true'
    assert evaluate(rule, helmet, {'mercenary_equipment': {'head': helmet}}).truth == 'unknown'


@pytest.mark.parametrize('stats', [[], {'93:0': []}, {'93:0': {'status': 'decoded', 'value': True}}])
def test_malformed_equipped_jewel_stats_cannot_satisfy_dependency(stats):
    helmet = replace(
        facts('Casque', 'unique', 'Stealskull'),
        sockets=1,
        socket_contents='filled',
        socket_items=[{'item_type': facts('Jewel', 'magic').item_type, 'stats': stats}],
    )
    rule = {**RULE, 'slot': 'head', 'when': {'op': 'socket_jewel_stat_at_least', 'key': '93:0', 'value': 15}}
    assert check({'head': helmet}, rule) == 'unknown'
