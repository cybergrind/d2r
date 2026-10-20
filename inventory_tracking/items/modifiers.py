"""Recover local weapon ED omitted from totals, using owned modifier evidence."""

import struct


def owned_chain(diagnostics, item, *, fillers=False):
    """Every stat of the item's own +0xD0 modifier chain (`native/item_diagnostics.py` `capture_stat_candidates`),
    once its snapshot is stable, its root and every list name the item as owner and the links end; None otherwise.
    An item with no modifier list gives []. `fillers`: a list another item owns is passed over, not a failure: what
    fills its sockets ([verified] 2026-10-20: in 516 of 9,751 captured white, superior and magic units, 60 collection
    captures, each such list's owner is one of the item's socketed children, and none holds a stat)."""
    if not diagnostics.get('stable') or diagnostics.get('root_address') != item.get('stats_pointer'):
        return None
    try:
        root = bytes.fromhex(diagnostics['header_hex'])
        if struct.unpack_from('<II', root, 8) != (4, item['unit_id']):
            return None
        chains = [c for c in diagnostics['chains'] if c['head_offset'] == 0xD0]
        if len(chains) != 1 or not chains[0]['complete']:
            return None
        current = struct.unpack_from('<Q', root, 0xD0)[0]
        stats = []
        for node in chains[0]['lists']:
            if node['address'] != current:
                return None
            header = bytes.fromhex(node['header_hex'])
            owner = struct.unpack_from('<QII', header, 0)
            if owner == (item['address'], 4, item['unit_id']):
                stats.extend(node['stats'])
            elif not fillers or owner[1] != 4 or owner[2] == item['unit_id']:
                return None
            current = struct.unpack_from('<Q', header, 0x48)[0]
        return None if current else stats
    except KeyError, ValueError, struct.error:
        return None


def owned_modifiers(diagnostics, item, ids, forbidden=()):
    chain = owned_chain(diagnostics, item)
    if chain is None:
        return []
    try:
        stats = [s for s in chain if s['id'] in (*ids, *forbidden)]
        if sorted(s['id'] for s in stats) != sorted(ids):
            return []
        if any(s['layer'] != 0 or s['raw'] < 0 for s in stats):
            return []
        return stats
    except KeyError:
        return []


def owned_damage_modifiers(diagnostics, item):
    stats = owned_modifiers(diagnostics, item, (17, 18))
    return stats if stats and stats[0]['raw'] == stats[1]['raw'] else []


def owned_defense_modifiers(diagnostics, item):
    return owned_modifiers(diagnostics, item, (16,))


def owned_flat_damage_modifiers(diagnostics, item):
    """Only an owned +1 maximum with no percent ED proves the fallback."""
    if 'stats_pointer' not in item:
        return []
    rows = []
    for stat in (22, 24):
        found = owned_modifiers(diagnostics, item, (stat,), forbidden=(17, 18))
        if found and type(found[0]['raw']) is int and found[0]['raw'] == 1:
            rows.extend(found)
    return rows
