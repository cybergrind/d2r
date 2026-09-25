"""Session-stable item key.

Unit ids and pointers change between games, so the key is a content hash over the
decoded base, quality/identity, flags, every captured memory stat and the socket
contents. Research R4 (research.md, 2026-09-25) found no per-item seed in the D2R
item record, so this content hash is final: two items with identical content share
one key and appear as two placements.
"""

import hashlib
import json
from typing import Any


QUANTITY_STAT = 70  # stack size changes do not make a different item


def memory_stats(observation: dict[str, Any]) -> list[tuple[int, int, int]]:
    """Every (layer, id, raw) the decoder saw, from decoded, combined and unresolved entries."""
    found: list[tuple[int, int, int]] = []
    for entry in [*observation.get('decoded_stats', []), *observation.get('unresolved_stats', [])]:
        if 'memory_stats' in entry:
            stats = entry['memory_stats']
        elif 'memory_stat' in entry:
            stats = [entry['memory_stat']]
        else:
            stats = [entry]
        for stat in stats:
            if all(k in stat for k in ('layer', 'id', 'raw')) and stat['id'] != QUANTITY_STAT:
                found.append((stat['layer'], stat['id'], stat['raw']))
    return sorted(set(found))


def fingerprint(observation: dict[str, Any]) -> str:
    item = observation['item']
    identity = observation.get('source', {}).get('item_identity') or {}
    payload = {
        'base_code': item['base_code'],
        'rarity': item['rarity'],
        'identity': [identity.get('table'), identity.get('table_id')],
        'identified': item.get('identified'),
        'ethereal': item.get('ethereal'),
        'sockets': item.get('sockets'),
        'socket_items': [s.get('name') for s in item.get('socket_items', [])],
        'stats': memory_stats(observation),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()
