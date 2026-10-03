"""Native Sharp grand-charm table witnesses, retaining independent suffix choices."""

from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq, role_requires
from pricing.knowledge.builds import decode_planner


KIND = 'native_sharp_grand_charm'
SUFFIX_STATS = {
    'hp': ('7:0', 'maxhp'),
    'balance3': ('99:0', 'item_fastergethitrate'),
    'move3': ('96:0', 'item_fastermovevelocity'),
    'dmg-max': ('22:0', 'maxdamage'),
}


def require_affix_identity(role, table, record_ids):
    """Native runtime IDs differ from the source table's record keys."""
    affixes = metadata()['affixes'][table]
    predicates = []
    for record_id in record_ids:
        matches = [a for a in affixes.values() if a['source']['record_key'] == str(record_id)]
        if len(matches) != 1:
            raise ValueError('Sharp charm affix identity is ambiguous')
        predicates.append({'op': 'affix_present', 'table': table, 'value': matches[0]['table_id']})
    expected = predicates[0] if len(predicates) == 1 else {'any': predicates}
    if not role_requires(role, expected):
        raise ValueError('Sharp charm overlapping totals require native affix identity')


def validate_pattern(review, role, occurrence, parser, index, read_json):
    span = parser.mentions[index]
    label = review.get('pattern_label')
    if (
        review.get('pattern_kind') != KIND
        or role.get('types') != ['lcha']
        or role.get('qualities') != ['magic']
        or role.get('names')
        or role.get('slot') != 'Charms'
        or occurrence.get('class') not in CLASS_NAMES
        or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', occurrence['class'])
        or not label
        or span['label'] != label
        or parser.entry_labels[index] != label
        or not parser.table_membership[index]
    ):
        raise ValueError('Invalid Sharp charm table context')
    planner, prefixes, suffixes = (review.get(k, {}) for k in ('planner', 'prefixes', 'suffixes'))
    if (
        planner.get('path') != f'pricing/raw/mr/planners/{span["profile_id"]}.json'
        or prefixes.get('path') != 'third-parties/d2data/json/magicprefix.json'
        or suffixes.get('path') != 'third-parties/d2data/json/magicsuffix.json'
        or type(review.get('prefix_id')) is not int
        or review['prefix_id'] != 253
    ):
        raise ValueError('Sharp charm requires exact native witnesses')
    prefix = read_json(prefixes).get('253', {})
    expected = {
        'Name': 'Sharp',
        'itype1': 'lcha',
        'spawnable': 1,
        'level': 29,
        'mod1code': 'att',
        'mod1min': 49,
        'mod1max': 76,
        'mod2code': 'dmg-max',
        'mod2min': 7,
        'mod2max': 10,
    }
    if any(prefix.get(k) != v for k, v in expected.items()) or any(prefix.get(f'mod{i}code') for i in range(3, 8)):
        raise ValueError('Sharp native definition changed')
    suffix_ids = review.get('suffix_ids')
    if (
        not isinstance(suffix_ids, list)
        or any(type(s) is not int for s in suffix_ids)
        or len(suffix_ids) != len(set(suffix_ids))
    ):
        raise ValueError('Invalid Sharp charm suffix references')
    suffix_table = read_json(suffixes)
    pool = [suffix_table.get(str(s), {}) for s in suffix_ids]
    required = {'19:0': 49, '22:0': 7}
    if pool:
        code = pool[0].get('mod1code')
        if code not in SUFFIX_STATS or any(
            r.get('itype1') != 'lcha'
            or r.get('spawnable') != 1
            or type(r.get('level')) is not int
            or not 1 <= r['level'] <= 99
            or r.get('mod1code') != code
            or r.get('Name') != pool[0].get('Name')
            or type(r.get('mod1min')) is not int
            or type(r.get('mod1max')) is not int
            or not 0 < r['mod1min'] <= r['mod1max']
            or any(r.get(f'mod{i}code') for i in range(2, 8))
            for r in pool
        ):
            raise ValueError('Invalid or unattainable Sharp charm suffix')
        key = SUFFIX_STATS[code][0]
        if key in required:
            require_affix_identity(role, 'prefix', [review['prefix_id']])
            require_affix_identity(role, 'suffix', suffix_ids)
        required[key] = required.get(key, 0) + min(r['mod1min'] for r in pool)
    if label != 'Sharp Grand Charm' + (' ' + pool[0]['Name'] if pool else ''):
        raise ValueError('Sharp charm label differs from native affixes')
    for field, value in [('identified', True), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')]:
        if not requires_eq(role.get('must', {}), 'fact_eq', field, value):
            raise ValueError('Sharp charm lost its capture guards')
    if role.get('important_stats') != list(required) or not role_requires(
        role,
        {
            'all': [
                {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}
                for key, value in required.items()
            ]
        },
    ):
        raise ValueError('Sharp charm lost its native modifier requirements')
    item = decode_planner(read_json(planner))['items'][span['item_id']]
    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Grand Charm')
    mods = item.get('mods', {})
    selected = [s for s in suffix_ids if 'ms' + str(s) in mods]
    if (
        item.get('base') != base
        or item.get('quality') != 3
        or item.get('ethereal') is not False
        or item.get('sockets') != 0
        or item.get('socketedItems')
        or set(mods) != {'mp253', *('ms' + str(s) for s in selected)}
        or len(selected) != (1 if pool else 0)
    ):
        raise ValueError('Planner is not the specified Sharp charm')
    sharp = mods['mp253']
    if len(sharp) != 2 or not all(type(v) is int for v in sharp) or not 49 <= sharp[0] <= 76 or not 7 <= sharp[1] <= 10:
        raise ValueError('Planner Sharp prefix is outside native bounds')
    expected_stats = {'tohit': sharp[0], 'maxdamage': sharp[1]}
    if selected:
        record = suffix_table[str(selected[0])]
        values = mods['ms' + str(selected[0])]
        if len(values) != 1 or type(values[0]) is not int or not record['mod1min'] <= values[0] <= record['mod1max']:
            raise ValueError('Planner Sharp suffix is outside native bounds')
        key = SUFFIX_STATS[record['mod1code']][1]
        expected_stats[key] = expected_stats.get(key, 0) + values[0]
    if item.get('stats') != expected_stats:
        raise ValueError('Planner Sharp totals disagree with native affixes')
