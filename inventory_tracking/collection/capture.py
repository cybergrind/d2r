"""Full-pass read of every item the local character exposes (plan.md Step 2).

Live part: `collect_inventory` samples the unit tables once, then reads item data,
stat arrays, socket children and stash-tab metadata for every candidate item in one
bounded reader pass and rechecks the units afterwards. Pure part: `build_sightings`
turns that record into decoded observations and collection sightings, one
`decode_items` call per item so a single undecodable item never hides the rest.
"""

import os
import struct
import time
from typing import Any

from pydantic import BaseModel, ConfigDict

from inventory_tracking.collection.models import (
    SHARED_OWNER,
    Character,
    ContainerKey,
    ContainerSpace,
    ItemRecord,
    Location,
    Sighting,
)
from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.modifiers import owned_damage_modifiers, owned_defense_modifiers
from inventory_tracking.native.item_diagnostics import capture_stat_candidates
from inventory_tracking.native.layout import HIRELING_CLASS_ID, SUPPORTED_SHA256
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.resource_probe import read_item_arrays, read_location
from inventory_tracking.native.socket_items import read_socket_items
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.native.units import describe_item, unit_matches
from inventory_tracking.tracking.state import select_player


NO_OWNER = 0xFFFFFFFF
STASH_PAGE = 4
CUBE_PAGE = 3
EQUIPMENT_PAGE = 255
PLAYER_PAGES = frozenset((0, CUBE_PAGE, STASH_PAGE))
# d2go orders shared stash owners by this u64 (item.go:26); host run
# 20260925T114444Z reproduced the user's tab numbers from it (research.md R1).
# d2go's Sharedstash state bit (states.go index 186 → word 5, bit 25 at stats-list
# +0xAF0) reads as all zeros on this build, so it is recorded as evidence only and
# shared owners are recognized by `is_shared_candidate`.
STASH_ORDER_OFFSET = 0xD8
STATES_OFFSET = 0xAF0
STATES_WORDS = 6
SHARED_STASH_STATE = 186
INVENTORY_MAGIC = 0x1020304
# Currency-tab stacks: u32 count at item data +0x9C, verified against 43 in-game
# counts (runes, shards, potions, every gem cell) in run 20260925T124336Z (research.md).
STACK_COUNT_OFFSET = 0x9C
CLASS_NAMES = {
    0: 'Amazon',
    1: 'Sorceress',
    2: 'Necromancer',
    3: 'Paladin',
    4: 'Barbarian',
    5: 'Druid',
    6: 'Assassin',
    7: 'Warlock',
}
LEVEL_STAT = 12
LIFE_STATS = frozenset((6, 7))
EQUIPMENT_SLOTS = 13
# Grid index = inventory page + 2 (hover/selection.py); host-verified dimensions.
GRID_CONTAINERS = {2: ('inventory', 10, 4), 5: ('cube', 3, 4), 6: ('stash', 10, 10)}
SHARED_GRID = 6
ITEM_SIZES = ((1, 1), (1, 2), (1, 3), (1, 4), (2, 2), (2, 3), (2, 4))


def shared_stash_state(words: bytes) -> bool:
    if len(words) != STATES_WORDS * 4:
        raise ValueError('State words have an unexpected size')
    index = SHARED_STASH_STATE - 1
    word = struct.unpack_from('<I', words, (index // 32) * 4)[0]
    return bool(word & (1 << (index % 32)))


def read_stash_meta(read, unit) -> dict[str, Any]:
    """Tab ordering key and shared-stash state of one player unit."""
    order = struct.unpack('<Q', read(unit['address'] + STASH_ORDER_OFFSET, 8))[0]
    words = read(unit['stats_pointer'] + STATES_OFFSET, STATES_WORDS * 4) if unit['stats_pointer'] else b''
    if not unit_matches(read, unit):
        raise ValueError('Player unit changed during stash metadata read')
    return {
        'unit_id': unit['unit_id'],
        'name': unit['details'].get('name'),
        'txt_id': unit['txt_id'],
        'order': order,
        'state_bit': shared_stash_state(words) if words else None,
        'states_hex': words.hex(),
    }


def stat_ids(unit) -> set[int]:
    stats = unit.get('details', {}).get('full_stats')
    return {s['id'] for s in stats} if isinstance(stats, list) else set()


def is_shared_candidate(unit, main) -> bool:
    """Shared stash tabs are player units named like the local player with no level or life.

    Party members carry a level and life; the local player is excluded by id. An
    empty tab (no gold, no items) still qualifies so tab numbering stays complete.
    """
    if unit['unit_id'] == main['unit_id'] or unit.get('type') != 0:
        return False
    if unit.get('details', {}).get('name') != main['details'].get('name'):
        return False
    ids = stat_ids(unit)
    return LEVEL_STAT not in ids and not ids & LIFE_STATS


def read_owner_grids(read, unit) -> dict[int, dict[str, Any]]:
    """Every inventory grid of a unit: index → width, height and cell item pointers.

    Same layout the native selection path verifies (hover/selection.py): unit header
    +0x90/+0x98 inventory pointers, inventory magic 0x1020304 and back-reference,
    grid array/count at +0x20, 32-byte grids with size at +0x10 and cells at +0x18.
    """
    header = read(unit['address'], 0xB0)
    if struct.unpack_from('<I', header)[0] != unit['type'] or struct.unpack_from('<I', header, 8)[0] != unit['unit_id']:
        raise ValueError('Owner header mismatch')
    grids: dict[int, dict[str, Any]] = {}
    for offset in (0x90, 0x98):
        address = struct.unpack_from('<Q', header, offset)[0]
        if not address:
            continue
        inventory = read(address, 0x48)
        if struct.unpack_from('<I', inventory)[0] != INVENTORY_MAGIC:
            continue
        if struct.unpack_from('<Q', inventory, 8)[0] != unit['address']:
            raise ValueError('Inventory owner mismatch')
        array, count = struct.unpack_from('<QQ', inventory, 0x20)
        if count > 32:
            raise ValueError('Inventory grid count exceeds bound')
        for index in range(count):
            grid = read(array + index * 32, 32)
            width, height = grid[0x10:0x12]
            cells = struct.unpack_from('<Q', grid, 0x18)[0]
            if not cells:
                continue
            if not 1 <= width <= 16 or not 1 <= height <= 16:
                raise ValueError('Inventory grid dimensions exceed bound')
            pointers = struct.unpack(f'<{width * height}Q', read(cells, width * height * 8))
            grids.setdefault(index, {'width': width, 'height': height, 'cells': list(pointers)})
    return grids


def grid_space(grid: dict[str, Any], container: str, tab: int | None = None) -> dict[str, Any]:
    """Occupancy of one grid: row bitmaps ('.' free, '#' used) and how many items of each size still fit."""
    width, height, cells = grid['width'], grid['height'], grid['cells']
    rows: list[str] = [''.join('#' if cells[y * width + x] else '.' for x in range(width)) for y in range(height)]
    return {
        'container': container,
        'tab': tab,
        'width': width,
        'height': height,
        'free': sum(1 for c in cells if not c),
        'occupied': sum(1 for c in cells if c),
        'rows': rows,
        'fits': fits_counts(rows),
    }


def fits_counts(rows: list[str]) -> dict[str, int]:
    """Greedy row-major packing count per item size; a lower bound on what still fits."""
    result: dict[str, int] = {}
    height = len(rows)
    width = len(rows[0]) if rows else 0
    for w, h in ITEM_SIZES:
        used = [list(r) for r in rows]
        count = 0
        for y in range(height - h + 1):
            for x in range(width - w + 1):
                if all(used[y + dy][x + dx] == '.' for dy in range(h) for dx in range(w)):
                    for dy in range(h):
                        for dx in range(w):
                            used[y + dy][x + dx] = '#'
                    count += 1
        result[f'{w}x{h}'] = count
    return result


def item_sizes(grids: dict[int, dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """Item pointer → (width, height) from the cells that hold it."""
    sizes: dict[int, tuple[int, int]] = {}
    for grid in grids.values():
        width = grid['width']
        cells = grid['cells']
        seen: dict[int, list[tuple[int, int]]] = {}
        for index, pointer in enumerate(cells):
            if pointer:
                seen.setdefault(pointer, []).append((index % width, index // width))
        for pointer, positions in seen.items():
            xs = {x for x, _ in positions}
            ys = {y for _, y in positions}
            sizes[pointer] = (len(xs), len(ys))
    return sizes


def find_mercenary(snapshot, player_id) -> dict[str, Any] | None:
    monsters = snapshot.get('groups', {}).get('monsters', {})
    matches = [
        m
        for m in monsters.get('units', [])
        if m.get('type') == 1
        and m.get('txt_id') == HIRELING_CLASS_ID
        and m.get('identity_stable')
        and len(m['details'].get('monster_data_u32', [])) > 21
        and m['details']['monster_data_u32'][21] == player_id
    ]
    return matches[0] if len(matches) == 1 and monsters.get('complete') else None


def read_stack_count(read, unit) -> int:
    return struct.unpack('<I', read(unit['data_pointer'] + STACK_COUNT_OFFSET, 4))[0]


def read_item_record(read, unit, candidates, *, stack: bool = False) -> dict[str, Any]:
    """Everything `decode_items` needs for one item, read fresh; mirrors Alt+D `verify_item`."""
    item_data = read(unit['data_pointer'], 0x60)
    stack_count = read_stack_count(read, unit) if stack else None
    if unit['stats_pointer']:
        arrays: dict[str, Any] = read_item_arrays(read, unit['stats_pointer'])
        diagnostics = capture_stat_candidates(read, unit['stats_pointer'])
    else:
        arrays = {'complete': True, 'arrays': [{'header_offset': o, 'stats': []} for o in (0x30, 0xA8, 0xE8)]}
        diagnostics = {}
    if not arrays.get('complete'):
        raise ValueError(arrays.get('reason', 'Item stat arrays incomplete'))
    damage = owned_damage_modifiers(diagnostics, unit)
    if damage:
        arrays['damage_modifiers'] = damage
    defense = owned_defense_modifiers(diagnostics, unit)
    if defense:
        arrays['defense_modifiers'] = defense
    arrays['item_data_hex'] = item_data.hex()
    arrays['stat_diagnostics'] = diagnostics
    arrays['socket_items'] = read_socket_items(read, unit, candidates)
    if stack_count is not None:
        arrays['stack_count'] = stack_count
    if not unit_matches(read, unit) or describe_item(read, unit) != unit['details']:
        raise ValueError('Item changed during read')
    return {key: unit[key] for key in ('unit_id', 'txt_id', 'mode', 'details')} | {'resource_stats': arrays}


def candidate_kind(unit, player_id, shared_ids, merc_addresses) -> str | None:
    details = unit.get('details', {})
    if 'quality' not in details:
        return None
    owner, page, mode = details.get('owner_id'), details.get('inventory_page'), unit.get('mode')
    if mode == 0 and owner == player_id and page in PLAYER_PAGES:
        return 'player'
    if mode == 0 and page == STASH_PAGE and owner in shared_ids:
        return 'shared'
    if mode == 0 and page == STASH_PAGE and owner == NO_OWNER:
        # Currency/materials stash: one owner-less unit per held type at (0,0); the
        # stack count is not in the item record or stat list yet (research.md).
        return 'materials'
    if mode == 1 and page == EQUIPMENT_PAGE and owner == player_id:
        return 'player'
    if mode == 1 and page == EQUIPMENT_PAGE and owner == NO_OWNER and unit['address'] in merc_addresses:
        return 'mercenary'
    return None


def collect_inventory(pid, images, capture) -> dict[str, Any]:
    """One bounded pass over every owned item; raises when the snapshot cannot be trusted."""
    started = time.monotonic()
    snapshot = sample_units(pid, images, capture, merc=True)
    if snapshot.get('status') != 'research' or not snapshot.get('mappings_stable'):
        raise ValueError(snapshot.get('error', 'Unit snapshot unavailable'))
    groups = snapshot['groups']
    if not all(groups[name]['complete'] for name in ('players', 'items', 'monsters')):
        raise ValueError('Incomplete unit traversal')
    player_id, _ = select_player(groups['players']['units'])
    players = [u for u in groups['players']['units'] if u['type'] == 0 and u.get('identity_stable')]
    main = next(u for u in players if u['unit_id'] == player_id)
    items = groups['items']['units']
    issues: list[str] = []
    mappings = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, mappings)
        read = reader.read
        stash_units = []
        for unit in players:
            try:
                meta = read_stash_meta(read, unit)
            except (OSError, ValueError, struct.error) as exc:
                issues.append(f'Player unit {unit["unit_id"]}: {exc}')
                continue
            meta['shared_state'] = is_shared_candidate(unit, main)
            stash_units.append(meta)
        shared_ids = {u['unit_id'] for u in stash_units if u['shared_state'] and u['unit_id'] != player_id}
        mercenary: dict[str, Any] | None = None
        merc_addresses: set[int] = set()
        merc = find_mercenary(snapshot, player_id)
        if merc is not None:
            try:
                grids = read_owner_grids(read, merc)
                equipment = grids.get(0)
                if equipment is None or (equipment['width'], equipment['height']) != (EQUIPMENT_SLOTS, 1):
                    raise ValueError('Mercenary equipment grid unavailable')
                merc_addresses = {p for p in equipment['cells'] if p}
                mercenary = {'unit_id': merc['unit_id'], 'item_addresses': sorted(merc_addresses)}
            except (OSError, ValueError, struct.error) as exc:
                issues.append(f'Mercenary: {exc}')
        spaces: list[dict[str, Any]] = []
        sizes: dict[int, tuple[int, int]] = {}
        grid_owners = [(main, None)] + [(u, u['unit_id']) for u in players if u['unit_id'] in shared_ids]
        for unit, shared_id in grid_owners:
            try:
                grids = read_owner_grids(read, unit)
            except (OSError, ValueError, struct.error) as exc:
                issues.append(f'Grids of unit {unit["unit_id"]}: {exc}')
                continue
            sizes.update(item_sizes(grids))
            wanted = {SHARED_GRID: ('shared_stash', 10, 10)} if shared_id is not None else GRID_CONTAINERS
            for index, (container, width, height) in wanted.items():
                grid = grids.get(index)
                if grid is None:
                    continue
                if (grid['width'], grid['height']) != (width, height):
                    issues.append(f'{container} grid of unit {unit["unit_id"]} is {grid["width"]}x{grid["height"]}')
                    continue
                spaces.append(grid_space(grid, container) | {'owner_unit_id': shared_id})
        try:
            location: int | None = read_location(read, main['path_pointer'])
        except (OSError, ValueError, struct.error) as exc:
            location = None
            issues.append(f'Location: {exc}')
        rows = []
        kinds: dict[str, str] = {}  # keyed by str(unit_id) so capture.json round-trips
        for unit in items:
            kind = candidate_kind(unit, player_id, shared_ids, merc_addresses)
            if kind is None:
                continue
            try:
                row = read_item_record(read, unit, items, stack=kind == 'materials')
                if unit['address'] in sizes:
                    row['resource_stats']['size'] = list(sizes[unit['address']])
                rows.append(row)
                kinds[str(unit['unit_id'])] = kind
            except (OSError, ValueError, struct.error) as exc:
                issues.append(f'Item {unit["unit_id"]} ({kind}): {exc}')
        changed = [
            u['unit_id']
            for u in items
            if str(u['unit_id']) in kinds and (not unit_matches(read, u) or describe_item(read, u) != u['details'])
        ]
        if changed:
            raise ValueError(f'{len(changed)} items changed during the pass')
        if identity(pid) != images['identity']:
            raise ValueError('Game process changed during the pass')
        bytes_requested = reader.bytes_requested
    finally:
        os.close(fd)
    snapshot['resources'] = {'complete': True, 'items': rows, 'kinds': kinds}
    return {
        'snapshot': snapshot,
        'player_id': player_id,
        'stash_units': stash_units,
        'shared_ids': sorted(shared_ids),
        'mercenary': mercenary,
        'spaces': spaces,
        'location': location,
        'issues': issues,
        'timing': {'ms': round((time.monotonic() - started) * 1000, 1), 'bytes_requested': bytes_requested},
    }


class CollectionBuild(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    character: Character
    sightings: list[Sighting]
    containers: list[ContainerKey]
    tabs: dict[int, int]  # shared owner unit id → tab number
    spaces: list[ContainerSpace] = []
    issues: list[str]


def character_from(unit) -> Character:
    stats = unit['details'].get('full_stats')
    level = None
    if isinstance(stats, list):
        level = next((s['raw'] for s in stats if s.get('id') == LEVEL_STAT and s.get('layer') == 0), None)
    return Character(
        name=unit['details']['name'],
        class_id=unit['txt_id'],
        class_name=CLASS_NAMES.get(unit['txt_id']),
        level=level,
    )


def shared_tabs(record) -> dict[int, int]:
    shared = [u for u in record['stash_units'] if u['shared_state'] and u['unit_id'] != record['player_id']]
    return {u['unit_id']: index + 1 for index, u in enumerate(sorted(shared, key=lambda u: u['order']))}


def build_sightings(record, *, run_id=None, captured_at=None) -> CollectionBuild:
    snapshot = record['snapshot']
    player_id = record['player_id']
    main = next(u for u in snapshot['groups']['players']['units'] if u['unit_id'] == player_id)
    character = character_from(main)
    tabs = shared_tabs(record)
    merc = record.get('mercenary') or {}
    report = {
        'state': 'complete',
        'run_id': run_id,
        'finished_at': captured_at,
        'game': {'identity': snapshot['identity'], 'executable_fingerprint': {'sha256': SUPPORTED_SHA256}},
    }
    containers: list[ContainerKey] = [(character.name, c, None) for c in ('inventory', 'cube', 'equipped', 'stash')]
    containers += [(SHARED_OWNER, 'shared_stash', tab) for tab in sorted(tabs.values())]
    containers.append((SHARED_OWNER, 'materials', None))
    if merc:
        containers.append((character.name, 'mercenary', None))
    sightings: list[Sighting] = []
    issues = list(record.get('issues', []))
    spaces: list[ContainerSpace] = []
    for space in record.get('spaces', []):
        shared_id = space.get('owner_unit_id')
        tab = tabs.get(shared_id) if shared_id is not None else None
        if shared_id is not None and tab is None:
            continue
        spaces.append(
            ContainerSpace(
                owner=SHARED_OWNER if shared_id is not None else character.name,
                container=space['container'],
                tab=tab,
                width=space['width'],
                height=space['height'],
                free=space['free'],
                occupied=space['occupied'],
                rows=space['rows'],
                fits=space['fits'],
            )
        )
    kinds = snapshot['resources'].get('kinds', {})
    for row in snapshot['resources']['items']:
        kind = kinds.get(str(row['unit_id']))
        details = row['details']
        owner, page = details['owner_id'], details['inventory_page']
        options: dict[str, Any] = {'inventory_page': page}
        tab = None
        if kind == 'shared':
            tab = tabs.get(owner)
            if tab is None:
                issues.append(f'Item {row["unit_id"]}: shared owner {owner} has no tab order')
                continue
            options.update(inventory_owner_id=owner, inventory_owner_type=0)
        elif kind == 'materials':
            options['materials'] = True
        elif kind == 'mercenary':
            options.update(inventory_owner_id=merc['unit_id'], inventory_owner_type=1)
        elif kind != 'player':
            issues.append(f'Item {row["unit_id"]}: unknown candidate kind {kind!r}')
            continue
        single = dict(snapshot, resources={'complete': True, 'items': [row]})
        try:
            [observation] = decode_items(single, report, **options)
            quantity = row['resource_stats'].get('stack_count')
            if quantity is not None:
                observation['item']['quantity'] = quantity
                observation['decoded_stats'].append(
                    {'status': 'decoded', 'name': 'stack', 'text': f'Quantity: {quantity}'}
                )
            item = ItemRecord.from_observation(observation)
            location = Location.from_source(observation['source'], character.name, tab=tab)
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(f'Item {row["unit_id"]} ({kind}, page {page}): {exc}')
            continue
        sightings.append(Sighting(item=item, location=location))
    return CollectionBuild(
        character=character, sightings=sightings, containers=containers, tabs=tabs, spaces=spaces, issues=issues
    )
