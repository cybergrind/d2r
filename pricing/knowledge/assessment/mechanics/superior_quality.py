"""Validate selected superior bonuses; absence alone never proves zero enhancement.

Pinned ItemsMagic.cpp 968-998 selects exactly one qualityitems row and writes
its index to ItemData. Armor and weapons retain separate selected patterns.
"""

from inventory_tracking.items.identity import IDENTITY_OFFSET
from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.mechanics.superior_damage import flat_damage_fallback


STATS = {'att': (19,), 'dur%': (75,), 'dmg%': (17, 18), 'ac%': (16,)}


def selected_pattern(facts, category):
    if facts.rarity != 'superior' or facts.runeword or not facts.capture_complete or facts.identified is not True:
        return None
    identity = facts.provenance.get('capture', {}).get('superior_quality', {})
    index = identity.get('table_id')
    if type(index) is not int or identity.get('offset') != IDENTITY_OFFSET or identity.get('category') != category:
        return None
    pattern = metadata().get('superior', {}).get(category, {}).get('patterns', {}).get(str(index))
    gate = {'weapons': 'weapon', 'armor': 'armor'}.get(category)
    return pattern if pattern and gate and pattern.get(gate) else None


def pattern_roll_gaps(facts, pattern):
    gaps = []
    for slot in (1, 2):
        code = pattern.get(f'mod{slot}code')
        if not code:
            continue
        if code not in STATS or pattern.get(f'mod{slot}param', 0) != 0:
            gaps.append('Superior quality modifier is unsupported.')
            continue
        low, high = pattern.get(f'mod{slot}min'), pattern.get(f'mod{slot}max')
        if code == 'dmg%' and flat_damage_fallback(facts, pattern):
            continue
        for stat in STATS[code]:
            row = facts.stats.get(f'{stat}:0', {})
            value = row.get('value')
            if (
                row.get('status') != 'decoded'
                or type(value) is not int
                or type(row.get('raw')) is not int
                or row['raw'] != value
                or type(low) is not int
                or type(high) is not int
                or not low <= value <= high
            ):
                gaps.append(f'Superior quality modifier {stat}:0 is missing, changed or out of range.')
        if code == 'dmg%' and facts.stats.get('17:0', {}).get('value') != facts.stats.get('18:0', {}).get('value'):
            gaps.append('Superior enhanced damage fields must represent the same roll.')
    return gaps


def superior_roll_gaps(facts, category):
    if facts.rarity != 'superior' or facts.runeword or not facts.provenance.get('capture', {}).get('superior_quality'):
        return []
    pattern = selected_pattern(facts, category)
    if pattern is None:
        return ['Superior quality identity is unknown or incompatible with the base.']
    return pattern_roll_gaps(facts, pattern)


def superior_flat_damage(facts):
    pattern = selected_pattern(facts, 'weapons')
    return pattern is not None and flat_damage_fallback(facts, pattern) and not pattern_roll_gaps(facts, pattern)


def superior_without_ed(facts, category='weapons'):
    pattern = selected_pattern(facts, category)
    if pattern is None or facts.socket_contents != 'empty':
        return False
    enhancement = 'dmg%' if category == 'weapons' else 'ac%'
    market_field = '510' if category == 'weapons' else '425'
    if any(pattern.get(f'mod{slot}code') == enhancement for slot in (1, 2)):
        return False
    if {f'{stat}:0' for stat in STATS[enhancement]} & facts.stats.keys() or market_field in facts.properties:
        return False
    return bool(pattern.get('mod1code')) and not pattern_roll_gaps(facts, pattern)
