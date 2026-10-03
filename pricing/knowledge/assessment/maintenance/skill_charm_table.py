"""Bind skill-charm guide entries to native prefix/suffix and planner witnesses."""

from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.stat_constants import CLASS_ABBREVIATIONS, CLASS_NAMES
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq, role_requires
from pricing.knowledge.builds import decode_planner


KIND = 'native_skill_grand_charm'
SUFFIX_STATS = {
    'hp': ('7:0', 'maxhp'),
    'balance3': ('99:0', 'item_fastergethitrate'),
    'move3': ('96:0', 'item_fastermovevelocity'),
}


def validate_pattern(review, role, occurrence, parser, index, read_json):
    span = parser.mentions[index]
    label = review.get('pattern_label')
    if (
        review.get('pattern_kind') != KIND
        or role.get('types') != ['lcha']
        or role.get('qualities') != ['magic']
        or role.get('names')
        or role.get('slot') != 'Charms'
        or not label
        or span['label'] != label
        or parser.entry_labels[index] != label
        or not parser.table_membership[index]
    ):
        raise ValueError('Invalid skill charm table context')
    planner, prefixes, suffixes = (review.get(k, {}) for k in ('planner', 'prefixes', 'suffixes'))
    if (
        planner.get('path') != f'pricing/raw/mr/planners/{span["profile_id"]}.json'
        or prefixes.get('path') != 'third-parties/d2data/json/magicprefix.json'
        or suffixes.get('path') != 'third-parties/d2data/json/magicsuffix.json'
    ):
        raise ValueError('Skill charm requires exact native witnesses')
    prefix_id, suffix_ids = review.get('prefix_id'), review.get('suffix_ids')
    if type(prefix_id) is not int or not isinstance(suffix_ids, list) or any(type(s) is not int for s in suffix_ids):
        raise ValueError('Invalid skill charm affix references')
    if len(suffix_ids) != len(set(suffix_ids)):
        raise ValueError('Duplicate skill charm suffix')
    prefix = read_json(prefixes).get(str(prefix_id), {})
    tab = prefix.get('mod1param')
    if (
        prefix.get('itype1') != 'lcha'
        or prefix.get('mod1code') != 'skilltab'
        or prefix.get('mod1min') != 1
        or prefix.get('mod1max') != 1
        or prefix.get('spawnable') != 1
        or type(prefix.get('level')) is not int
        or not 1 <= prefix['level'] <= 99
        or type(tab) is not int
        or not 0 <= tab < 3 * len(CLASS_NAMES)
        or CLASS_ABBREVIATIONS.get(prefix.get('classspecific')) != CLASS_NAMES[tab // 3]
        or occurrence.get('class') != CLASS_NAMES[tab // 3]
    ):
        raise ValueError('Invalid native skill charm prefix')
    layer = (tab // 3) * 8 + tab % 3
    required = {f'188:{layer}': 1}
    suffix_table = read_json(suffixes)
    pool = [suffix_table.get(str(s), {}) for s in suffix_ids]
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
            for r in pool
        ):
            raise ValueError('Invalid or unattainable skill charm suffix')
        required[SUFFIX_STATS[code][0]] = min(r['mod1min'] for r in pool)
    for field, value in (('identified', True), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')):
        if not requires_eq(role.get('must', {}), 'fact_eq', field, value):
            raise ValueError('Skill charm lost capture guards')
    if role.get('important_stats') != list(required) or not role_requires(
        role,
        {
            'all': [
                {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}
                for key, value in required.items()
            ]
        },
    ):
        raise ValueError('Skill charm lost its exact native modifier requirements')
    item = decode_planner(read_json(planner))['items'][span['item_id']]
    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Grand Charm')
    mods = item.get('mods', {})
    selected = [s for s in suffix_ids if 'ms' + str(s) in mods]
    expected_mods = {'mp' + str(prefix_id)} | {'ms' + str(s) for s in selected}
    if (
        item.get('base') != base
        or item.get('quality') != 3
        or item.get('ethereal') is not False
        or item.get('sockets') != 0
        or item.get('socketedItems')
        or set(mods) != expected_mods
        or mods.get('mp' + str(prefix_id)) != [1]
        or len(selected) != (1 if pool else 0)
    ):
        raise ValueError('Planner is not the specified skill charm')
    expected_stats = {f'item_addskill_tab#{tab}': 1}
    if selected:
        record = suffix_table[str(selected[0])]
        values = mods['ms' + str(selected[0])]
        if len(values) != 1 or type(values[0]) is not int or not record['mod1min'] <= values[0] <= record['mod1max']:
            raise ValueError('Planner skill charm suffix is outside native bounds')
        expected_stats[SUFFIX_STATS[record['mod1code']][1]] = values[0]
    if item.get('stats') != expected_stats:
        raise ValueError('Planner skill charm totals disagree with its affixes')
