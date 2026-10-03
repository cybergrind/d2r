"""Reject impossible named armor totals without reconstructing missing rolls."""

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
from pricing.knowledge.market_base_catalog import equipment_index


# Reviewed standalone and partial-set effects do not lower item defense.
# This is a lower bound only: it does not infer original bases, intrinsic rolls,
# socket contents, or an upper bound for equipped set totals.
NONDEFENSE_PROPERTIES = {
    "Aldur's Advance": frozenset({'indestruct', 'regen-stam', 'hp', 'dmg-to-mana', 'move3', 'stam', 'res-fire', 'dex'}),
}


def defense_conflict(row, variants):
    allowed = NONDEFENSE_PROPERTIES.get(row.get('name'))
    total = row.get('properties', {}).get('1855')
    code = row.get('base_code')
    if allowed is None or total is None or code is None:
        return None
    if type(total) is not int:
        return 'Named total defense must be an integer.'
    if not variants or any(
        variant.get('rarity') != 'set'
        or not variant.get('game_definition')
        or any(
            value not in allowed
            for key, value in variant['game_definition'].items()
            if key.startswith(('prop', 'aprop'))
        )
        for variant in variants
    ):
        return 'Named defense effects changed; native lower-bound review is required.'
    try:
        index, _ = equipment_index(read_artifact(CATALOG))
        bases = [base for base in index.values() if base.get('base_code') == code]
    except OSError, ValueError, KeyError, TypeError:
        return 'Named defense base data is unavailable.'
    if len(bases) != 1:
        return 'Named defense base is ambiguous or unavailable.'
    bounds = bases[0].get('details', {}).get('base_defense', ())
    if len(bounds) != 2 or any(type(value) is not int for value in bounds):
        return 'Named defense base range is unavailable.'
    if total < bounds[0]:
        return f'Total defense {total} is below the supplied base minimum {bounds[0]}.'
    return None
