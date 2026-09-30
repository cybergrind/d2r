"""Validate captured native IDs independently of item names and rolled totals."""

from inventory_tracking.items.metadata import metadata


TABLES = frozenset(('prefix', 'suffix', 'auto'))


def captured_affixes(value, item):
    rarity = item.get('rarity')
    if rarity not in ('magic', 'rare') or item.get('identified') is not True:
        return None
    if not isinstance(value, dict) or set(value) != TABLES:
        return None
    result = {}
    for table, ids in value.items():
        limit = 1 if rarity == 'magic' or table == 'auto' else 3
        if not isinstance(ids, list) or len(ids) > limit or any(type(i) is not int or i <= 0 for i in ids):
            return None
        if len(set(ids)) != len(ids):
            return None
        for ident in ids:
            entry = metadata()['affixes'][table].get(str(ident))
            if not entry or item.get('base_code') not in entry['base_codes']:
                return None
            if rarity == 'rare' and table != 'auto' and not entry.get('rare'):
                return None
        result[table] = ids
    return result if any(result.values()) else None
