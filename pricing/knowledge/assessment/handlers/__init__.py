"""Quality/family strategies; generic numerical tolerance is deliberately absent."""

from pricing.knowledge.assessment.handlers.exact import AffixedHandler, BaseHandler, ReviewHandler
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler


HANDLERS = {
    'base': BaseHandler(),
    'affixed': AffixedHandler(),
    'named': NamedHandler(),
    'runeword': RunewordHandler(),
    'unsupported': ReviewHandler('Unsupported quality policy.'),
}
