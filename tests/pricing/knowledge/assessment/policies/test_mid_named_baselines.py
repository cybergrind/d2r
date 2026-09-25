from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_remaining_rolls import item


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'key', 'low', 'high'),
    [
        ("Tal Rasha's Guardianship", 'Lacquered Plate', 'set', '80:0', 88, 88),
        ('Bloodpact Shard', 'Mithral Point', 'unique', '80:0', 20, 35),
        ("Ondal's Wisdom", 'Elder Staff', 'unique', '127:0', 2, 4),
        ("Skullder's Ire", 'Russet Armor', 'unique', '16:0', 160, 200),
    ],
)
def test_mid_named_baseline_does_not_invent_roll_premium_or_ethereal_price(name, base, quality, key, low, high):
    def candidate(value):
        return replace(item(base, name, {key: value}), rarity=quality)

    for value in (low, high):
        result = assess_tier(candidate(value))
        assert result['tier'] == 'med'
        assert result['reasons'] == []
    for other in (
        candidate(low - 1),
        candidate(high + 1),
        replace(candidate(low), stats={}),
        replace(candidate(low), ethereal=True),
        replace(candidate(low), socket_contents='filled'),
    ):
        assert assess_tier(other)['tier'] is None
