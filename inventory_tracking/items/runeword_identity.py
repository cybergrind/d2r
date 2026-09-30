"""Verified prefix identities, with ordered captured recipes for unmapped words."""

TOTAL_STATS_OFFSET = 0xE8
SOCKETS_STAT_ID = 194
ITEM_UNIT_TYPE = 4


def socket_count(arrays):
    counts = [
        stat.get('raw')
        for array in arrays.get('arrays', [])
        if array.get('header_offset') == TOTAL_STATS_OFFSET
        for stat in array.get('stats', [])
        if stat.get('id') == SOCKETS_STAT_ID and stat.get('layer') == 0
    ]
    if len(counts) == 1 and type(counts[0]) is int and counts[0] > 0:
        return counts[0]
    return None


def captured_runes(capture, count, bases):
    children = capture.get('children')
    if capture.get('complete') is not True or not isinstance(children, list) or len(children) != count:
        return None
    codes, unit_ids = [], set()
    for position, child in enumerate(children):
        if not isinstance(child, dict) or child.get('position') != position:
            return None
        unit = child.get('unit')
        if not isinstance(unit, dict) or unit.get('type') != ITEM_UNIT_TYPE or unit.get('identity_stable') is not True:
            return None
        base = bases.get(str(unit.get('txt_id')))
        unit_id = unit.get('unit_id')
        if not base or base.get('type') != 'rune' or type(unit_id) is not int or unit_id in unit_ids:
            return None
        codes.append(base['code'])
        unit_ids.add(unit_id)
    return codes


def resolve_runeword(table_id, arrays, base, catalog):
    """Caller has already verified ItemData, identification, quality and runeword flag."""
    count = socket_count(arrays)
    if count is None:
        return None
    capacity = base.get('max_sockets')
    if type(capacity) is int and count > capacity:
        return None
    capture = arrays.get('socket_items', {})
    runes = captured_runes(capture, count, catalog['bases'])
    known = catalog['identities']['runeword']
    entry = known.get(str(table_id))
    if entry:
        if base['code'] not in entry['base_codes'] or count != len(entry['runes']):
            return None
        if capture.get('complete') is True and runes != entry['runes']:
            return None
        return entry
    # An unknown prefix cannot establish an identity by base or stats alone.
    if runes is None or type(capacity) is not int:
        return None
    matches = [
        entry
        for entry in [*known.values(), *catalog.get('unmapped_runewords', [])]
        if base['code'] in entry['base_codes'] and runes == entry['runes']
    ]
    if len(matches) != 1:
        return None
    return {**matches[0], 'method': 'captured_recipe', 'observed_table_id': table_id}
