"""Bounded D2R unit traversal using the supported build layout.

Layout lead: d2go/pkg/memory/{player,item,game_reader}.go (2026-09-21).
The live signature's following instructions independently use next link +0x158.
"""

import struct
from typing import Any

from .layout import BELT_ITEM_MODE, DEAD_MODES, HIRELING_CLASS_ID


def walk_units(read, heads, expected_type, *, max_units=2048) -> dict[str, Any]:
    result: dict[str, Any] = {'units': [], 'errors': [], 'complete': True}
    visited = set()
    for bucket, pointer in enumerate(heads):
        while pointer:
            try:
                if pointer in visited:
                    raise ValueError('cycle or duplicate unit pointer')
                if len(visited) >= max_units:
                    raise ValueError('unit traversal budget reached')
                visited.add(pointer)
                data = read(pointer, 0x160)
                if len(data) != 0x160:
                    raise ValueError('short unit read')
                unit_type, txt_id, unit_id, mode = struct.unpack_from('<IIII', data)
                if unit_type != expected_type or unit_id % 128 != bucket:
                    raise ValueError('unit type or bucket mismatch')
                result['units'].append(
                    {
                        'address': pointer,
                        'type': unit_type,
                        'txt_id': txt_id,
                        'unit_id': unit_id,
                        'mode': mode,
                        'data_pointer': struct.unpack_from('<Q', data, 0x10)[0],
                        'path_pointer': struct.unpack_from('<Q', data, 0x38)[0],
                        'stats_pointer': struct.unpack_from('<Q', data, 0x88)[0],
                        'inventory_pointer': struct.unpack_from('<Q', data, 0x90)[0],
                        'next_pointer': struct.unpack_from('<Q', data, 0x158)[0],
                    }
                )
                pointer = result['units'][-1]['next_pointer']
            except (OSError, ValueError) as exc:
                result['errors'].append({'bucket': bucket, 'address': pointer, 'error': str(exc)})
                result['complete'] = False
                break
    return result


def unit_matches(read, unit):
    """Recheck every header field used to locate or interpret unit details."""
    data = read(unit['address'], 0x160)
    if len(data) != 0x160:
        raise ValueError('short unit verification read')
    fields = [
        ('type', '<I', 0),
        ('txt_id', '<I', 4),
        ('unit_id', '<I', 8),
        ('mode', '<I', 0x0C),
        ('data_pointer', '<Q', 0x10),
        ('path_pointer', '<Q', 0x38),
        ('stats_pointer', '<Q', 0x88),
        ('inventory_pointer', '<Q', 0x90),
        ('next_pointer', '<Q', 0x158),
    ]
    if unit['type'] == 1:
        # Monster animation changes are normal during combat. For hirelings,
        # preserve the dead/dying boundary; other monsters are traversal only.
        fields = [field for field in fields if field[0] != 'mode']
        if unit['txt_id'] == HIRELING_CLASS_ID:
            mode = struct.unpack_from('<I', data, 0x0C)[0]
            if (mode in DEAD_MODES) != (unit['mode'] in DEAD_MODES):
                return False
    return all(struct.unpack_from(fmt, data, offset)[0] == unit[name] for name, fmt, offset in fields)


def read_stats(read, address):
    header = read(address, 16)
    pointer, count = struct.unpack('<QQ', header)
    if count > 1024:
        raise ValueError('stat count exceeds research bound')
    data = read(pointer, count * 8) if count else b''
    if read(address, 16) != header:
        raise ValueError('stat array header changed during read')
    return [{'layer': layer, 'id': stat_id, 'raw': raw} for layer, stat_id, raw in struct.iter_unpack('<HHi', data)]


def describe_player(read, unit):
    name = read(unit['data_pointer'], 16).split(b'\0', 1)[0].decode('utf-8', errors='replace')
    inventory = read(unit['inventory_pointer'], 0x78) if unit['inventory_pointer'] else bytes(0x78)
    result = {
        'name': name,
        'inventory_marker_30': struct.unpack_from('<H', inventory, 0x30)[0],
        'inventory_marker_70': struct.unpack_from('<H', inventory, 0x70)[0],
    }
    # +0xe8 verified by gear changes on disk hash 1e2ac459... (3.3.93787).
    # Older d2go's +0xa8 is empty here; this remains build-specific research.
    for label, offset in [('base_stats', 0x30), ('full_stats', 0xE8)]:
        try:
            stats = read_stats(read, unit['stats_pointer'] + offset)
            result[label] = stats
            life = {x['id']: x['raw'] for x in stats if x['layer'] == 0 and x['id'] in (6, 7)}
            if 6 in life and 7 in life:
                result[label + '_hp_candidate'] = {'current': life[6] / 256, 'max': life[7] / 256}
        except (OSError, ValueError) as exc:
            result[label] = {'error': str(exc)}
    result['stat_array_candidates'] = discover_stat_arrays(read, unit['stats_pointer'])
    return result


def discover_stat_arrays(read, address) -> list[dict[str, Any]]:
    """Inspect bounded adjacent descriptors without assuming a full-stat offset."""
    header = read(address, 0x200)
    candidates = []
    for offset in range(0, len(header) - 15, 8):
        pointer, count = struct.unpack_from('<QQ', header, offset)
        if not 0x10000 <= pointer < 2**47 or pointer % 8 or not 1 <= count <= 1024:
            continue
        try:
            data = read(pointer, count * 8)
            stats = [
                {'layer': layer, 'id': stat_id, 'raw': raw} for layer, stat_id, raw in struct.iter_unpack('<HHi', data)
            ]
            if len(stats) == count and all(x['id'] < 2048 for x in stats):
                candidates.append({'header_offset': offset, 'array_address': pointer, 'stats': stats})
        except OSError, ValueError:
            continue
    if read(address, 0x200) != header:
        return []
    return candidates


def describe_item(read, unit):
    data = read(unit['data_pointer'], 0x60)
    result = {
        'quality': struct.unpack_from('<I', data)[0],
        'owner_id': struct.unpack_from('<I', data, 0x0C)[0],
        'inventory_page': data[0x55],
        'body_location': data[0x54],
    }
    if unit['path_pointer']:
        path = read(unit['path_pointer'], 0x20)
        result.update(x=struct.unpack_from('<H', path, 0x10)[0], y=struct.unpack_from('<H', path, 0x14)[0])
    return result


def summarize_research(groups):
    """Human-readable candidate values, never local-player or controller state."""
    players = []
    for unit in groups['players']['units']:
        details = unit['details']
        health = []
        for array in details.get('stat_array_candidates', []):
            values = {s['id']: s['raw'] for s in array['stats'] if s['layer'] == 0}
            if 6 in values and 7 in values:
                health.append(
                    {
                        'descriptor_offset': hex(array['header_offset']),
                        'current': values[6] >> 8,
                        'max': values[7] >> 8,
                        'plausible': 0 <= values[6] <= values[7] and values[7] > 0,
                    }
                )
        if health:
            players.append({'unit_id': unit['unit_id'], 'name': details.get('name'), 'health_candidates': health})
    belt = []
    # IDs/names verified against blizzhackers/d2data misc.json on 2026-09-21.
    names = {531: 'Full Rejuvenation Potion', 606: 'Super Healing Potion'}
    for unit in groups['items']['units']:
        if unit['mode'] != BELT_ITEM_MODE or 'error' in unit['details']:
            continue
        d = unit['details']
        belt.append(
            {
                'unit_id': unit['unit_id'],
                'owner_id': d['owner_id'],
                'cell_index': d.get('x'),
                'path_y': d.get('y'),
                'txt_id': unit['txt_id'],
                'name': names.get(unit['txt_id'], 'unknown'),
            }
        )
    return {'players': players, 'belt_candidates': belt}
