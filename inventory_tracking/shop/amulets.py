"""Reviewed +3 tree amulets with a big suffix: 80+ life, 25+ strength or dexterity, 30+ MF (4 sellers, asks Q1 22.8;
a plain +3 tree asks a median of 0.57 from 20 sellers, one with 10 FCR 7.6 from 14; 2026-09-18/19). Vendors rarely
stock amulets (AMULETS.md).

2026-09-27 review and source distinctions: AMULETS.md. Native stat188 layers,
not properties.json's sequential skilltab parameters. Only reviewed trees alert.
"""

from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_TABS, StatId


TREE_USES = {
    8: 'Meteor / Enchant',
    9: 'Lightning Sorceress',
    10: 'Blizzard / Frozen Orb',
    17: 'Poison Nova',
    18: 'Summon Necromancer',
    24: 'Hammer / Fist of the Heavens',
    34: 'Singer / Battle Orders / Find Item',
    40: 'Summon Druid',
    42: 'Fire / Wind Druid',
    48: 'Lightning Sentry / Wake of Fire / Fire Blast',
    49: 'buffing equipment',
    57: 'Echoing Strike candidate',
    58: 'Abyss',
}

SUFFIXES = ((7, 80, 'life'), (0, 25, 'strength'), (2, 25, 'dexterity'), (80, 30, 'MF'))


def match_amulet(observation, stats):
    item = observation['item']
    if item.get('item_type') != 'amul' or item.get('rarity') != 'magic' or item.get('identified') is not True:
        return []
    unknown = {(s['id'], s['layer']) for s in observation.get('unresolved_stats', [])}

    def value(stat, layer=0):
        return 0 if (stat, layer) in unknown else stats.get((stat, layer), 0)

    reasons = []
    for layer, use in TREE_USES.items():
        if value(StatId.SKILL_TAB, layer) != 3:
            continue
        extras = [f'{value(stat):g} {label}' for stat, low, label in SUFFIXES if value(stat) >= low]
        if extras:
            name = f'{CLASS_NAMES[layer // 8]} {SKILL_TABS[layer // 8][layer % 8]}'
            reasons.append(f'+3 {name} / {" / ".join(extras)} amulet — {use}')
    return reasons
