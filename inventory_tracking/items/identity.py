"""Resolve identified set/unique titles from revalidated ItemData bytes.

Quality, identified flag, table index and base must agree. No identity or rolled
modifier is guessed from matching tooltip stats or the base type alone.
"""

import struct

from inventory_tracking.items.metadata import metadata


ITEM_DATA_SIZE = 0x60
QUALITY_OFFSET = 0x00
FLAGS_OFFSET = 0x18
IDENTIFIED_FLAG = 0x10
IDENTITY_OFFSET = 0x34
RUNEWORD_FLAG = 0x04000000
ETHEREAL_FLAG = 0x00400000  # Local D2MOO D2Items.h IFLAG_ETHEREAL.
SOCKETED_FLAG = 0x00000800  # Local D2MOO D2Items.h IFLAG_SOCKETED.
RUNEWORD_OFFSET = 0x48
IDENTITY_TABLES = {5: 'set', 7: 'unique'}


def item_flags(details, arrays):
    """Read flags only from complete, quality-matched, revalidated ItemData."""
    encoded = arrays.get('item_data_hex')
    if not isinstance(encoded, str):
        return None
    try:
        raw = bytes.fromhex(encoded)
    except ValueError:
        return None
    if len(raw) != ITEM_DATA_SIZE or struct.unpack_from('<I', raw, QUALITY_OFFSET)[0] != details.get('quality'):
        return None
    return struct.unpack_from('<I', raw, FLAGS_OFFSET)[0]


def resolve_identity(details, arrays, base):
    quality = details.get('quality')
    encoded = arrays.get('item_data_hex')
    if not isinstance(encoded, str):
        return None
    try:
        raw = bytes.fromhex(encoded)
    except ValueError:
        return None
    if len(raw) != ITEM_DATA_SIZE or struct.unpack_from('<I', raw, QUALITY_OFFSET)[0] != quality:
        return None
    flags = struct.unpack_from('<I', raw, FLAGS_OFFSET)[0]
    if not flags & IDENTIFIED_FLAG:
        return None
    if quality == 6:
        names = []
        for part, offset in (('prefix', 0x42), ('suffix', 0x44)):
            entry = metadata()['rare_names'][part].get(str(struct.unpack_from('<H', raw, offset)[0]))
            if not entry or base['code'] not in entry['base_codes']:
                return None
            names.append(entry['name'])
        return {
            'name': ' '.join(names),
            'table': 'rare',
            'table_id': list(struct.unpack_from('<2H', raw, 0x42)),
            'offset': 0x42,
            'roll_ranges': {},
            'enhanced_damage_expected': False,
        }
    table = 'runeword' if flags & RUNEWORD_FLAG and quality in (2, 3) else IDENTITY_TABLES.get(quality)
    if table is None:
        return None
    offset = RUNEWORD_OFFSET if table == 'runeword' else IDENTITY_OFFSET
    table_id = struct.unpack_from('<H' if table == 'runeword' else '<I', raw, offset)[0]
    entry = metadata()['identities'][table].get(str(table_id))
    if not entry:
        return None
    if base['code'] not in entry['base_codes']:
        upgrade = entry.get('upgrade_variants', {}).get(base['code']) if table in ('unique', 'set') else None
        if upgrade is None:
            return None
        entry = {**entry, **upgrade}
    if table == 'runeword':
        sockets = [
            s['raw']
            for a in arrays['arrays']
            if a.get('header_offset') == 0xE8
            for s in a.get('stats', [])
            if s['id'] == 194 and s['layer'] == 0
        ]
        if sockets != [len(entry['runes'])]:
            return None
    return {**entry, 'table': table, 'table_id': table_id, 'offset': offset}


def identity_review(identity, stats):
    if identity is None:
        return [
            'Item title, unique/set/runeword identity, identification flags, '
            'socket contents and requirements are unverified.'
        ]
    notes = ['Requirements are unverified; socket contents are labeled by evidence source.']
    if identity.get('roll_ranges'):
        notes.append('Ranges describe item definitions; totals can include socket or set contributions.')
    return notes + identity_issues(identity, stats)


def identity_issues(identity, stats):
    if identity and identity['enhanced_damage_expected'] and not any(s['id'] in (17, 18) for s in stats):
        return ['Enhanced Damage percentage was not captured.']
    return []


def superior_quality_identity(details, arrays, base):
    """Selected quality row, using the same ItemData file index as named items."""
    flags = item_flags(details, arrays)
    if details.get('quality') != 3 or flags is None or not flags & IDENTIFIED_FLAG or flags & RUNEWORD_FLAG:
        return None
    raw = bytes.fromhex(arrays['item_data_hex'])
    index = struct.unpack_from('<I', raw, IDENTITY_OFFSET)[0]
    category = base.get('category')
    patterns = metadata().get('superior', {}).get(category, {}).get('patterns', {})
    if str(index) not in patterns:
        return None
    return {'table_id': index, 'offset': IDENTITY_OFFSET, 'category': category}
