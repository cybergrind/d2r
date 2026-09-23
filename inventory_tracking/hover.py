"""Candidate hover layout; requires controlled host validation before hotkey use.

Layout lead: relentlessricktrinidad/d2go pkg/memory/{offset,game_reader}.go,
inspected 2026-09-23. Signature match alone is not layout validation.
"""

import re
import struct


PATTERN = re.compile(rb'\xc6\x84\xc2.....\x48\x8b\x74', re.DOTALL)


def scan_hover(blocks, base, image_size):
    tail, end, candidates = b'', None, set()
    for address, data in blocks:
        if address != end:
            tail = b''
        combined = tail + data
        for match in PATTERN.finditer(combined):
            rva = struct.unpack_from('<I', match.group(), 3)[0] - 1
            if 0 <= rva <= image_size - 12:
                candidates.add(rva)
        tail, end = combined[-10:], address + len(data)
    return sorted(candidates)


def parse_hover(raw):
    if len(raw) != 12:
        raise ValueError('Short hover read')
    active, _, unit_type, unit_id = struct.unpack('<HHII', raw)
    if not active:
        return None
    if unit_type > 5:
        raise ValueError('Invalid hovered unit type')
    return {'unit_type': unit_type, 'unit_id': unit_id}


def capture_selection(read_hover, sample):
    before = read_hover()
    if before is None or before['unit_type'] != 4:
        return {'status': 'no_item', 'hover': before, 'validated': False}
    snapshot = sample()
    if before != read_hover():
        raise ValueError('Hover changed during capture')
    group = snapshot.get('groups', {}).get('items', {})
    matches = [row for row in group.get('units', []) if row['unit_id'] == before['unit_id']]
    if snapshot.get('status') != 'research' or not group.get('complete') or len(matches) != 1:
        raise ValueError('No unique stable hovered item in traversal')
    if not matches[0].get('identity_stable'):
        raise ValueError('Hovered item is not stable')
    return {'status': 'candidate', 'hover': before, 'item': matches[0], 'snapshot': snapshot, 'validated': False}


def read_indexed_hover(read, table_address, selector_address):
    selector = read(selector_address, 4)
    slot = struct.unpack('<I', selector)[0]
    if slot > 15:
        raise ValueError('Hover selector outside research bound')
    raw = read(table_address + slot * 16, 12)
    if read(selector_address, 4) != selector:
        raise ValueError('Hover selector changed during read')
    if read(table_address + slot * 16, 12) != raw:
        raise ValueError('Hover changed during read')
    return {'hover': parse_hover(raw), 'slot': slot, 'raw_hex': raw.hex()}
