"""Base-defense rolls when the captured total still equals the unmodified base."""

import struct

from inventory_tracking.items.identity import ETHEREAL_FLAG, FLAGS_OFFSET, ITEM_DATA_SIZE


def defense_range_context(arrays, identity):
    definition = (identity or {}).get('base_defense_range')
    if not definition:
        return None
    try:
        raw = bytes.fromhex(arrays.get('item_data_hex', ''))
    except ValueError:
        return None
    if len(raw) != ITEM_DATA_SIZE or struct.unpack_from('<I', raw, FLAGS_OFFSET)[0] & ETHEREAL_FLAG:
        return None
    values = {}
    for offset in (0x30, 0xE8):
        matches = [a for a in arrays.get('arrays', []) if a.get('header_offset') == offset]
        if len(matches) != 1:
            return None
        values[offset] = [s['raw'] for s in matches[0]['stats'] if s['id'] == 31 and s['layer'] == 0]
    if len(values[0x30]) != 1 or values[0x30] != values[0xE8]:
        return None
    return {
        'roll_ranges': {'31': {**definition, 'better': 'higher'}},
        'source': definition['source'],
        'scope': 'unmodified non-ethereal base defense',
    }
