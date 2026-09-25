"""Research probe: raw records around the currency/materials stash (research.md).

Reads wider blocks than the capture keeps so the stack count field can be located
by correlating with counts the user reads off the in-game tab. Evidence only; no
interpretation here.
"""

import os
import struct
from typing import Any

from inventory_tracking.collection.capture import NO_OWNER, STASH_PAGE, is_shared_candidate, read_owner_grids
from inventory_tracking.items.metadata import item_base
from inventory_tracking.native.process import process_mappings
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.tracking.state import select_player


ITEM_DATA_WIDE = 0x100
STATS_WIDE = 0x200
UNIT_WIDE = 0x160
OWNER_DATA_WIDE = 0x200


def read_or_error(read, address, size) -> dict[str, Any]:
    try:
        return {'address': address, 'hex': read(address, size).hex()}
    except (OSError, ValueError) as exc:
        return {'address': address, 'error': str(exc)}


def probe_materials(pid, images, capture) -> dict[str, Any]:
    snapshot = sample_units(pid, images, capture, merc=True)
    if snapshot.get('status') != 'research':
        raise ValueError(snapshot.get('error', 'Unit snapshot unavailable'))
    groups = snapshot['groups']
    player_id, _ = select_player(groups['players']['units'])
    players = [u for u in groups['players']['units'] if u['type'] == 0]
    main = next(u for u in players if u['unit_id'] == player_id)
    materials = [
        u
        for u in groups['items']['units']
        if u['mode'] == 0
        and u['details'].get('owner_id') == NO_OWNER
        and u['details'].get('inventory_page') == STASH_PAGE
    ]
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, process_mappings(pid)).read
        owners = []
        for unit in players:
            if not is_shared_candidate(unit, main):
                continue
            entry: dict[str, Any] = {
                'unit_id': unit['unit_id'],
                'unit': read_or_error(read, unit['address'], UNIT_WIDE),
                'data': read_or_error(read, unit['data_pointer'], OWNER_DATA_WIDE),
                'stats_root': read_or_error(read, unit['stats_pointer'], STATS_WIDE) if unit['stats_pointer'] else None,
            }
            try:
                entry['grids'] = {
                    str(i): {'width': g['width'], 'height': g['height'], 'filled': sum(1 for c in g['cells'] if c)}
                    for i, g in read_owner_grids(read, unit).items()
                }
            except (OSError, ValueError, struct.error) as exc:
                entry['grids_error'] = str(exc)
            owners.append(entry)
        items = []
        for unit in materials:
            base = item_base(unit['txt_id']) or {}
            entry = {
                'unit_id': unit['unit_id'],
                'name': base.get('name'),
                'code': base.get('code'),
                'unit': read_or_error(read, unit['address'], UNIT_WIDE),
                'item_data': read_or_error(read, unit['data_pointer'], ITEM_DATA_WIDE),
                'stats_root': read_or_error(read, unit['stats_pointer'], STATS_WIDE) if unit['stats_pointer'] else None,
                'path': read_or_error(read, unit['path_pointer'], 0x40) if unit['path_pointer'] else None,
                'inventory': read_or_error(read, unit['inventory_pointer'], 0x48)
                if unit['inventory_pointer']
                else None,
            }
            items.append(entry)
    finally:
        os.close(fd)
    return {'identity': images['identity'], 'player_id': player_id, 'owners': owners, 'materials': items}
