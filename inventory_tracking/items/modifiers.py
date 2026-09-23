"""Recover local weapon ED omitted from totals, using owned modifier evidence."""

import struct


def owned_modifiers(diagnostics, item, ids):
    if not diagnostics.get('stable') or diagnostics.get('root_address') != item['stats_pointer']:
        return []
    try:
        root = bytes.fromhex(diagnostics['header_hex'])
        if struct.unpack_from('<II', root, 8) != (4, item['unit_id']):
            return []
        chains = [c for c in diagnostics['chains'] if c['head_offset'] == 0xD0]
        if len(chains) != 1 or not chains[0]['complete']:
            return []
        current = struct.unpack_from('<Q', root, 0xD0)[0]
        stats = []
        for node in chains[0]['lists']:
            if node['address'] != current:
                return []
            header = bytes.fromhex(node['header_hex'])
            if struct.unpack_from('<QII', header, 0) != (item['address'], 4, item['unit_id']):
                return []
            stats.extend(s for s in node['stats'] if s['id'] in ids)
            current = struct.unpack_from('<Q', header, 0x48)[0]
        if current or sorted(s['id'] for s in stats) != sorted(ids):
            return []
        if any(s['layer'] != 0 or s['raw'] < 0 for s in stats):
            return []
        return stats
    except KeyError, ValueError, struct.error:
        return []


def owned_damage_modifiers(diagnostics, item):
    stats = owned_modifiers(diagnostics, item, (17, 18))
    return stats if stats and stats[0]['raw'] == stats[1]['raw'] else []


def owned_defense_modifiers(diagnostics, item):
    return owned_modifiers(diagnostics, item, (16,))
