from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_remaining_rolls import item


@pytest.mark.parametrize('pierce', [3, 4, 5])
def test_sling_all_native_rolls_valuable_but_perfect_segment_is_distinguished(pierce):
    result = assess_tier(item('Ring', 'Sling', {'358:0': pierce}))
    assert result['tier'] == 'high'
    assert bool(result['reasons']) is (pierce == 5)


@pytest.mark.parametrize('resistance', [6, 7, 8])
def test_opalvein_requires_all_four_resistances_within_native_range(resistance):
    stats = {f'{key}:0': resistance for key in (39, 41, 43, 45)}
    candidate = item('Ring', 'Opalvein', stats)
    assert assess_tier(candidate)['tier'] == 'high'
    assert assess_tier(item('Ring', 'Opalvein', stats | {'45:0': 9}))['tier'] is None
    del stats['45:0']
    assert assess_tier(item('Ring', 'Opalvein', stats))['tier'] is None


@pytest.mark.parametrize(
    ('base', 'name', 'quality', 'key', 'low', 'high', 'tier'),
    [
        ('Burnt Text', 'Measured Wrath', 'unique', '16:0', 130, 180, 'med'),
        ('Troll Belt', "Trang-Oul's Girth", 'set', '9:0', 25, 50, 'low'),
        ('War Belt', "Thundergod's Vigor", 'unique', '16:0', 160, 200, 'low'),
        ('Ring', 'Sling', 'unique', '358:0', 3, 5, 'high'),
    ],
)
def test_reviewed_segment_accepts_endpoints_but_abstains_on_modified_or_unknown_rolls(
    base, name, quality, key, low, high, tier
):
    def candidate(value):
        return replace(item(base, name, {key: value}), rarity=quality)

    for value in (low, high):
        assert assess_tier(candidate(value))['tier'] == tier
    for value in (low - 1, high + 1):
        assert assess_tier(candidate(value))['tier'] is None
    valid = candidate(low)
    for modified in (replace(valid, stats={}), replace(valid, ethereal=True), replace(valid, socket_contents='filled')):
        assert assess_tier(modified)['tier'] is None
