from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_baselines import assess_tier
from tests.pricing.knowledge.assessment.policies.test_fixed_socket_intrinsic import child
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def guardian(total, insert):
    return replace(
        facts('Templar Coat', 'unique', 'Guardian Angel'),
        ethereal=True,
        sockets=1,
        socket_contents='filled',
        socket_items=[child(insert)],
        stats={'16:0': {'status': 'decoded', 'value': total}},
    )


@pytest.mark.parametrize(
    ('total', 'insert', 'native', 'tier'),
    [
        (230, 'Pul Rune', 200, 'high'),
        (217, 'Pul Rune', 187, 'low'),
        (200, 'Ral Rune', 200, 'high'),
        (187, 'Ral Rune', 187, 'low'),
    ],
)
def test_guardian_native_ed_survives_insert_and_baseline_selection(total, insert, native, tier):
    result = assess_tier(guardian(total, insert))
    assert result['tier'] == tier
    assert result['intrinsic_rolls']['16:0'] == {'observed': total, 'socket': total - native, 'intrinsic': native}
    assert result['intrinsic_roll_ranges']['16:0']['min'] == 180
    assert result['intrinsic_roll_ranges']['16:0']['max'] == 200


def test_socket_augmented_200_ed_is_not_a_perfect_guardian():
    result = assess_tier(guardian(200, 'Pul Rune'))
    assert result['tier'] != 'high'
    assert result['variant']['tier'] is None


def test_unknown_insert_cannot_prove_native_guardian_premium():
    item = replace(guardian(200, 'Ral Rune'), socket_items=[])
    assert assess_tier(item)['tier'] != 'high'
