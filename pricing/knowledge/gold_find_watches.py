"""Guide-backed gold-find combinations; approximate wording is not a roll cutoff."""

import hashlib
import json

from pricing.knowledge.plain_resistance_watches import PLANNER, linked_rows


# Explicit text ranges can cross native suffix tiers; ambiguous examples remain
# exact targets until independently reviewed lower cutoffs exist.
EXAMPLES = (
    (
        'warcries-gold',
        '80',
        'Grand Charm',
        'Sounding Grand Charm of Greed',
        'High',
        '30-40% Gold Find',
        {'ms281': [40], 'mp480': [1]},
        {'item_goldbonus': 40, 'item_addskill_tab#14': 1},
        {'188:34': (1, 1), '79:0': (30, 40)},
        'Warcries + gold find: +1 Warcries, 30-40% gold find (Travincal)',
    ),
    (
        'sharp-gold',
        '309',
        'Grand Charm',
        'Sharp Grand Charm of Greed',
        'High',
        '8-10 Maximum Damage and 30-40% Gold Find',
        {'mp253': [76, 10], 'ms281': [40]},
        {'tohit': 76, 'maxdamage': 10, 'item_goldbonus': 40},
        {'22:0': (8, 10), '19:0': (49, 76), '79:0': (30, 40)},
        'Damage + attack rating + gold find: 8-10 damage, 49-76 AR, 30-40% gold find',
    ),
    (
        'lucky-gold',
        '79',
        'Grand Charm',
        'Lucky Grand Charm of Greed',
        'Medium',
        'approximates these stats',
        {'ms281': [40], 'mp277': [12]},
        {'item_goldbonus': 40, 'item_magicbonus': 12},
        {'79:0': (40, 40), '80:0': (12, 12)},
        'Magic find + gold find: 12% MF, 40% gold find (Travincal)',
    ),
    (
        'grand-gold',
        '78',
        'Grand Charm',
        'Grand Charm of Greed',
        'Low',
        'Used for farming Travincal',
        {'ms281': [40]},
        {'item_goldbonus': 40},
        {'79:0': (40, 40)},
        'Gold find: 40% (Grand Charm; Travincal guide priority: low)',
    ),
    (
        'shimmering-gold',
        '122',
        'Small Charm',
        'Shimmering Small Charm of Greed',
        'High',
        'approximates these stats',
        {'mp322': [5], 'ms284': [10]},
        {**dict.fromkeys(('fireresist', 'lightresist', 'coldresist', 'poisonresist'), 5), 'item_goldbonus': 10},
        {**{f'{s}:0': (5, 5) for s in (39, 41, 43, 45)}, '79:0': (10, 10)},
        'All resistances + gold find: 5 all res, 10% gold find (Travincal)',
    ),
    (
        'ruby-gold',
        '128',
        'Small Charm',
        'Ruby Small Charm of Greed',
        'Medium',
        'approximates these stats',
        {'ms284': [10], 'mp369': [11]},
        {'item_goldbonus': 10, 'fireresist': 11},
        {'79:0': (10, 10), '39:0': (11, 11)},
        'Fire resistance + gold find: 11% fire res, 10% gold find (Travincal)',
    ),
    (
        'small-gold',
        '123',
        'Small Charm',
        'Small Charm of Greed',
        'Low',
        'Can have value',
        {'ms284': [10]},
        {'item_goldbonus': 10},
        {'79:0': (10, 10)},
        'Gold find: 10% (Small Charm; Travincal guide priority: low)',
    ),
)


def gold_specs(read, guide_html):
    guide = linked_rows(guide_html)
    raw = read(PLANNER)
    document = json.loads(raw)
    if document.get('id') != 'qx0106eh':
        raise ValueError('Gold-find planner identity changed')
    items = json.loads(document['data'])['items']
    misc = json.loads(read('third-parties/d2data/json/misc.json'))
    bases = {r['name']: r['code'] for r in misc.values()}
    specs, sources = [], {}
    for key, ident, base, label, tier, quote, mods, stats, bounds, description in EXAMPLES:
        item = items[ident]
        matches = [i for i, links in guide.links.items() if links == {('qx0106eh', ident)}]
        if (
            len(matches) != 1
            or guide.rows[matches[0]][:2] != [label, tier]
            or quote not in guide.rows[matches[0]][2]
            or item.get('mods') != mods
            or item.get('stats') != stats
            or item.get('base') != bases[base]
            or item.get('quality') != 3
            or item.get('ethereal') is not False
            or item.get('sockets') != 0
        ):
            raise ValueError(f'Gold-find guide/planner evidence changed: {ident}')
        specs.append((key, base, label, quote, bounds, (), description, tier))
        sources[key] = {
            'path': PLANNER,
            'sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'locator': f'data/items/{ident}',
            'source_date': document['date'],
        }
    return specs, sources
