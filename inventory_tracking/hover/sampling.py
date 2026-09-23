"""Bounded hover capture shared by appraisal and research probes."""

import os
import time

from inventory_tracking.hover.native import collect_native
from inventory_tracking.hover.ui import collect_ui
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader


def observe_ui(pid, images, snapshot=None, *, all_grids=False):
    if identity(pid) != images['identity']:
        raise ValueError('UI process changed before capture')
    base = images['candidate_base']
    pe = next(row['pe'] for row in images['images'] if row['base'] == base)
    mappings = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    started = time.monotonic()
    try:
        reader = ResearchReader(fd, mappings)
        mouse_before = reader.read(base + 0x1EC9C4D, 11)
        result = collect_ui(reader.read, base, pe['image_size'])
        if snapshot is not None:
            result['native'] = collect_native(reader.read, base, result, snapshot, all_grids=all_grids)
        result['mouse_position_hex'] = mouse_before.hex()
        result['stable'] &= reader.read(base + 0x1EC9C4D, 11) == mouse_before
    finally:
        os.close(fd)
    after = process_mappings(pid)
    result['mappings_stable'] = all(
        read_mappings(mappings, address, size) == read_mappings(after, address, size) for address, size in reader.ranges
    )
    result['process_stable'] = identity(pid) == images['identity']
    result['stable'] &= result['mappings_stable'] and result['process_stable']
    result.update(started_monotonic=started, finished_monotonic=time.monotonic(), identity=images['identity'])
    return result


def capture_ui_sample(observe, sample, observe_after=None):
    before = observe()
    units = sample()
    after = observe_after(units) if observe_after else observe()
    anchors_before = [(row['address'], row['before_hex']) for row in before['anchors']]
    anchors_after = [(row['address'], row['before_hex']) for row in after['anchors']]
    return {
        'validated': False,
        'atomic_snapshot': False,
        'before': before,
        'snapshot': units,
        'after': after,
        'ui_path_stable': before['stable']
        and after['stable']
        and anchors_before == anchors_after
        and before.get('mouse_position_hex') == after.get('mouse_position_hex'),
        'note': 'Path stability is not item selection or ownership validation; raw records require comparison.',
    }
