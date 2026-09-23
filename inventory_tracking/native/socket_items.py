"""Bounded socket-parent linkage from ItemData +0xA0 -> +0x08.

Layout source: pinned third-parties/d2go/pkg/memory/item.go. Every accepted link
must point to the selected parent unit exactly and survive a second read.
"""

import struct
from typing import Any

from inventory_tracking.native.units import describe_item, unit_matches


MAX_SOCKET_CANDIDATES = 256
ITEM_EXTRA_OFFSET = 0xA0
PARENT_UNIT_OFFSET = 0x08


def read_socket_items(read, parent, candidates):
    """Candidates must be from a complete, stable item-unit traversal."""
    units = [u for u in candidates if u.get('mode') == 6]
    if len(units) > MAX_SOCKET_CANDIDATES:
        raise ValueError('Socket candidate count exceeds bound')
    children: list[dict[str, Any]] = []
    fields = []

    def field(address, size):
        data = read(address, size)
        if len(data) != size:
            raise ValueError('Incomplete socket field')
        fields.append((address, data))
        return data

    for unit in units:
        if not unit_matches(read, unit):
            raise ValueError('Socket candidate identity changed')
        extra = struct.unpack('<Q', field(unit['data_pointer'] + ITEM_EXTRA_OFFSET, 8))[0]
        if not extra:
            continue
        parent_address = struct.unpack('<Q', field(extra + PARENT_UNIT_OFFSET, 8))[0]
        if parent_address != parent['address']:
            continue
        if not unit_matches(read, unit) or describe_item(read, unit) != unit['details']:
            raise ValueError('Socket child changed')
        position = unit['details'].get('x')
        if type(position) is not int or not 0 <= position < 6:
            raise ValueError('Socket position outside bound')
        children.append({'unit': unit, 'position': position, 'item_data_hex': field(unit['data_pointer'], 0x60).hex()})
    positions = [c['position'] for c in children]
    if len(positions) != len(set(positions)):
        raise ValueError('Duplicate socket position')
    if any(read(a, len(data)) != data for a, data in fields):
        raise ValueError('Socket parent linkage changed')
    if not unit_matches(read, parent) or any(
        not unit_matches(read, c['unit']) or describe_item(read, c['unit']) != c['unit']['details'] for c in children
    ):
        raise ValueError('Socket unit identity changed')
    return {
        'complete': True,
        'children': sorted(children, key=lambda c: c['position']),
        'candidate_units': units,
        'source': {'item_extra_offset': ITEM_EXTRA_OFFSET, 'parent_unit_offset': PARENT_UNIT_OFFSET},
    }
