"""Verified required level for original named bases with empty sockets.

D2MOO Items.cpp ITEMS_GetRequiredLevel: maximum of named/base/skill levels,
socket fillers, then native level requirement adjustment. Unresolved upgrades,
fillers and wearer-dependent oskill requirements stay outside this proof.
"""

from inventory_tracking.items.metadata import metadata


def required_level(facts, definition):
    if (
        facts.rarity not in ('unique', 'set')
        or not facts.capture_complete
        or facts.base_code != definition.get('base_code')
        or facts.socket_contents != 'empty'
        or any(key.split(':')[0] in ('92', '94') for key in facts.stats)
    ):
        return None
    levels = [
        definition.get('game_definition', {}).get('lvl req'),
        definition.get('base_definition', {}).get('levelreq'),
    ]
    if any(type(level) is not int or not 0 <= level <= 99 for level in levels):
        return None
    level = max(levels)
    oskill_levels = []
    for key, row in facts.stats.items():
        stat, layer = key.split(':')
        if stat not in ('97', '107'):
            continue
        skill = metadata()['skills'].get(layer, {})
        skill_level = skill.get('required_level')
        if row.get('status') != 'decoded' or type(skill_level) is not int or not 0 <= skill_level <= 99:
            return None
        if stat == '107':
            level = max(level, skill_level)
        else:
            oskill_levels.append(skill_level + 6)
    if any(skill_level > level for skill_level in oskill_levels):
        return None  # Effective requirement can depend on the wearer's class.
    return level
