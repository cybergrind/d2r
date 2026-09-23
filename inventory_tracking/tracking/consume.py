"""Optional Consume observation, called after LiveReader's executable build gate.

2026-09-21 probes: state bit +0xB48/0x10000, list head +0xD0,
previous +0x68, state +0x20, stats +0x30. Applied level survives gear swap.
"""

import os
import struct
import time

from inventory_tracking.models import ConsumeBuff, Observation
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import read_stats, unit_matches


def read_consume(read, root):
    flag = read(root + 0xB48, 4)
    head = read(root + 0xD0, 8)
    active = bool(struct.unpack('<I', flag)[0] & 0x10000)
    pointer = struct.unpack('<Q', head)[0]
    nodes = {}
    found = []
    while pointer:
        if pointer in nodes or len(nodes) >= 128:
            raise ValueError('Consume list cycle or budget exceeded')
        raw = read(pointer, 0x80)
        nodes[pointer] = raw
        if struct.unpack_from('<I', raw, 0x20)[0] == 208:
            stats = read_stats(read, pointer + 0x30)
            if stats != read_stats(read, pointer + 0x30):
                raise ValueError('Consume stats changed')
            skills = [s['raw'] for s in stats if s['id'] == 350 and s['layer'] == 0]
            levels = [s['raw'] for s in stats if s['id'] == 351 and s['layer'] == 0]
            level = levels[0] if skills == [381] and len(levels) == 1 and 1 <= levels[0] <= 255 else None
            found.append(ConsumeBuff(True, level, pointer))
        pointer = struct.unpack_from('<Q', raw, 0x68)[0]
    for address, raw in nodes.items():
        if read(address, 0x80) != raw:
            raise ValueError('Consume list changed')
    if read(root + 0xD0, 8) != head or read(root + 0xB48, 4) != flag:
        raise ValueError('Consume state changed')
    if len(found) > 1 or (found and not active):
        raise ValueError('Inconsistent Consume state')
    return found[0] if found else ConsumeBuff(active)


def observe_consume(pid, images, snapshot, player_id):
    sampled = time.monotonic()
    try:
        token = images['identity']
        player = next(p for p in snapshot['groups']['players']['units'] if p['unit_id'] == player_id)
        before = process_mappings(pid)
        if identity(pid) != token:
            raise ValueError('Consume process changed')
        fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        try:
            reader = ResearchReader(fd, before)
            if not unit_matches(reader.read, player):
                raise ValueError('Consume player changed')
            value = read_consume(reader.read, player['stats_pointer'])
            if not unit_matches(reader.read, player):
                raise ValueError('Consume player changed')
        finally:
            os.close(fd)
        after = process_mappings(pid)
        if identity(pid) != token or any(
            read_mappings(before, address, size) != read_mappings(after, address, size)
            for address, size in reader.ranges
        ):
            raise ValueError('Consume process/mappings changed')
        return Observation(sampled, value)
    except (OSError, ValueError, KeyError, StopIteration, struct.error) as exc:
        return Observation.unavailable(sampled, str(exc))
