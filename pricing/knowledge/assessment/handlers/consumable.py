"""Exact single-potion comparisons, without borrowing equipment or bulk prices."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.policies.consumables import assess_consumable


class ConsumableHandler:
    def contract(self, facts, family):
        utility = assess_consumable(facts)
        if utility is None:
            return None, ['This consumable definition still needs review.']
        if utility['gaps']:
            return None, utility['gaps']
        return ComparableContract(
            1, 'consumable', family, facts.base_name, facts.rarity, False, 0, 'empty', {}, base_code=facts.base_code
        ), []
