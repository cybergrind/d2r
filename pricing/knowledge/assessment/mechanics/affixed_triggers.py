"""Project affix proc chances only when the market field also fixes spell level.

Native PropertyFunc11 stores chance and packs skill/level in the stat layer.
A scalar chance field cannot distinguish equal-chance affixes at different levels.
"""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.knowledge.assessment.mechanics.affix_pool import can_generate
from pricing.knowledge.assessment.mechanics.triggers import MARKET_FIELDS
from pricing.knowledge.named_triggers import EVENTS


TRIGGER_STATS = frozenset({'195', '196', '197', '198', '199', '201'})


@lru_cache(maxsize=512)
def eligible_levels(base_code, rarity, stat, skill, chance, generation):
    data = metadata()
    event = next((code for code, name in EVENTS.items() if data['stats'].get(str(stat), {}).get('name') == name), None)
    if event is None:
        return frozenset()
    levels, groups = set(), set()
    for table_name, table in data['affixes'].items():
        for entry in table.values():
            if not can_generate(entry, base_code, rarity):
                continue
            record = entry['game_definition']
            for slot in (1, 2, 3):
                if record.get(f'mod{slot}code') != event or record.get(f'mod{slot}param') != skill:
                    continue
                group = record.get('group')
                probability, level = record.get(f'mod{slot}min'), record.get(f'mod{slot}max')
                if (
                    type(group) is not int
                    or group <= 0
                    or type(probability) is not int
                    or not 1 <= probability <= 100
                    or type(level) is not int
                    or not 1 <= level < 64
                ):
                    return frozenset()
                groups.add((table_name, group))
                if probability == chance:
                    levels.add(level)
    if len(groups) > 1:
        return frozenset()
    if rarity == 'crafted':
        recipes = data.get('crafting_triggers', {})
        if base_code not in recipes:
            return frozenset()
        recipe_effects = [e for e in recipes[base_code] if e['stat_id'] == stat and e['skill_id'] == skill]
        # A recipe and affix can coexist. Until contribution combinations can be
        # represented, do not collapse them into the same scalar market field.
        if recipe_effects and groups:
            return frozenset()
        levels.update(e['level'] for e in recipe_effects if e['chance'] == chance)
    return frozenset(levels)


def affixed_trigger_properties(facts):
    properties, consumed, gaps = {}, set(), []
    for key, row in facts.stats.items():
        if key.partition(':')[0] not in TRIGGER_STATS:
            continue
        stat = int(key.partition(':')[0])
        parameter, chance = row.get('parameter'), row.get('value')
        if (
            facts.rarity not in ('magic', 'rare', 'crafted')
            or facts.socket_contents != 'empty'
            or type(parameter) is not int
            or parameter < 0
            or row.get('status') != 'decoded'
            or row.get('unit') != 'percent_chance'
            or type(chance) is not int
            or not 1 <= chance <= 100
            or type(row.get('raw')) is not int
            or row['raw'] != chance
            or key != f'{stat}:{parameter}'
        ):
            gaps.append(f'Affix trigger {key} has no verified empty-item proc identity.')
            continue
        skill, level = divmod(parameter, 64)
        levels = eligible_levels(facts.base_code, facts.rarity, stat, skill, chance, metadata_generation())
        prop = MARKET_FIELDS.get((stat, skill))
        if levels != {level} or not prop or row.get('market_property') not in (None, prop):
            gaps.append(f'Affix trigger {key} needs an unambiguous eligible affix level and market field.')
            continue
        if prop in properties:
            gaps.append(f'Affix triggers collide on market property {prop}.')
            continue
        properties[prop] = chance
        consumed.add(key)
    return properties, consumed, gaps
