"""Decode the ring fields validated against the 2026-09-23 host capture.

This is a narrow snapshot adapter, not a general item decoder. No memory access.
Memory stat IDs and market property IDs are deliberately separate namespaces.
"""

from collections import Counter

from .layout import SUPPORTED_SHA256
from .state import select_player


# Observed on build 1e2ac459..., unit 438836750, array +0xE8; screenshot comparison.
# Property IDs/labels verified from local appraisal-properties.json.
RING_CLASS = 537  # Local d2data misc.json classid, code rin.
RING_STATS = {
    11: ('452', 256, '+{{value}} Maximum Stamina'),
    105: ('520', 1, '+{{value}}% Faster Cast Rate'),
}


def decode_rings(snapshot, report):
    """Return owned inventory magic-ring observations; unknown fields stay unknown."""
    if report.get('game', {}).get('executable_fingerprint', {}).get('sha256') != SUPPORTED_SHA256:
        raise ValueError('Unsupported game build')
    if report.get('state') != 'complete' or snapshot.get('status') != 'research':
        raise ValueError('Incomplete or stale capture')
    if not snapshot.get('identity') or snapshot['identity'] != report.get('game', {}).get('identity'):
        raise ValueError('Capture process identity mismatch')
    groups = snapshot.get('groups', {})
    resources = snapshot.get('resources', {})
    if (
        not snapshot.get('mappings_stable')
        or not resources.get('complete')
        or not all(groups.get(name, {}).get('complete') for name in ('players', 'items'))
    ):
        raise ValueError('Unstable item snapshot')
    player_id, _ = select_player(groups['players']['units'])
    results = []
    for row in resources.get('items', []):
        details = row['details']
        if (
            row['txt_id'] != RING_CLASS
            or row['mode'] != 0
            or details.get('owner_id') != player_id
            or details.get('inventory_page') != 0
            or details.get('quality') != 4
        ):
            continue
        arrays = row.get('resource_stats', {})
        candidates = [a for a in arrays.get('arrays', []) if a.get('header_offset') == 0xE8]
        if not arrays.get('complete') or len(candidates) != 1 or not candidates[0].get('stats'):
            raise ValueError('Ring stat array missing or changed')
        stats = candidates[0]['stats']
        counts = Counter(s['id'] for s in stats)
        affixes, unresolved = [], []
        for stat in stats:
            spec = RING_STATS.get(stat['id'])
            if (
                spec is None
                or stat['layer'] != 0
                or counts[stat['id']] != 1
                or type(stat['raw']) is not int
                or stat['raw'] < 0
                or stat['raw'] % spec[1]
            ):
                unresolved.append(stat)
                continue
            property_id, divisor, label = spec
            affixes.append(
                {
                    'property_id': property_id,
                    'value': stat['raw'] // divisor,
                    'label': label,
                    'memory_stat': stat,
                    'descriptor_offset': 0xE8,
                }
            )
        results.append(
            {
                'item': {
                    'name': 'Ring',
                    'base_name': 'Ring',
                    'base_code': 'rin',
                    'rarity': 'magic',
                    'requirements': {},
                    'affixes': affixes,
                    'sockets': None,
                    'ethereal': None,
                    'socket_contents': None,
                },
                'source': {
                    'engine': 'memory_snapshot',
                    'unit_id': row['unit_id'],
                    'owner_id': player_id,
                    'position': [details.get('x'), details.get('y')],
                    'run_id': report.get('run_id'),
                    'captured_at': report.get('finished_at'),
                    'snapshot_only': True,
                    'build_sha256': SUPPORTED_SHA256,
                },
                'unresolved_stats': unresolved,
                'review': [
                    'Title, required level, flags and general affix coverage are not decoded.',
                    'Snapshot evidence is historical; it does not establish current inventory state.',
                ],
                'appraisal_ready': False,
                'offline': True,
                'status': 'needs_review',
            }
        )
    if not results:
        raise ValueError('No owned inventory magic rings in this capture')
    return results
