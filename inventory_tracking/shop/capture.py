"""Read loaded NPC stock across all four tabs, without opening or manipulating UI.

Stock identity for the automatic watcher is the first gear item (weapons/armor
category) in vendor, tab and cell order: its base, quality, cell and native stats.
Unit IDs and addresses are excluded so a closed and reopened shop keeps its key.
"""

import os
import time
from typing import Any

from inventory_tracking.collection.capture import NO_OWNER, read_item_record, read_owner_grids
from inventory_tracking.common import timestamp
from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.identity import IDENTIFIED_FLAG, item_flags
from inventory_tracking.items.metadata import item_base
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.layout import SUPPORTED_SHA256, TOWN_IDS
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.resource_probe import read_location
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.native.units import describe_item, unit_matches
from inventory_tracking.tracking.state import select_player


GEAR_CATEGORIES = frozenset({'weapons', 'armor'})
SHOP_GRIDS = (2, 3, 4, 5)

# d2data/json/monstats.json *hcIdx; supported-build Drognan grids verified by
# shop-probe/20260926T084304Z-6bc59abc. Names are display labels, not item codes.
VENDORS = {
    148: 'Akara',
    154: 'Charsi',
    147: 'Gheed',
    177: 'Drognan',
    199: 'Elzix',
    178: 'Fara',
    202: 'Lysander',
    254: 'Alkor',
    252: 'Asheara',
    253: 'Hratli',
    255: 'Ormus',
    257: 'Halbu',
    405: 'Jamella',
    511: 'Larzuk',
    512: 'Anya',
    513: 'Malah',
    514: 'Nihlathak',
}


def stock_members(snapshot, owners):
    """Resolve each occupied shop cell to one stable unit with matching page/ownership.

    Vendors are ordered by name, then tab, then top-left cell, so "the first item"
    is the same on every read of the same stock.
    """
    by_address = {u['address']: u for u in snapshot['groups']['items']['units']}
    selected = []
    seen: dict[int, tuple[int, int]] = {}  # pointer -> (owner record, grid index); large items span cells
    for owner in sorted(owners, key=lambda o: (o['name'], o['unit']['unit_id'])):
        for index in SHOP_GRIDS:
            grid = owner['grids'].get(index)
            if grid is None:
                continue
            if (grid['width'], grid['height']) != (10, 10):
                raise ValueError('Unexpected shop grid dimensions')
            for pointer in grid['cells']:
                if not pointer:
                    continue
                if pointer in seen:
                    if seen[pointer] != (id(owner), index):
                        raise ValueError('Item belongs to multiple shop grids')
                    continue
                seen[pointer] = (id(owner), index)
                unit = by_address.get(pointer)
                if unit is None or not unit.get('identity_stable'):
                    raise ValueError('Shop grid item missing from stable unit table')
                details = unit['details']
                if (unit['type'], unit['mode'], details.get('owner_id'), details.get('inventory_page')) != (
                    4,
                    0,
                    NO_OWNER,
                    index - 2,
                ):
                    raise ValueError('Shop item ownership/page mismatch')
                selected.append((owner, unit))
    return selected


def gear_sentinel(selected):
    """The first weapons/armor item in stock order, or None when only consumables are loaded."""
    for owner, unit in selected:
        base = item_base(unit['txt_id'])
        if base and base.get('category') in GEAR_CATEGORIES:
            return owner, unit
    return None


def sentinel_key(owner, unit, row):
    """Content identity of the sentinel item; independent of unit IDs and addresses."""
    details = unit['details']
    arrays = row['resource_stats']
    flags = item_flags(row['details'], arrays)
    return {
        'vendor': owner['name'],
        'txt_id': unit['txt_id'],
        'quality': details.get('quality'),
        'page': details.get('inventory_page'),
        'x': details.get('x'),
        'y': details.get('y'),
        'identified': None if flags is None else bool(flags & IDENTIFIED_FLAG),
        'stats': sorted((s['layer'], s['id'], s['raw']) for a in arrays['arrays'] for s in a.get('stats', [])),
    }


def locate_stock(read, snapshot):
    """Player location, vendor grids and ordered stock members; no item stats are read."""
    groups = snapshot.get('groups', {})
    if (
        snapshot.get('status') != 'research'
        or not snapshot.get('mappings_stable')
        or not all(groups.get(name, {}).get('complete') for name in ('players', 'items', 'monsters'))
    ):
        raise ValueError('Incomplete or unstable shop snapshot')
    player_id, _ = select_player(groups['players']['units'])
    player = next(p for p in groups['players']['units'] if p['unit_id'] == player_id)
    location = read_location(read, player['path_pointer'])
    owners = []
    if location in TOWN_IDS:
        for unit in groups['monsters']['units']:
            if unit['txt_id'] in VENDORS and unit.get('identity_stable'):
                grids = read_owner_grids(read, unit)
                owners.append({'unit': unit, 'name': VENDORS[unit['txt_id']], 'grids': grids})
    return {
        'player': player,
        'location': location,
        'owners': owners,
        'selected': stock_members(snapshot, owners) if location in TOWN_IDS else [],
    }


def read_stock(read, snapshot):
    located = locate_stock(read, snapshot)
    player, location, owners, selected = located['player'], located['location'], located['owners'], located['selected']
    if location not in TOWN_IDS:
        raise ValueError('Shop checking is available in town')
    groups = snapshot['groups']
    sentinel = gear_sentinel(selected)
    sentinel_row = None
    rows = []
    issues = []
    rejected_rows: list[dict[str, Any]] = []
    for owner, unit in selected:
        row = None
        try:
            row = read_item_record(read, unit, groups['items']['units'])
            flags = item_flags(row['details'], row['resource_stats'])
            # Buyback items can lack IFLAG_INSTORE: D2MOO ITEMS_Duplicate clears
            # it and STORES_SellItem sets the separate unit vendor flag instead.
            # Revalidated NPC grid membership is the ownership proof.
            if flags is None:
                raise ValueError('Shop item flags unreadable or quality mismatch')
            rows.append({'owner_id': owner['unit']['unit_id'], 'vendor': owner['name'], 'row': row})
            if sentinel is not None and unit is sentinel[1]:
                sentinel_row = row
        except (OSError, ValueError) as exc:
            issues.append(f'{owner["name"]} item {unit["unit_id"]}: {exc}')
            rejected_rows.append({'vendor': owner['name'], 'unit': unit, 'row': row, 'error': str(exc)})
    for owner in owners:
        if not unit_matches(read, owner['unit']) or read_owner_grids(read, owner['unit']) != owner['grids']:
            raise ValueError('Shop stock changed during scan; press Win+D again')
    for _, unit in selected:
        if not unit_matches(read, unit) or describe_item(read, unit) != unit['details']:
            raise ValueError('Shop item changed during scan; press Win+D again')
    if not unit_matches(read, player) or read_location(read, player['path_pointer']) != location:
        raise ValueError('Player left the shop area during scan')
    return {
        'snapshot': snapshot,
        'owners': owners,
        'rows': rows,
        'rejected_rows': rejected_rows,
        'issues': issues,
        'location': location,
        'stock_count': len(selected),
        'sentinel': sentinel_key(*sentinel, sentinel_row) if sentinel is not None and sentinel_row else None,
    }


def probe_stock(read, snapshot):
    """Cheap stock identity for the watcher: grids plus one item record, never the whole stock.

    States: `away` (not in town), `unloaded` (no vendor stock in memory, e.g. Trade
    closed), `no_gear` (consumables only), `gamble` (sentinel unidentified) and
    `loaded` with the sentinel `key`.
    """
    located = locate_stock(read, snapshot)
    player, location, selected = located['player'], located['location'], located['selected']
    if location not in TOWN_IDS:
        return {'state': 'away', 'stock_count': 0}
    result: dict[str, Any] = {'stock_count': len(selected), 'vendors': sorted({o['name'] for o, _ in selected})}
    if not selected:
        return result | {'state': 'unloaded'}
    sentinel = gear_sentinel(selected)
    if sentinel is None:
        return result | {'state': 'no_gear'}
    owner, unit = sentinel
    row = read_item_record(read, unit, snapshot['groups']['items']['units'])
    key = sentinel_key(owner, unit, row)
    if key['identified'] is None:
        raise ValueError('Sentinel item flags unreadable')
    if not unit_matches(read, owner['unit']) or read_owner_grids(read, owner['unit']) != owner['grids']:
        raise ValueError('Shop stock changed during probe')
    if not unit_matches(read, player) or read_location(read, player['path_pointer']) != location:
        raise ValueError('Player moved during probe')
    return result | {'state': 'loaded' if key['identified'] else 'gamble', 'key': key}


def _with_reader(pid, images, capture, work):
    started = time.monotonic()
    snapshot = sample_units(pid, images, capture, merc=True)
    if snapshot.get('status') != 'research':
        raise ValueError(snapshot.get('error', 'Unit snapshot unavailable'))
    before = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, before)
        record = work(reader.read, snapshot)
        after = process_mappings(pid)
        if identity(pid) != images['identity'] or any(
            read_mappings(before, a, n) != read_mappings(after, a, n) for a, n in reader.ranges
        ):
            raise ValueError('Shop process/mappings changed')
    finally:
        os.close(fd)
    record['timing'] = {
        'capture_ms': round((time.monotonic() - started) * 1000, 1),
        'bytes_requested': reader.bytes_requested + snapshot.get('bytes_requested', 0),
    }
    return record


def capture_shop(pid, images, capture):
    return _with_reader(pid, images, capture, read_stock)


def capture_sentinel(pid, images, capture):
    return _with_reader(pid, images, capture, probe_stock)


def decode_stock(record):
    snapshot = record['snapshot']
    report = {
        'state': 'complete',
        'finished_at': timestamp(),
        'game': {'identity': snapshot['identity'], 'executable_fingerprint': {'sha256': SUPPORTED_SHA256}},
    }
    observations = []
    issues = list(record['issues'])
    for entry in record['rows']:
        row = entry['row']
        single = dict(snapshot, resources={'complete': True, 'items': [row]})
        try:
            decoded = decode_items(
                single,
                report,
                inventory_page=row['details']['inventory_page'],
                inventory_owner_id=entry['owner_id'],
                inventory_owner_type=1,
            )
            if len(decoded) != 1:
                raise ValueError('Shop item could not be decoded')
            observation: dict[str, Any] = decoded[0]
            if observation['item']['identified'] is not True:
                raise ValueError('Unidentified shop item; gamble stock cannot be checked')
            observation['vendor'] = entry['vendor']
            observations.append(observation)
        except (OSError, ValueError) as exc:
            issues.append(f'{entry["vendor"]} item {row["unit_id"]}: {exc}')
    return observations, issues
