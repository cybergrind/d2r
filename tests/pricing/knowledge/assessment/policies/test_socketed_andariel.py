from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_fixed_socket_intrinsic import child
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def andariel(strength, leech, payload):
    return replace(
        facts('Demonhead', 'unique', "Andariel's Visage"),
        ethereal=True,
        sockets=1,
        socket_contents='filled',
        socket_items=[payload],
        stats={k: {'status': 'decoded', 'value': v} for k, v in {'0:0': strength, '60:0': leech}.items()},
    )


@pytest.mark.parametrize(
    ('name', 'strength', 'bonus'), [('Ral Rune', 30, 0), ('Fal Rune', 40, 10), ('Perfect Amethyst', 40, 10)]
)
def test_known_insert_preserves_native_andariel_rolls(name, strength, bonus):
    captured = andariel(strength, 10, child(name))
    result = assess_tier(captured)
    assert result['tier'] == 'high'
    assert result['intrinsic_rolls']['0:0'] == {'observed': strength, 'socket': bonus, 'intrinsic': 30}
    assert result['intrinsic_rolls']['60:0'] == {'observed': 10, 'socket': 0, 'intrinsic': 10}
    assert captured.stats['0:0']['value'] == strength
    assert '30 strength and 10%' in result['reasons'][0]


def test_jewel_strength_does_not_make_a_perfect_andariel():
    jewel = {
        'name': 'Jewel',
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {'0:0': {'status': 'decoded', 'value': 5}},
    }
    result = assess_tier(andariel(30, 10, jewel))
    assert result['intrinsic_rolls']['0:0']['intrinsic'] == 25
    assert result['reasons'] == ['Ethereal mercenary asking segment']


@pytest.mark.parametrize('failure', ['incomplete', 'unresolved', 'conflicting', 'out-of-range', 'missing'])
def test_unverified_or_impossible_andariel_intrinsic_rolls_remain_pending(failure):
    jewel = {
        'name': 'Jewel',
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {'0:0': {'status': 'decoded', 'value': 5}},
    }
    captured = andariel(30, 10, jewel)
    if failure == 'incomplete':
        captured = replace(captured, socket_items=[{**jewel, 'stats_complete': False}])
    elif failure == 'unresolved':
        captured = replace(captured, socket_items=[{**jewel, 'stats': {'0:0': {'status': 'unresolved'}}}])
    elif failure == 'conflicting':
        captured = replace(captured, socket_items=[{**child('Fal Rune'), 'name': 'Ral Rune'}])
    elif failure == 'out-of-range':
        captured = andariel(24, 10, child('Ral Rune'))
    else:
        captured = replace(captured, socket_items=[])
    assert assess_tier(captured)['tier'] is None
