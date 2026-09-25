"""Prove recipe poison rates, duration and source count are absent."""

from pricing.knowledge.crafting_elements import affix_only_bases


POISON_STATS = frozenset({'poisonmindam', 'poisonmaxdam', 'poisonlength', 'poison_count'})


def crafting_affix_only_poison(recipes, bases, properties, matches):
    return affix_only_bases(recipes, bases, properties, matches, POISON_STATS)
