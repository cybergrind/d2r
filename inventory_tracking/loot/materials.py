"""Valuable stackable drops other than runes, by item class: Worldstone Shards, flawless and perfect
gems, the Colossal Ancients' statues and the Pandemonium keys (user, 2026-10-07).

Class IDs and names come from the item decoder's bases (items/metadata.py, the game's classid
column), by item code. The statues' table names are placeholders ('Uber Ancient Summon Material
Act 1'), so their in-game names are given here (as pricing's quest_materials.NAMES).
"""

import re

from inventory_tracking.items.metadata import metadata


STATUE_NAMES = {
    'ua1': "Talic's Anguish",
    'ua2': "Korlic's Pain",
    'ua3': "Madawc's Ire",
    'ua4': "Bul-Kathos' Nightmare",
    'ua5': "Worusk's End",
}
# Group -> item codes. Gems: flawless gl* (amethyst gzv) and skl, perfect gp* and skz.
GROUPS = {
    'shards': r'xa[1-5]',
    'gems': r'gl[bgrwy]|gzv|gp[bgrvwy]|sk[lz]',
    'statues': r'ua[1-5]',
    'keys': r'pk[1-3]',
}


def material_classes(groups) -> dict[int, str]:
    """Item class ID -> row label, for the named groups."""
    patterns = [GROUPS[group] for group in groups]
    return {
        int(class_id): STATUE_NAMES.get(base['code'], base['name'])
        for class_id, base in metadata()['bases'].items()
        if any(re.fullmatch(pattern, base['code']) for pattern in patterns)
    }
