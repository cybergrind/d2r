"""Resolve magic/rare affix ranges from captured affix IDs, never from rolled values."""

import struct
from collections import Counter

from inventory_tracking.items.identity import FLAGS_OFFSET, IDENTIFIED_FLAG, ITEM_DATA_SIZE, QUALITY_OFFSET
from inventory_tracking.items.metadata import metadata


PREFIX_OFFSET = 0x48
SUFFIX_OFFSET = 0x4E
CHARM_TYPES = frozenset(('scha', 'mcha', 'lcha'))


def resolve_affix_ranges(details, arrays, base):
    quality = details.get('quality')
    if quality not in (4, 6):
        return None
    encoded = arrays.get('item_data_hex')
    if not isinstance(encoded, str):
        return None
    try:
        raw = bytes.fromhex(encoded)
    except ValueError:
        return None
    if (
        len(raw) != ITEM_DATA_SIZE
        or struct.unpack_from('<I', raw, QUALITY_OFFSET)[0] != quality
        or not struct.unpack_from('<I', raw, FLAGS_OFFSET)[0] & IDENTIFIED_FLAG
    ):
        return None
    entries = []
    for table, offset in (('prefix', PREFIX_OFFSET), ('suffix', SUFFIX_OFFSET)):
        ids = struct.unpack_from('<3H', raw, offset)
        if quality == 4 and any(ids[1:]):
            return None
        if len([i for i in ids if i]) != len({i for i in ids if i}):
            return None
        for affix_id in ids:
            if not affix_id:
                continue
            entry = metadata()['affixes'][table].get(str(affix_id))
            if not entry or base['code'] not in entry['base_codes'] or (quality == 6 and not entry.get('rare')):
                return None
            entries.append(entry)
    auto_id = struct.unpack_from('<H', raw, 0x46)[0]
    if auto_id:
        auto = metadata()['affixes']['auto'].get(str(auto_id))
        if not auto or base['code'] not in auto['base_codes']:
            return None
        entries.append(auto)
    if not entries:
        return None
    counts = Counter(stat for entry in entries for stat in entry['roll_ranges'])

    def pool(entry, stat):
        key = entry.get('rare_range_pools' if quality == 6 else 'range_pools', {}).get(base['code'], {}).get(stat)
        return metadata()['affix_pools'].get(key, {})

    ranges = {
        stat: {
            **definition,
            'affix': entry['name'],
            'affix_id': entry['table_id'],
            'source': entry['source'],
            'tiers': pool(entry, stat).get('tiers', []),
            'quality_range': pool(entry, stat).get('range'),
        }
        for entry in entries
        for stat, definition in entry['roll_ranges'].items()
        if counts[stat] == 1 and not (base.get('type') not in CHARM_TYPES and stat in ('21', '22', '23', '24', '31'))
    }
    return {
        'roll_ranges': ranges,
        'source': [entry['source'] for entry in entries],
        'scope': 'captured affix tier',
        'review': [
            f'Range unavailable: multiple captured affixes contribute to stat {stat}.'
            for stat, count in counts.items()
            if count > 1
        ],
        'quality_scope': (
            'all spawnable tiers for this charm size'
            if base.get('type') in CHARM_TYPES
            else 'all eligible tiers for this base and rarity'
        ),
    }


def resolve_charm_ranges(details, arrays, base):
    """Compatibility entry point restricted to magic charms."""
    if details.get('quality') == 4 and base.get('type') in CHARM_TYPES:
        return resolve_affix_ranges(details, arrays, base)
    return None
