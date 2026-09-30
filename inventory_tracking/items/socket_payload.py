"""Decode only a linked child's captured total stats; never parent totals."""

from inventory_tracking.items.metadata import decode_stats
from inventory_tracking.items.stat_constants import TOTAL_STATS_DESCRIPTOR_OFFSET


def decode_payload(child, base):
    capture = child.get('stat_arrays', {})
    candidates = [a for a in capture.get('arrays', []) if a.get('header_offset') == TOTAL_STATS_DESCRIPTOR_OFFSET]
    result = {'item_type': base['type'], 'stats': {}, 'stats_complete': False}
    if capture.get('complete') is not True or len(candidates) != 1 or 'stats' not in candidates[0]:
        return result
    decoded, _, unresolved = decode_stats(candidates[0]['stats'], base=base)
    for row in decoded:
        for native in row.get('memory_stats', [row.get('memory_stat')]):
            if not native:
                continue
            key = f'{native["id"]}:{native["layer"]}'
            semantic = row.get('native_values', {}).get(key, row)
            result['stats'][key] = {
                'status': row['status'],
                'value': semantic.get('value'),
                'raw': native['raw'],
                **({'unit': semantic['unit']} if 'unit' in semantic else {}),
            }
    result['stats_complete'] = not unresolved
    return result
