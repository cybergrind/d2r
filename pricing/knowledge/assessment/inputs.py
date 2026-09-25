"""File-backed inputs currently participating in appraisal snapshot consistency."""

from pricing.knowledge.assessment import base_use
from pricing.knowledge.assessment.adapters import market_projection
from pricing.knowledge.assessment.mechanics import base_tiers
from pricing.knowledge.assessment.policies import generic_leveling, leveling, named_tiers


def artifact_inputs():
    return {
        market_projection.CATALOG.resolve(): 'native market projections',
        named_tiers.RULES.resolve(): 'named tier rules',
        (named_tiers.ROOT / 'pricing/data/wp-i-uniques-misc.json').resolve(): 'named tier research',
        (named_tiers.ROOT / 'pricing/data/wp-h-jewels-charms.json').resolve(): 'unique charm tier research',
        (
            named_tiers.ROOT / 'pricing/data/appraisal-named-tier-research.json'
        ).resolve(): 'additional named tier research',
        generic_leveling.SOURCE.resolve(): 'generic leveling research',
        base_use.UTILITY.resolve(): 'runeword utility',
        base_tiers.CATALOG.resolve(): 'base catalog',
        (leveling.DATA / 'appraisal-recommendations.json').resolve(): 'leveling recommendations',
        (leveling.DATA / 'appraisal-item-facts.json').resolve(): 'leveling item facts',
    }
