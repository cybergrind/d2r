"""Immutable recipe candidate indexes; no item-specific decisions during compilation."""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from pricing.knowledge.assessment.domain.facts import freeze


@dataclass(frozen=True)
class RecipeIndex:
    by_base: Mapping
    mercenary_alternatives: Mapping


def compile_recipe_index(rows, base_types):
    by_base = defaultdict(list)
    alternatives = defaultdict(set)
    for row in rows:
        if row.get('kind') != 'base_rule':
            continue
        name = row['name']
        by_base[name].append(row)
        details = row.get('details', {})
        word = details.get('runeword')
        if (
            word
            and details.get('recommended')
            and details.get('context', {}).get('builds_merc')
            and base_types.get(name) in ('pole', 'spea')
        ):
            alternatives[word].add(name)
    return RecipeIndex(freeze(dict(by_base)), freeze({word: sorted(names) for word, names in alternatives.items()}))
