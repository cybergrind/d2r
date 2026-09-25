"""Price rechargeable affixes only when level uniquely determines capacity.

Native PropertyFunc19 maps the affix parameters and item level to skill level
and maximum charges. Remaining uses do not change a rechargeable item variant.
ItemsMagic.cpp:303-323 excludes magic-only affixes from both rare and crafted
items; crafting does not make a different charged-skill capacity formula.
"""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.mechanics.affix_pool import can_generate
from pricing.knowledge.assessment.mechanics.named_charges import MARKET_FIELDS, fixed_charge_properties


def skill_level(parameter, item_level, required, maximum):
    if parameter > 0:
        return parameter
    if parameter == 0:
        return min(maximum if maximum > 0 else 20, max(1, int((item_level - required) / 4) + 1))
    divisor = max(1, max(1, 99 - required) // -parameter)
    return max(1, int((item_level - required) / divisor))


@lru_cache(maxsize=512)
def possible_capacities(base_code, rarity, skill, level, generation):
    data = metadata()
    skill_row = data['skills'].get(str(skill), {})
    required, maximum = skill_row.get('required_level'), skill_row.get('maximum_level')
    if type(required) is not int or type(maximum) is not int:
        return frozenset()
    capacities = set()
    for table in data['affixes'].values():
        for entry in table.values():
            if not can_generate(entry, base_code, rarity):
                continue
            record = entry['game_definition']
            for slot in (1, 2, 3):
                if record.get(f'mod{slot}code') != 'charged' or record.get(f'mod{slot}param') != skill:
                    continue
                parameter, capacity = record.get(f'mod{slot}max'), record.get(f'mod{slot}min')
                if type(parameter) is not int or type(capacity) is not int:
                    continue
                if not any(skill_level(parameter, ilvl, required, maximum) == level for ilvl in range(1, 100)):
                    continue
                if capacity < 0:
                    capacity = level * -capacity // 8 - capacity
                capacities.add(min(255, max(1, capacity)) if capacity else 5)
    return frozenset(capacities)


def affixed_charge_properties(facts):
    properties, consumed, gaps = {}, set(), []
    for key, row in facts.stats.items():
        if not key.startswith('204:'):
            continue
        parameter = row.get('parameter')
        if facts.rarity not in ('magic', 'rare', 'crafted') or type(parameter) is not int or parameter < 0:
            gaps.append(f'Charged skill {key} has no supported affix identity.')
            continue
        skill, level = divmod(parameter, 64)
        capacities = possible_capacities(facts.base_code, facts.rarity, skill, level, metadata_generation())
        if len(capacities) != 1 or skill not in MARKET_FIELDS or key != f'204:{parameter}':
            gaps.append(f'Charged skill {key} needs an unambiguous eligible affix and capacity.')
            continue
        definition = {
            'game_definition': {'prop1': 'charged', 'par1': skill, 'max1': level, 'min1': next(iter(capacities))}
        }
        fields, keys, errors = fixed_charge_properties(facts, definition)
        gaps.extend(error.replace('Named charged', 'Charged') for error in errors)
        for prop, value in fields.items():
            if prop in properties and properties[prop] != value:
                gaps.append(f'Charged skills conflict on market property {prop}.')
            properties[prop] = value
        consumed |= keys
    return properties, consumed, gaps
