"""Single-material comparisons never borrow a key/statue set or a quantity lot."""

from pricing.knowledge.assessment.domain.contracts import ComparableContract
from pricing.knowledge.assessment.policies.quest_materials import TRADEABLE, assess_material


class QuestMaterialHandler:
    def contract(self, facts, family):
        utility = assess_material(facts)
        if utility is None:
            return None, ['Quest identity needs a reviewed utility or trade-material disposition.']
        if utility['gaps']:
            return None, utility['gaps']
        if facts.base_code not in TRADEABLE:
            return None, ['Horadric Cube: personal recipe/storage utility; no reviewed trade comparison.']
        return ComparableContract(
            1, 'quest_material', family, utility['name'], 'normal', False, 0, 'empty', {}, base_code=facts.base_code
        ), []
