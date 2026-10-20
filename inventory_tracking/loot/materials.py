"""Valuable drops other than runes, by item group (config `material_marks`, `pickup_also`; the rulings are
dated there). Class IDs and names come from the item decoder's bases (items/metadata.py), by item code; the
statues' table names are placeholders, so their in-game names are given here.
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
    'charms': r'cm[1-3]',
    'essences': r'tes|ceh|bet|fed',  # Twisted, Charged, Burning, Festering
    'rings': r'rin',  # class 537
    'jewels': r'jew',  # class 658
    'amulets': r'amu',  # class 535
    'leg': r'leg',  # Wirt's Leg, class 88 (weapons.txt): the way to the cow level
}


# Worth shows only once identified: one lying identified was dropped by the player and is not taken again
# (user, 2026-10-10 night).
APPRAISED = ('charms', 'rings', 'jewels', 'amulets')
# One a character: the game takes no second while one is had (the player, 2026-10-20 13:33: "if we already have one,
# we cannot pick another one => don't waste time"; three aims at a second Wirt's Leg stopped the loop in Tristram)
CARRY_ONE = ('leg',)


def material_classes(groups) -> dict[int, str]:
    """Item class ID -> row label, for the named groups."""
    patterns = [GROUPS[group] for group in groups]
    return {
        int(class_id): STATUE_NAMES.get(base['code'], base['name'])
        for class_id, base in metadata()['bases'].items()
        if any(re.fullmatch(pattern, base['code']) for pattern in patterns)
    }


def appraised_classes() -> frozenset[int]:
    """Item class IDs of the `APPRAISED` groups."""
    return frozenset(material_classes(APPRAISED))


def carry_one_classes() -> frozenset[int]:
    """Item class IDs of the `CARRY_ONE` groups."""
    return frozenset(material_classes(CARRY_ONE))
