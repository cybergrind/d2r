from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies, assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_all_enabled_set_identities_have_explicit_reviewed_policies():
    policies = _policies(RULES.read_bytes())
    missing = [
        name
        for (quality, name), definition in named_definitions().items()
        if quality == 'set'
        and name
        not in {"Warlord's Authority", "Warlord's Conquest", "Warlord's Crushers", "Warlord's Lust", "Warlord's Mantle"}
        and (quality, name) not in policies
    ]
    assert missing == []


@pytest.mark.parametrize(
    ('base', 'name', 'tier'),
    [
        ('Basinet', "Sazabi's Mental Sheath", 'low'),
        ('Cryptic Sword', "Sazabi's Cobalt Redeemer", 'low'),
        ('Bramble Mitts', 'Laying of Hands', 'low'),
        ('Sash', "Death's Guard", 'low'),
        ('Ring', 'Angelic Halo', 'low'),
        ('Breast Plate', "Isenhart's Case", 'trash'),
    ],
)
def test_set_tiers_keep_specialist_combinations_without_calling_them_expensive(base, name, tier):
    item = facts(base, 'set', name)
    assert assess_tier(item)['tier'] == tier
    assert assess_tier(replace(item, ethereal=True))['tier'] is None
    assert assess_tier(replace(item, identified=False))['tier'] is None


def test_griswold_weapon_socket_count_controls_specialist_tier():
    item = facts('Caduceus', 'set', "Griswold's Redemption")
    assert assess_tier(replace(item, sockets=3))['tier'] == 'low'
    assert assess_tier(replace(item, sockets=4))['tier'] == 'med'
    assert assess_tier(replace(item, sockets=None))['tier'] is None
    assert assess_tier(replace(item, sockets=4, socket_contents='unknown'))['tier'] is None
