from dataclasses import replace

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_affixed_poison import charm
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def weapon(base='Axe', rate=31, frames=50):
    poison = charm(rate=rate, frames=frames)
    return replace(
        facts(base, 'crafted'),
        stats={**poison.stats, **{f'{s}:0': {'status': 'decoded', 'value': 0} for s in (17, 18)}},
        properties={'510': 0, '462': 3},
        projection_gaps=poison.projection_gaps,
    )


def test_crafted_poison_preserves_recipe_properties_and_exact_duration():
    contract, gaps = HANDLERS['affixed'].contract(weapon(), 'weapon')
    assert contract is not None, gaps
    assert contract.rarity == 'crafted'
    assert contract.properties == {'510': 0, '462': 3, '589': 6}
    for item in (weapon(base='Long Sword'), weapon(frames=75), weapon(rate=30)):
        assert HANDLERS['affixed'].contract(item, 'weapon')[0] is None


def test_unknown_recipe_poison_contributions_remain_unpriceable(monkeypatch):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_poison

    monkeypatch.setattr(affixed_poison, 'metadata', lambda: {**metadata(), 'crafting_affix_only_poison': []})
    assert HANDLERS['affixed'].contract(weapon(), 'weapon')[0] is None
