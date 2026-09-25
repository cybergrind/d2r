from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_socketed_elemental_uniques import item
from tests.pricing.knowledge.assessment.policies.test_socketed_ravenlore import raven


def child(name):
    base = next(b for b in metadata()['bases'].values() if b['name'] == name)
    return {'name': name, 'base_code': base['code'], 'item_type': base['type'], 'stats_complete': False, 'stats': {}}


@pytest.mark.parametrize('name', ['Ko Rune', 'Perfect Emerald'])
def test_known_helmet_dexterity_bonus_is_not_an_intrinsic_nightwing_roll(name):
    captured = item("Nightwing's Veil", {'331:0': 15, '2:0': 30}, {})
    result = assess_tier(replace(captured, socket_items=[child(name)]))
    assert result['tier'] == 'high'
    assert result['intrinsic_rolls']['2:0']['intrinsic'] == 20
    assert result['intrinsic_rolls']['2:0']['socket'] == 10


def test_um_does_not_change_ravenlore_fire_pierce():
    result = assess_tier(replace(raven(20), socket_items=[child('Um Rune')]))
    assert result['tier'] == 'high'
    assert result['intrinsic_rolls']['333:0']['socket'] == 0


@pytest.mark.parametrize('change', ['name', 'base_code', 'item_type'])
def test_conflicting_child_identity_stays_pending(change):
    payload = child('Um Rune')
    payload[change] = 'not-the-captured-child'
    assert assess_tier(replace(raven(20), socket_items=[payload]))['tier'] is None


def test_fixed_effects_follow_the_recipient():
    from pricing.knowledge.assessment.mechanics.fixed_socket_scalars import contribution
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    emerald = child('Perfect Emerald')
    assert contribution(facts('Spired Helm'), emerald, '2:0') == 10
    assert contribution(facts('Dimensional Shard'), emerald, '2:0') == 0
    assert contribution(facts('Monarch'), emerald, '2:0') == 0
