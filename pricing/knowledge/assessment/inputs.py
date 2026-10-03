"""File-backed inputs currently participating in appraisal snapshot consistency."""

from pricing.knowledge.assessment import base_use
from pricing.knowledge.assessment.adapters import market_projection
from pricing.knowledge.assessment.build_profiles import OUTPUT
from pricing.knowledge.assessment.mechanics import base_tiers
from pricing.knowledge.assessment.policies import (
    complete_sets,
    consumables,
    crown_trade,
    generic_leveling,
    leveling,
    magic_trade,
    named_baselines,
    named_leveling,
    named_tiers,
    quest_materials,
    shako_trade,
    stormshield_trade,
)
from pricing.knowledge.documented_cache_dates import runtime_paths


def artifact_inputs(collection_reviews=None):
    return {
        **crown_trade.inputs(),
        **magic_trade.inputs(),
        **shako_trade.inputs(),
        **stormshield_trade.inputs(),
        **runtime_paths(named_tiers.ROOT, collection_reviews),
        consumables.SOURCE.resolve(): 'reviewed native potion, supply and loose socket-material definitions',
        quest_materials.RECIPES.resolve(): 'reviewed material recipe uses',
        OUTPUT.resolve(): 'reviewed profiles and guide demand',
        market_projection.CATALOG.resolve(): 'native market projections',
        named_tiers.RULES.resolve(): 'named tier rules',
        named_baselines.RULES.resolve(): 'named identity baselines',
        named_leveling.RULES.resolve(): 'named leveling reviews',
        complete_sets.RULES.resolve(): 'complete-set tier reviews',
        complete_sets.NATIVE.resolve(): 'native complete-set membership and bonuses',
        (named_tiers.ROOT / 'pricing/data/appraisal-value-watch.json').resolve(): 'named baseline demand evidence',
        (named_tiers.RULES.parent / 'named_tier_reviews.json').resolve(): 'complete named qualitative tier reviews',
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
