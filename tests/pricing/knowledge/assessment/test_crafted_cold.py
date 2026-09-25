from dataclasses import replace

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_affixed_cold import cold


def test_crafted_weapon_cold_uses_rare_affixes_without_erasing_recipe_bonuses():
    item = cold(base='Axe', rarity='crafted')
    item = replace(item, properties={**item.properties, '462': 3})
    contract, gaps = HANDLERS['affixed'].contract(item, 'weapon')
    assert contract is not None, gaps
    assert contract.rarity == 'crafted'
    assert contract.properties == {'510': 0, '482': 1, '483': 3, '462': 3}
    assert HANDLERS['affixed'].contract(cold(base='Long Sword', rarity='crafted'), 'weapon')[0] is None
    assert HANDLERS['affixed'].contract(cold(base='Axe', rarity='crafted', frames=50), 'weapon')[0] is None


def test_missing_recipe_evidence_cannot_prove_crafted_cold(monkeypatch):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_cold

    monkeypatch.setattr(affixed_cold, 'metadata', lambda: {**metadata(), 'crafting_affix_only_cold': []})
    assert HANDLERS['affixed'].contract(cold(base='Axe', rarity='crafted'), 'weapon')[0] is None


def test_crafted_cold_combinations_cannot_exceed_four_random_affixes(monkeypatch):
    from pricing.knowledge.assessment.mechanics import affixed_cold

    groups = tuple((side, ((1, 1, 1, 1, 25, 25),)) for side in ['prefix'] * 3 + ['suffix'] * 2)
    monkeypatch.setattr(affixed_cold, 'cold_groups', lambda *_: groups)
    assert affixed_cold.possible_durations('test', 'rare', 5, 5, 'five-affixes') == {125}
    assert affixed_cold.possible_durations('test', 'crafted', 5, 5, 'five-affixes') == set()
