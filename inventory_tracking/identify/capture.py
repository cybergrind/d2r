"""Read which carried items are identified, and the full records of chosen ones.

The watcher only needs the identified flag of every magic-or-better item in the main
inventory and the Horadric Cube (one 0x60 item-data read each); the full stat arrays
are read only for the items that just became identified.
"""

import struct
from typing import Any

from inventory_tracking.collection.capture import read_item_record
from inventory_tracking.common import timestamp
from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.identity import FLAGS_OFFSET, IDENTIFIED_FLAG, ITEM_DATA_SIZE, QUALITY_OFFSET
from inventory_tracking.native.layout import SUPPORTED_SHA256, TOWN_IDS
from inventory_tracking.native.resource_probe import read_location
from inventory_tracking.native.units import describe_item, unit_matches
from inventory_tracking.shop.capture import _with_reader
from inventory_tracking.tracking.state import select_player


INVENTORY_PAGE = 0
CUBE_PAGE = 3
CARRIED_PAGES = frozenset((INVENTORY_PAGE, CUBE_PAGE))  # Cain identifies the cube's contents too
MAGIC_QUALITY = 4  # magic 4, set 5, rare 6, unique 7, crafted 8: everything that can be unidentified


def inventory_candidates(snapshot, player_id) -> list[dict[str, Any]]:
    """Magic-or-better items lying in the player's main inventory or cube (mode 0, page 0/3)."""
    return [
        unit
        for unit in snapshot['groups']['items']['units']
        if unit.get('mode') == 0
        and unit.get('details', {}).get('owner_id') == player_id
        and unit['details'].get('inventory_page') in CARRIED_PAGES
        and (unit['details'].get('quality') or 0) >= MAGIC_QUALITY
    ]


def identified_flag(data: bytes, quality) -> bool:
    if len(data) != ITEM_DATA_SIZE or struct.unpack_from('<I', data, QUALITY_OFFSET)[0] != quality:
        raise ValueError('Item data changed during read')
    return bool(struct.unpack_from('<I', data, FLAGS_OFFSET)[0] & IDENTIFIED_FLAG)


def probe_inventory(read, snapshot) -> dict[str, Any]:
    """`away` outside town; otherwise the identified state of every candidate by unit id.

    `owned` lists every item unit of the player (worn, stash and cursor included), so the
    watcher can tell an item that is new to the character from one that only moved.
    """
    groups = snapshot.get('groups', {})
    if (
        snapshot.get('status') != 'research'
        or not snapshot.get('mappings_stable')
        or not all(groups.get(name, {}).get('complete') for name in ('players', 'items'))
    ):
        raise ValueError('Incomplete or unstable inventory snapshot')
    player_id, _ = select_player(groups['players']['units'])
    player = next(p for p in groups['players']['units'] if p['unit_id'] == player_id)
    location = read_location(read, player['path_pointer'])
    if location not in TOWN_IDS:
        return {'state': 'away', 'location': location, 'player_id': player_id, 'items': {}}
    items = {}
    for unit in inventory_candidates(snapshot, player_id):
        details = unit['details']
        identified = identified_flag(read(unit['data_pointer'], ITEM_DATA_SIZE), details['quality'])
        if not unit_matches(read, unit) or describe_item(read, unit) != details:
            raise ValueError('Inventory changed during probe')
        items[str(unit['unit_id'])] = {
            'identified': identified,
            'quality': details['quality'],
            'txt_id': unit['txt_id'],
            'page': details['inventory_page'],
        }
    owned = sorted(
        str(unit['unit_id'])
        for unit in groups['items']['units']
        if unit.get('details', {}).get('owner_id') == player_id
    )
    return {'state': 'ok', 'location': location, 'player_id': player_id, 'items': items, 'owned': owned}


def capture_inventory_state(pid, images, capture):
    return _with_reader(pid, images, capture, probe_inventory)


def read_records(read, snapshot, unit_ids) -> dict[str, Any]:
    """Full item records (stats, item data, sockets) of the given inventory units."""
    groups = snapshot['groups']
    player_id, _ = select_player(groups['players']['units'])
    wanted = set(unit_ids)
    rows, issues = [], []
    for unit in inventory_candidates(snapshot, player_id):
        if str(unit['unit_id']) not in wanted:
            continue
        try:
            rows.append(read_item_record(read, unit, groups['items']['units']))
        except (OSError, ValueError, struct.error) as exc:
            issues.append(f'Item {unit["unit_id"]}: {exc}')
    missing = wanted - {str(row['unit_id']) for row in rows}
    for unit_id in sorted(missing):
        issues.append(f'Item {unit_id}: no longer in the inventory')
    return {'snapshot': snapshot, 'rows': rows, 'issues': issues}


def capture_records(pid, images, capture, unit_ids):
    return _with_reader(pid, images, capture, lambda read, snapshot: read_records(read, snapshot, unit_ids))


def decode_records(record) -> tuple[list[dict[str, Any]], list[str]]:
    snapshot = record['snapshot']
    report = {
        'state': 'complete',
        'finished_at': timestamp(),
        'game': {'identity': snapshot['identity'], 'executable_fingerprint': {'sha256': SUPPORTED_SHA256}},
    }
    observations, issues = [], list(record['issues'])
    for row in record['rows']:
        single = dict(snapshot, resources={'complete': True, 'items': [row]})
        try:
            [observation] = decode_items(single, report, inventory_page=row['details']['inventory_page'])
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(f'Item {row["unit_id"]}: {exc}')
            continue
        observations.append(observation)
    return observations, issues
