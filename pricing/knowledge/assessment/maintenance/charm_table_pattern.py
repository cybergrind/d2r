"""Exact physical/Dexterity charm table witness without name-only equivalence."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq, role_requires
from pricing.knowledge.builds import decode_planner


KIND = 'double_throw_sharp_dexterity_charm'
LABEL = 'Sharp Grand Charm of Dexterity'
ROLE = 'double-throw-sharp-dexterity-grand-charm'


def validate_pattern(review, role, occurrence, parser, index, read_json):
    span = parser.mentions[index]
    if (
        review.get('pattern_kind') != KIND
        or review.get('pattern_label') != LABEL
        or role['id'] != ROLE
        or role.get('build') != 'double-throw-barbarian-guide'
        or role.get('types') != ['lcha']
        or role.get('qualities') != ['magic']
        or role.get('names')
        or role.get('slot') != 'Charms'
        or occurrence.get('class') != 'Barbarian'
        or span['label'] != LABEL
        or parser.entry_labels[index] != LABEL
        or not parser.table_membership[index]
    ):
        raise ValueError('Invalid physical Dexterity charm table context')
    for field, value in (('identified', True), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')):
        if not requires_eq(role.get('must', {}), 'fact_eq', field, value):
            raise ValueError('Physical Dexterity charm lost its capture guards')
    required = {
        'all': [
            {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}
            for key, value in (('19:0', 49), ('22:0', 7), ('2:0', 3))
        ]
    }
    if not role_requires(role, required):
        raise ValueError('Physical Dexterity charm lost a native modifier requirement')
    planner_pin = review.get('planner', {})
    prefix_pin, suffix_pin = review.get('prefixes', {}), review.get('suffixes', {})
    if (
        planner_pin.get('path') != f'pricing/raw/mr/planners/{span["profile_id"]}.json'
        or prefix_pin.get('path') != 'third-parties/d2data/json/magicprefix.json'
        or suffix_pin.get('path') != 'third-parties/d2data/json/magicsuffix.json'
    ):
        raise ValueError('Physical Dexterity charm requires exact native witnesses')
    prefix = read_json(prefix_pin)['253']
    suffixes = read_json(suffix_pin)
    if any(
        prefix.get(k) != v
        for k, v in {
            'Name': 'Sharp',
            'itype1': 'lcha',
            'mod1code': 'att',
            'mod1min': 49,
            'mod1max': 76,
            'mod2code': 'dmg-max',
            'mod2min': 7,
            'mod2max': 10,
        }.items()
    ):
        raise ValueError('Sharp native definition changed')
    for key, low, high in (('255', 3, 4), ('258', 5, 6)):
        if any(
            suffixes[key].get(k) != v
            for k, v in {
                'Name': 'of Dexterity',
                'itype1': 'lcha',
                'mod1code': 'dex',
                'mod1min': low,
                'mod1max': high,
            }.items()
        ):
            raise ValueError('Dexterity native definition changed')
    item = decode_planner(read_json(planner_pin))['items'][span['item_id']]
    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Grand Charm')
    mods = item.get('mods', {})
    suffix = next((key for key in ('255', '258') if 'ms' + key in mods), None)
    if (
        item.get('base') != base
        or item.get('quality') != 3
        or item.get('ethereal') is not False
        or item.get('sockets') != 0
        or item.get('socketedItems')
        or suffix is None
        or set(mods) != {'mp253', 'ms' + suffix}
    ):
        raise ValueError('Planner is not an unsocketed magic Sharp Dexterity Grand Charm')
    sharp, dex = mods['mp253'], mods['ms' + suffix]
    if (
        len(sharp) != 2
        or len(dex) != 1
        or not all(type(v) is int for v in (*sharp, *dex))
        or not 49 <= sharp[0] <= 76
        or not 7 <= sharp[1] <= 10
        or not suffixes[suffix]['mod1min'] <= dex[0] <= suffixes[suffix]['mod1max']
        or item.get('stats') != {'tohit': sharp[0], 'maxdamage': sharp[1], 'dexterity': dex[0]}
    ):
        raise ValueError('Planner physical Dexterity charm modifiers disagree with native bounds')
