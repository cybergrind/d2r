from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'tier'),
    [
        ("Aldur's Advance", 'low'),
        ("Bane's Authority", 'trash'),
        ("Bane's Oathmaker", 'trash'),
        ("Bane's Wraithskin", 'low'),
        ("Horazon's Countenance", 'trash'),
        ("Horazon's Dominion", 'low'),
        ("Horazon's Hold", 'trash'),
        ("Horazon's Legacy", 'low'),
        ("Horazon's Secrets", 'low'),
        ("Immortal King's Detail", 'trash'),
        ("Immortal King's Forge", 'trash'),
        ("Immortal King's Pillar", 'trash'),
        ("Immortal King's Soul Cage", 'trash'),
        ("Immortal King's Will", 'low'),
        ("Tal Rasha's Fine-Spun Cloth", 'low'),
        ("Tal Rasha's Horadric Crest", 'low'),
        ("Tal Rasha's Lidless Eye", 'low'),
        ("Trang-Oul's Claws", 'low'),
    ],
)
def test_reviewed_set_baselines_reject_ethereal_and_socketed_variants(name, tier):
    definition = named_definitions()['set', name]
    base = next(b for b in metadata()['bases'].values() if b['code'] == definition['base_codes'][0])
    item = facts(base['name'], 'set', name)
    assert assess_tier(item)['tier'] == tier
    assert assess_tier(replace(item, ethereal=True))['tier'] is None
    assert assess_tier(replace(item, socket_contents='filled'))['tier'] is None


def test_low_trade_tier_preserves_trang_gloves_leveling_recommendation():
    item = facts('Heavy Bracers', 'set', "Trang-Oul's Claws")
    assert assess_tier(item)['tier'] == 'low'
    assert assess_leveling(item)


def test_naj_teleport_swap_has_low_trade_tier_without_claiming_numeric_price():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    item = facts('Elder Staff', 'set', "Naj's Puzzler")
    result = assess_tier(item)
    assert result['tier'] == 'low'
    assert 'teleport' in result['basis'].lower()
    assert 'two' in result['basis'].lower()
    assert assess_tier(replace(item, ethereal=True))['tier'] is None
