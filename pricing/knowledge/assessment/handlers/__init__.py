"""Quality/family strategies; generic numerical tolerance is deliberately absent."""

from pricing.knowledge.assessment.handlers.consumable import ConsumableHandler
from pricing.knowledge.assessment.handlers.exact import AffixedHandler, BaseHandler, ReviewHandler
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.handlers.quest_material import QuestMaterialHandler
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from pricing.knowledge.assessment.handlers.socket_material import SocketMaterialHandler
from pricing.knowledge.assessment.handlers.supply import SupplyHandler


HANDLERS = {
    'quest_material': QuestMaterialHandler(),
    'supply': SupplyHandler(),
    'socket_material': SocketMaterialHandler(),
    'consumable': ConsumableHandler(),
    'base': BaseHandler(),
    'affixed': AffixedHandler(),
    'named': NamedHandler(),
    'runeword': RunewordHandler(),
    'unsupported': ReviewHandler('Unsupported quality policy.'),
}
