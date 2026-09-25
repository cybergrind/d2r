"""Prove which crafted bases have no recipe contribution to item cold damage."""

from pricing.knowledge.crafting_elements import affix_only_bases


COLD_STATS = frozenset({'coldmindam', 'coldmaxdam', 'coldlength'})


def crafting_affix_only_cold(recipes, bases, properties, matches):
    return affix_only_bases(recipes, bases, properties, matches, COLD_STATS)
