from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('base', 'name', 'stats', 'tier'),
    [
        ('Spiderweb Sash', 'Arachnid Mesh', {'16:0': 109}, 'med'),
        ('Spiderweb Sash', 'Arachnid Mesh', {'16:0': 110}, 'high'),
        ('Ring', "Bul-Kathos' Wedding Band", {'60:0': 4}, 'med'),
        ('Ring', "Bul-Kathos' Wedding Band", {'60:0': 5}, 'high'),
        ('Chain Gloves', 'Chance Guards', {'80:0': 39}, 'low'),
        ('Chain Gloves', 'Chance Guards', {'80:0': 40}, 'med'),
        ('Dimensional Shard', "Death's Fathom", {'331:0': 24}, 'med'),
        ('Dimensional Shard', "Death's Fathom", {'331:0': 25}, 'high'),
        ('Vampirebone Gloves', "Dracul's Grasp", {'60:0': 10, '0:0': 14}, 'med'),
        ('Vampirebone Gloves', "Dracul's Grasp", {'60:0': 10, '0:0': 15}, 'high'),
        ('War Boots', 'Gore Rider', {'16:0': 199}, 'med'),
        ('War Boots', 'Gore Rider', {'16:0': 200}, 'high'),
        ('Gilded Shield', 'Herald of Zakarum', {'16:0': 169}, 'low'),
        ('Gilded Shield', 'Herald of Zakarum', {'16:0': 170}, 'med'),
        ('Spired Helm', "Nightwing's Veil", {'331:0': 14, '2:0': 20}, 'low'),
        ('Spired Helm', "Nightwing's Veil", {'331:0': 15, '2:0': 10}, 'high'),
        ('Myrmidon Greaves', 'Shadow Dancer', {'2:0': 24}, 'med'),
        ('Myrmidon Greaves', 'Shadow Dancer', {'2:0': 25}, 'high'),
        ('Mithril Coil', "Verdungo's Hearty Cord", {'3:0': 37, '36:0': 15}, 'low'),
        ('Mithril Coil', "Verdungo's Hearty Cord", {'3:0': 38, '36:0': 15}, 'high'),
        ('Sharkskin Boots', 'Waterwalk', {'7:0': 64}, 'low'),
        ('Sharkskin Boots', 'Waterwalk', {'7:0': 65}, 'med'),
        ('Hydra Bow', 'Windforce', {'62:0': 7}, 'med'),
        ('Hydra Bow', 'Windforce', {'62:0': 8}, 'high'),
        ('Ring', 'Wisp Projector', {'80:0': 20, '144:0': 19}, 'med'),
        ('Ring', 'Wisp Projector', {'80:0': 20, '144:0': 20}, 'high'),
    ],
)
def test_reviewed_unique_ask_segments_follow_native_roll_boundaries(base, name, stats, tier):
    item = replace(facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in stats.items()})
    assert assess_tier(item)['tier'] == tier
    assert assess_tier(replace(item, stats={}))['status'] == 'conditional'
    assert assess_tier(replace(item, ethereal=True))['tier'] is None
    impossible = {k: {'status': 'decoded', 'value': 999} for k in stats}
    assert assess_tier(replace(item, stats=impossible))['tier'] is None


@pytest.mark.parametrize(
    ('base', 'name', 'quality', 'tier'),
    [
        ('Winged Helm', "Guillaume's Face", 'set', 'low'),
        ('Amulet', "Tal Rasha's Adjudication", 'set', 'low'),
        ('Amulet', "Highlord's Wrath", 'unique', 'med'),
        ('Ring', 'The Stone of Jordan', 'unique', 'high'),
    ],
)
def test_fixed_segment_items_have_tiers_independent_of_leveling(base, name, quality, tier):
    item = facts(base, quality, name)
    assert assess_tier(item)['tier'] == tier
    assert assess_tier(replace(item, ethereal=True))['tier'] is None


def test_socket_contributions_cannot_be_mistaken_for_natural_premium_rolls():
    item = replace(
        facts('Dimensional Shard', 'unique', "Death's Fathom"), stats={'331:0': {'status': 'decoded', 'value': 30}}
    )
    assert assess_tier(item)['tier'] == 'high'
    assert assess_tier(replace(item, sockets=1, socket_contents='filled'))['tier'] is None
