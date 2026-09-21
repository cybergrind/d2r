"""Bounded item-stat and location reads with independent consistency checks."""

import struct
from typing import Any

from .layout import STAFF_CLASS_IDS, TOME_CLASS_ID
from .units import describe_item, read_stats, unit_matches


def read_location(read, path):
    fields = []

    def field(address, fmt):
        raw = read(address, struct.calcsize(fmt))
        fields.append((address, raw))
        value = struct.unpack(fmt, raw)[0]
        if not value:
            raise ValueError('Null location field')
        return value

    room = field(path + 0x20, '<Q')
    room2 = field(room + 0x18, '<Q')
    level = field(room2 + 0x90, '<Q')
    area = field(level + 0x1F8, '<I')
    if not 1 <= area <= 1024:
        raise ValueError('Area outside research bound')
    if any(read(address, len(raw)) != raw for address, raw in fields):
        raise ValueError('Location chain changed')
    return area


def read_item_arrays(read, pointer) -> dict[str, Any]:
    arrays = []
    for offset in (0x30, 0xA8, 0xE8):
        try:
            stats = read_stats(read, pointer + offset)
            if stats != read_stats(read, pointer + offset):
                return {'complete': False, 'arrays': arrays, 'reason': 'Item stat values changed during read'}
            arrays.append({'header_offset': offset, 'stats': stats})
        except (OSError, ValueError, struct.error) as exc:
            arrays.append({'header_offset': offset, 'reason': str(exc)})
    return {'complete': True, 'arrays': arrays}


def collect_resources(read, groups) -> dict[str, Any]:
    result: dict[str, Any] = {'complete': True, 'validated': False, 'items': [], 'locations': []}
    if not all(groups[name]['complete'] for name in ('players', 'items')):
        return dict(result, complete=False, reason='Incomplete player/item traversal')
    for player in groups['players']['units']:
        location = {'unit_id': player['unit_id']}
        try:
            location['area_id'] = read_location(read, player['path_pointer'])
            if not unit_matches(read, player):
                raise ValueError('Player identity changed during location read')
        except (OSError, ValueError, struct.error) as exc:
            location = {'unit_id': player['unit_id'], 'reason': str(exc)}
        result['locations'].append(location)
    for item in groups['items']['units']:
        if item['mode'] not in (0, 1) or item['txt_id'] not in STAFF_CLASS_IDS | {TOME_CLASS_ID}:
            continue
        record = {key: item[key] for key in ('unit_id', 'txt_id', 'mode', 'details')}
        record['resource_stats'] = read_item_arrays(read, item['stats_pointer'])
        try:
            if not unit_matches(read, item) or describe_item(read, item) != item['details']:
                raise ValueError('Resource item identity or location changed')
        except (OSError, ValueError, struct.error) as exc:
            result.update(complete=False, reason=str(exc))
        result['items'].append(record)
    return result
