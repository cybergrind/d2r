"""Verify fixed rune-only throw-damage entries on nonthrowing runeword weapons.

PropertyFunc05/06 writes all damage modes to the rune's stat list. On a
nonthrowing socketed weapon, native159/160 is a redundant rune contribution,
not the weapon's actual minimum/maximum damage or an independent roll.
"""

from collections import Counter

from pricing.knowledge.market_mechanics import THROWING_TYPES


def fixed_physical_rune_keys(facts, definition, family):
    if family != 'weapon' or facts.item_type in THROWING_TYPES or not facts.capture_complete:
        return set()
    totals = Counter()
    for effect in definition.get('socket_compound_effects', {}).get('weapon', ()):
        if effect.get('kind') != 'physical_mirror':
            continue
        stat, value = effect.get('stat_id'), effect.get('value')
        if stat not in (159, 160) or type(value) is not int or value < 1:
            return set()
        totals[stat] += value
    consumed = set()
    for stat, expected in totals.items():
        key = f'{stat}:0'
        row = facts.stats.get(key, {})
        if (
            row.get('status') == 'decoded'
            and type(row.get('raw')) is int
            and row['raw'] == expected
            and type(row.get('value')) is int
            and row['value'] == expected
            and row.get('market_property') is None
        ):
            consumed.add(key)
    return consumed
