"""Reviewed +3 tree amulets: self-use evidence, not a resale-price claim.

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
        extras = []
        for stat, low, high, label in ((105, 10, 10, 'FCR'), (7, 81, 100, 'life'), (80, 26, 35, 'MF')):
            amount = value(stat)
            if low <= amount <= high:
                extras.append(f'{amount:g} {label}')
        gold = value(79)
        if layer == 34 and 41 <= gold <= 80:
            extras.append(f'{gold:g} gold find')
        quality = 'Build review' if extras else 'Build use'
        name = f'{CLASS_NAMES[layer // 8]} {SKILL_TABS[layer // 8][layer % 8]}'
        suffix = ' / ' + ' / '.join(extras) if extras else ''
        reasons.append(f'{quality}: +3 {name}{suffix} — {use}')
    return reasons
