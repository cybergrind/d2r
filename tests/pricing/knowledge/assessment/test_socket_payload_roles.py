from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from pricing.knowledge.assessment.roles.predicates import evaluate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'socket_jewel_stat_at_least', 'key': '93:0', 'value': 15}


def helmet():
    return replace(
        facts('Great Helm', 'set', "Sigon's Visor"),
        sockets=1,
        socket_contents='filled',
        socket_items=[
            {
                'name': 'Jewel',
                'item_type': 'jewl',
                'stats': {'93:0': {'status': 'decoded', 'value': 15}},
                'stats_complete': True,
            }
        ],
    )


def test_socket_role_uses_individual_jewel_and_never_parent_ias():
    item = helmet()
    assert evaluate(RULE, item).truth == 'true'
    missing = replace(
        item, socket_items=[{'name': 'Jewel', 'item_type': 'jewl'}], stats={'93:0': {'status': 'decoded', 'value': 15}}
    )
    assert evaluate(RULE, missing).truth == 'unknown'
    for child in (
        {'name': 'Jewel', 'item_type': 'jewl', 'stats': {}, 'stats_complete': True},
        {'name': 'Rune', 'item_type': 'rune'},
    ):
        assert evaluate(RULE, replace(item, socket_items=[child])).truth == 'false'
    partial = replace(item, sockets=2, socket_items=[{'name': 'Rune', 'item_type': 'rune'}])
    assert evaluate(RULE, partial).truth == 'unknown'
    assert evaluate(RULE, replace(item, sockets=0, socket_contents='empty', socket_items=[])).truth == 'false'
    invalid = replace(item, sockets=0)
    assert evaluate(RULE, invalid).truth == 'unknown'


def test_double_throw_helmet_socket_dependency_can_be_verified():
    profile = next(
        p for p in build()['profiles'] if p['id'] == "double-throw-barbarian-guide-starter-set-Sigon's Visor"
    )
    context = {'player_class': 'Barbarian', 'player_items': ["Sigon's Gage", "Sigon's Sabot"]}
    result = assess_roles(helmet(), [profile], context)[0]
    assert any(
        d['label'] == 'Socket a jewel with at least 15% Increased Attack Speed.' and d['status'] == 'true'
        for d in result['dependencies']
    )
    assert not any('jewel' in m for m in result['missing'])


def test_socket_threshold_is_per_jewel_not_sum_and_invalid_values_stay_unknown():
    item = helmet()
    low = {
        'name': 'Jewel',
        'item_type': 'jewl',
        'stats': {'93:0': {'status': 'decoded', 'value': 10}},
        'stats_complete': True,
    }
    assert evaluate(RULE, replace(item, sockets=2, socket_items=[low, low])).truth == 'false'
    for value in (True, float('nan'), float('inf'), '15'):
        child = {**low, 'stats': {'93:0': {'status': 'decoded', 'value': value}}}
        assert evaluate(RULE, replace(item, socket_items=[child])).truth == 'unknown'
