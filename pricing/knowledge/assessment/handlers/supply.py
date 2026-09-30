"""Single scroll comparisons; native stack counts require a verified market mapping."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.policies.supplies import SCROLLS, assess_supply


class SupplyHandler:
    def contract(self, facts, family):
        utility = assess_supply(facts)
        if utility is None:
            return None, ['This supply identity is not covered by ordinary supply rules.']
        if utility['gaps']:
            return None, utility['gaps']
        if facts.base_code not in SCROLLS:
            return None, ['Stack pricing needs a verified listing quantity inside each stack.']
        return ComparableContract(
            1, 'supply', family, facts.base_name, 'normal', False, 0, 'empty', {}, base_code=facts.base_code
        ), []
