"""Recipe-set availability from recorded collection placements, never live inventory claims."""

import json
from contextlib import closing
from pathlib import Path

from inventory_tracking.appraisal.owned import connect_readonly
from pricing.knowledge.assessment.commodity_sets import relevant_set


# Native codes verified in misc.json; market bundle meanings in commodity_sets.SETS.
COMPONENTS = {
    '3x3 Key Set': {'pk1': ('Key of Terror', 3), 'pk2': ('Key of Hate', 3), 'pk3': ('Key of Destruction', 3)},
    'Statue Set': {
        'ua1': ("Talic's Anguish", 1),
        'ua2': ("Korlic's Pain", 1),
        'ua3': ("Madawc's Ire", 1),
        'ua4': ("Bul-Kathos' Nightmare", 1),
        'ua5': ("Worusk's End", 1),
    },
}


def recorded_set(observation, database):
    item = observation.get('item', {})
    name = relevant_set({'policy': 'quest_material', 'base_code': item.get('base_code')})
    if not name or item.get('rarity') != 'normal' or not Path(database).exists():
        return None
    spec = COMPONENTS[name]
    placeholders = ','.join('?' for _ in spec)
    with closing(connect_readonly(Path(database))) as db:
        rows = db.execute(
            'SELECT i.base_code, i.quantity, i.observation, i.last_seen, '
            'p.container, p.seen_at, p.x, p.y FROM placements p '
            'JOIN items i ON i.fingerprint=p.fingerprint WHERE p.gone_at IS NULL '
            f'AND i.rarity=? AND i.base_code IN ({placeholders})',
            ['normal', *spec],
        ).fetchall()
    if not rows:
        return None
    quantities = dict.fromkeys(spec, 0)
    unknown = set()
    dates = []
    for row in rows:
        # Quantity belongs to the latest content-hash observation, not each placement.
        # Outside the material stash these native quest objects are always individual.
        quantity = 1
        seen_at = row['seen_at']
        if row['container'] == 'materials':
            source = json.loads(row['observation']).get('source', {})
            matching_source = source.get('container', {}).get('name') == 'Materials stash' and source.get(
                'position'
            ) == [row['x'], row['y']]
            quantity = row['quantity'] if matching_source else None
            seen_at = row['last_seen'] if matching_source else seen_at
        dates.append(seen_at)
        if type(quantity) is not int or quantity < 0:
            unknown.add(row['base_code'])
        else:
            quantities[row['base_code']] += quantity
    complete = None if unknown else min(quantities[code] // required for code, (_, required) in spec.items())
    missing = (
        {}
        if complete is None
        else {
            label: required * (complete + 1) - quantities[code]
            for code, (label, required) in spec.items()
            if quantities[code] < required * (complete + 1)
        }
    )
    dates.sort()
    return {
        'name': name,
        'complete_sets': complete,
        'components': {label: None if code in unknown else quantities[code] for code, (label, _) in spec.items()},
        'missing_next': missing,
        'observed_at': dates[0],
        'observed_through': dates[-1],
    }


def set_lines(basket):
    if not basket or basket['complete_sets'] is None:
        return []
    date = basket['observed_at'][:10]
    through = basket.get('observed_through', basket['observed_at'])[:10]
    dates = date if date == through else f'{date} to {through}'
    count = basket['complete_sets']
    lines = [f'Recorded sets: {count} x {basket["name"]} ({dates})']
    missing = ', '.join(f'{quantity} {name}' for name, quantity in basket['missing_next'].items())
    if missing:
        lines.append(('For another set: ' if count else 'For a complete set: ') + missing)
    return lines
