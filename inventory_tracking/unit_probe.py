"""Bounded live unit research; never publishes controller-ready state."""

import os
import struct
import time

from .common import LOG
from .image_probe import read_mappings
from .images import read_pe
from .linux_process import identity, process_mappings
from .reports import publish
from .units import describe_item, describe_player, summarize_research, walk_units


class ResearchReader:
    def __init__(self, fd, mappings):
        self.fd = fd
        self.mappings = mappings
        self.bytes_requested = 0
        self.ranges = set()

    def read(self, address, size):
        self.bytes_requested += size
        if not 0 < size <= 8192 or self.bytes_requested > 8 * 1024 * 1024:
            raise ValueError('research read budget exceeded')
        cursor = address
        for mapping in self.mappings:
            if mapping['start'] <= cursor < mapping['end']:
                if not mapping['permissions'].startswith('r'):
                    break
                cursor = min(address + size, mapping['end'])
                if cursor == address + size:
                    self.ranges.add((address, size))
                    data = os.pread(self.fd, size, address)
                    if len(data) != size:
                        raise ValueError('short research read')
                    return data
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')


def inspect_units(pid, images, capture, directory):
    candidates = capture['unit_table_candidates']
    addresses = sorted({x['table_address'] for x in candidates})
    if len(addresses) != 1:
        return {'status': 'unavailable', 'error': 'Expected one freshly scanned table address'}
    token = images['identity']
    base = images['candidate_base']
    pe = next(x['pe'] for x in images['images'] if x['base'] == base)
    if identity(pid) != token:
        return {'status': 'stale', 'error': 'Process changed before unit research'}
    before = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, before)
        read = reader.read
        if identity(pid) != token or read_pe(lambda o, n: read(base + o, n)) != pe:
            return {'status': 'stale', 'error': 'Image identity changed'}
        table_address = addresses[0]
        result = {
            'status': 'research',
            'validated': False,
            'identity': token,
            'table_address': table_address,
            'sample_monotonic': time.monotonic(),
            'atomic_snapshot': False,
            'groups': {},
        }
        for unit_type, label, describe in [(0, 'players', describe_player), (4, 'items', describe_item)]:
            table = table_address + unit_type * 1024
            heads = read(table, 1024)
            group = walk_units(read, struct.unpack('<128Q', heads), unit_type)
            for unit in group['units']:
                try:
                    unit['details'] = describe(read, unit)
                    check = read(unit['address'], 0x160)
                    stable = (
                        struct.unpack_from('<I', check)[0] == unit['type']
                        and struct.unpack_from('<I', check, 8)[0] == unit['unit_id']
                        and struct.unpack_from('<Q', check, 0x158)[0] == unit['next_pointer']
                    )
                    unit['identity_stable'] = stable
                    if not stable:
                        group['complete'] = False
                except (OSError, ValueError) as exc:
                    unit['details'] = {'error': str(exc)}
                    group['complete'] = False
            group['heads_stable'] = heads == read(table, 1024)
            if not group['heads_stable']:
                group['complete'] = False
            result['groups'][label] = group
        after = process_mappings(pid)
        result['mappings_stable'] = all(
            read_mappings(before, a, n) == read_mappings(after, a, n) for a, n in reader.ranges
        )
        if identity(pid) != token or not result['mappings_stable']:
            result['status'] = 'stale'
        result['bytes_requested'] = reader.bytes_requested
    finally:
        os.close(fd)
    publish(directory / 'units.json', result)
    counts = {name: len(group['units']) for name, group in result['groups'].items()}
    LOG.info('Unit research: %s; counts=%s', result['status'], counts)
    summary = summarize_research(result['groups']) if result['status'] == 'research' else {}
    LOG.info('Candidate summary (unvalidated): %s', summary)
    return {
        'status': result['status'],
        'validated': False,
        'manifest': 'units.json',
        'counts': counts,
        'complete': all(g['complete'] for g in result['groups'].values()),
        'summary': summary,
    }
