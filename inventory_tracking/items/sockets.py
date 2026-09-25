"""Socket names from verified child linkage, or explicitly labeled recipes."""

from typing import Any

from inventory_tracking.items.identity import SOCKETED_FLAG, resolve_identity
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.items.socket_payload import decode_payload


def annotate_sockets(item, decoded, arrays, identity):
    rows = [r for r in decoded if r.get('memory_stat', {}).get('id') == 194 and r['status'] == 'decoded']
    if len(rows) != 1 or not 0 <= rows[0]['value'] <= 6:
        return
    row = rows[0]
    count = row['value']
    item['sockets'] = count
    capture = arrays.get('socket_items', {})
    children = capture.get('children')
    complete = capture.get('complete') is True
    contents: list[dict[str, Any]] = []
    if children and len(children) <= count and [c['position'] for c in children] == list(range(len(children))):
        for child in children:
            unit = child['unit']
            base = item_base(unit['txt_id'])
            if not base:
                contents = []
                break
            named = resolve_identity(unit['details'], {'item_data_hex': child['item_data_hex']}, base)
            contents.append(
                {
                    'name': named['name'] if named else base['name'],
                    'base_code': base['code'],
                    'unit_id': unit['unit_id'],
                    'position': child['position'],
                    **decode_payload(child, base),
                }
            )
    if contents:
        item['socket_items'] = contents
        item['socket_contents'] = 'filled'
        row['text'] = (
            row.get('text', f'Sockets: {count}') + ' — ' + ', '.join(c['name'].removesuffix(' Rune') for c in contents)
        )
        if complete:
            item['empty_sockets'] = count - len(contents)
            item['filled_sockets'] = len(contents)
            if item['empty_sockets']:
                row['text'] += f'; {item["empty_sockets"]} empty'
        elif len(contents) < count:
            row['text'] += f' ({len(contents)} contents captured)'
        row['socket_source'] = 'captured_children'
    elif identity and identity['table'] == 'runeword':
        by_code = {b['code']: b['name'] for b in metadata()['bases'].values()}
        recipe = [by_code.get(code, code) for code in identity['runes']]
        item['socket_recipe'] = recipe
        item['socket_contents'] = 'filled'
        row['text'] = (
            row.get('text', f'Sockets: {count}')
            + ' — '
            + ', '.join(name.removesuffix(' Rune') for name in recipe)
            + ' (runeword recipe)'
        )
        row['socket_source'] = 'runeword_definition'
    elif complete and children == []:
        item['socket_contents'] = 'empty'
        item['socket_items'] = []
        item['empty_sockets'] = count
        item['filled_sockets'] = 0
        row['text'] = row.get('text', f'Sockets: {count}') + f' — {count} empty'
        row['socket_source'] = 'complete_child_scan'
    elif count:
        row['text'] = f'Sockets: {count} — contents not captured'


# Pinned third-parties/d2data/json/itemtypes.json: all three MaxSockets bands
# are explicitly zero. Never generalize this rule to socketable equipment.
NONSOCKETABLE_TYPES = frozenset(
    {
        'amul',
        'ring',
        'scha',
        'mcha',
        'lcha',
        'jewl',
        'cjwl',
        'csch',
        'glov',
        'boot',
        'belt',
        'jave',
        'ajav',
        'tkni',
        'taxe',
    }
)


def infer_nonsocketable(item, stats, arrays, flags):
    if (
        item.get('item_type') not in NONSOCKETABLE_TYPES
        or flags is None
        or flags & SOCKETED_FLAG
        or any(row.get('id') == 194 for row in stats)
        or arrays.get('socket_items', {}).get('children')
        or item.get('sockets') not in (None, 0)
        or item.get('socket_contents') not in (None, 'empty')
    ):
        return False
    item.update(sockets=0, socket_contents='empty', socket_items=[], empty_sockets=0, filled_sockets=0)
    return True
