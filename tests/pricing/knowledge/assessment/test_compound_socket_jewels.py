from dataclasses import replace

import pytest

from pricing.knowledge.assessment.roles.predicates import evaluate, native_keys, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'socket_jewel_matches', 'stats': {'93:0': 15, '41:0': 30}}


def jewel(values, complete=True):
    return {
        'name': 'Jewel',
        'item_type': 'jewl',
        'stats_complete': complete,
        'stats': {key: {'status': 'decoded', 'value': value} for key, value in values.items()},
    }


def socketed(children):
    return replace(
        facts('Winged Helm', 'set', "Guillaume's Face"),
        sockets=len(children),
        socket_contents='filled',
        socket_items=children,
    )


def test_compound_rolls_must_belong_to_the_same_jewel():
    assert evaluate(RULE, socketed([jewel({'93:0': 15, '41:0': 30})])).truth == 'true'
    split = socketed([jewel({'93:0': 15}), jewel({'41:0': 30})])
    assert evaluate(RULE, split).truth == 'false'
    assert evaluate(RULE, socketed([jewel({'93:0': 15, '41:0': 29})])).truth == 'false'
    assert evaluate(RULE, socketed([jewel({'93:0': 15}, False)])).truth == 'unknown'
    assert evaluate(RULE, socketed([jewel({'93:0': 10}, False)])).truth == 'false'
    assert set(native_keys(RULE)) == {'93:0', '41:0'}


@pytest.mark.parametrize('stats', [{}, {'93:0': True}, {'93:0': float('nan')}, {'bad': 15}, []])
def test_invalid_compound_jewel_rule_cannot_be_published(stats):
    with pytest.raises(ValueError, match=r'predicate|threshold|native stat'):
        validate({**RULE, 'stats': stats})


@pytest.mark.parametrize('name', ['', ' ', None, 1])
def test_invalid_named_jewel_selector_cannot_be_published(name):
    with pytest.raises(ValueError, match='name'):
        validate({**RULE, 'name': name})


def test_budget_kicker_helmet_preserves_ias_and_lightning_resistance_payload():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.profiles import assess_roles

    profile = next((p for p in build()['profiles'] if p['id'] == 'dragon-talon-budget-guillaume'), None)
    assert profile is not None
    item = socketed([jewel({'93:0': 15, '41:0': 30})])
    context = {'player_class': 'Assassin'}
    result = assess_roles(item, [profile], context)[0]
    assert result['dependencies'][0]['status'] == 'true'
    assert result['status'] == 'partial'
    missing = replace(item, socket_items=[{'name': 'Jewel', 'item_type': 'jewl'}])
    assert assess_roles(missing, [profile], context)[0]['dependencies'][0]['status'] == 'unknown'
    low = socketed([jewel({'93:0': 15, '41:0': 29})])
    assert assess_roles(low, [profile], context)[0]['dependencies'][0]['status'] == 'false'
    assert assess_roles(item, [profile], {'player_class': 'Barbarian'})[0]['status'] == 'failed'
    assert not assess_roles(replace(item, name='Other helmet'), [profile], context)
