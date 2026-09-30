"""A named guide affix includes its native lower tiers, not only the planner tier."""

import pytest
from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('slug', 'base', 'stats'),
    [
        ('grand-steel', 'Grand Charm', ((19, 0, 88),)),
        ('grand-steel-vita', 'Grand Charm', ((19, 0, 88), (7, 0, 36 * 256))),
        ('grand-steel-balance', 'Grand Charm', ((19, 0, 88), (99, 0, 12))),
        ('grand-sharp-vita', 'Grand Charm', ((19, 0, 49), (22, 0, 7), (7, 0, 36 * 256))),
        ('sharp-large-vita', 'Large Charm', ((19, 0, 21), (22, 0, 4), (7, 0, 26 * 256))),
    ],
)
def test_named_charm_family_accepts_lower_native_tiers(slug, base, stats):
    result = assess(Item(base, 'magic', raw_stats=stats).capture(), loadout={'player_class': 'Paladin'})
    assert result == IsPartialDict(
        roles=Contains(IsPartialDict(id='zeal-paladin-charm-' + slug, rule_trace=IsPartialDict(truth='true')))
    )
