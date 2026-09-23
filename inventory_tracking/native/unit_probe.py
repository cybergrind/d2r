"""Bounded unit snapshots shared by diagnostics and the validated live reader."""

import os
import struct
import time
from bisect import bisect_right
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.images import read_pe
from inventory_tracking.native.mercenary import describe_monster
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.resource_probe import collect_resources
from inventory_tracking.native.units import describe_item, describe_player, summarize_research, unit_matches, walk_units
from inventory_tracking.reports import publish


class ResearchReader:
    def __init__(self, fd, mappings):
        self.fd = fd
        self.mappings = mappings
        self.starts = [m['start'] for m in mappings]
        self.bytes_requested = 0
        self.ranges = set()

    def read(self, address, size):
        self.bytes_requested += size
        if not 0 < size <= 8192 or self.bytes_requested > 8 * 1024 * 1024:
            raise ValueError('research read budget exceeded')
        cursor = address
        start_index = max(0, bisect_right(self.starts, address) - 1)
        for index in range(start_index, len(self.mappings)):
            mapping = self.mappings[index]
            if mapping['start'] > cursor:
                break
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


def sample_units(pid, images, capture, *, merc=False, resources=False, item_class=None) -> dict[str, Any]:
    """Return the complete in-memory research snapshot."""
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
        result: dict[str, Any] = {
            'status': 'research',
            'validated': False,
            'identity': token,
            'table_address': table_address,
            'sample_monotonic': time.monotonic(),
            'atomic_snapshot': False,
            'groups': {},
        }
        table_heads = {}
        group_specs = [(0, 'players', describe_player), (4, 'items', describe_item)]
        if merc:
            group_specs.append((1, 'monsters', describe_monster))
        for unit_type, label, describe in group_specs:
            table = table_address + unit_type * 1024
            heads = read(table, 1024)
            table_heads[label] = (table, heads)
            group = walk_units(read, struct.unpack('<128Q', heads), unit_type)
            for unit in group['units']:
                try:
                    unit['details'] = describe(read, unit)
                    stable = unit_matches(read, unit)
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
        # A unit checked early can change while later chains are traversed.
        # Recheck all headers and table heads at the end; this is still non-atomic.
        for label, group in result['groups'].items():
            for unit in group['units']:
                try:
                    stable = unit_matches(read, unit)
                    unit['identity_stable'] = unit.get('identity_stable', False) and stable
                    if not unit['identity_stable']:
                        raise ValueError('unit header changed during research')
                except (OSError, ValueError) as exc:
                    group['complete'] = False
                    group['errors'].append({'address': unit['address'], 'error': str(exc)})
            table, heads = table_heads[label]
            try:
                group['heads_stable'] = group['heads_stable'] and heads == read(table, 1024)
            except (OSError, ValueError) as exc:
                group['heads_stable'] = False
                group['errors'].append({'address': table, 'error': str(exc)})
            if not group['heads_stable']:
                group['complete'] = False
        result['sample_finished_monotonic'] = time.monotonic()
        after = process_mappings(pid)
        before_starts = [m['start'] for m in before]
        after_starts = [m['start'] for m in after]

        def relevant(mappings, starts, address, size):
            first = max(0, bisect_right(starts, address) - 1)
            last = bisect_right(starts, address + size - 1)
            return read_mappings(mappings[first:last], address, size)

        result['mappings_stable'] = all(
            relevant(before, before_starts, a, n) == relevant(after, after_starts, a, n) for a, n in reader.ranges
        )
        if identity(pid) != token or not result['mappings_stable']:
            result['status'] = 'stale'
        if resources or item_class is not None:
            # Separate budget and mappings: optional research cannot invalidate core data.
            optional = ResearchReader(fd, after)
            try:
                result['resources'] = collect_resources(
                    optional.read, result['groups'], **({'item_class': item_class} if item_class is not None else {})
                )
                for label in ('players', 'items'):
                    table, heads = table_heads[label]
                    if optional.read(table, 1024) != heads or any(
                        not unit_matches(optional.read, unit) for unit in result['groups'][label]['units']
                    ):
                        result['resources'].update(complete=False, reason='Resource traversal changed')
                final_mappings = process_mappings(pid)
                final_starts = [m['start'] for m in final_mappings]
                stable = all(
                    relevant(after, after_starts, a, n) == relevant(final_mappings, final_starts, a, n)
                    for a, n in optional.ranges
                )
                if identity(pid) != token or not stable:
                    result['resources'].update(complete=False, reason='Resource process/mappings changed')
            except (OSError, ValueError) as exc:
                result['resources'] = {'complete': False, 'reason': str(exc)}
        result['bytes_requested'] = reader.bytes_requested
    finally:
        os.close(fd)
    return result


def inspect_units(pid, images, capture, directory, *, log_summary=True, merc=False, resources=False, item_class=None):
    result = sample_units(
        pid,
        images,
        capture,
        merc=merc,
        **({'resources': True} if resources else {}),
        **({'item_class': item_class} if item_class is not None else {}),
    )
    if 'groups' not in result:
        return result
    publish(directory / 'units.json', result)
    counts = {name: len(group['units']) for name, group in result['groups'].items()}
    log = LOG.info if log_summary else LOG.debug
    log('Unit research: %s; counts=%s', result['status'], counts)
    complete = all(g['complete'] for g in result['groups'].values())
    if item_class is not None:
        resources_result = result.get('resources', {})
        selected = [row for row in resources_result.get('items', []) if row['txt_id'] == item_class]
        complete = (
            complete
            and resources_result.get('complete', False)
            and bool(selected)
            and all(
                row['resource_stats'].get('complete', False)
                and any(array.get('stats') for array in row['resource_stats'].get('arrays', []))
                for row in selected
            )
        )
    summary = summarize_research(result['groups']) if result['status'] == 'research' and complete else {}
    log('Candidate summary (unvalidated): %s', summary)
    return {
        'status': result['status'],
        'validated': False,
        'manifest': 'units.json',
        'counts': counts,
        'complete': complete,
        'summary': summary,
    }
