"""Pure planning/decoding parts of the full-pass capture; the live pass is host-gated."""

import copy
import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.collection.capture import (
    NO_OWNER,
    STACK_COUNT_OFFSET,
    STASH_ORDER_OFFSET,
    STATES_OFFSET,
    build_sightings,
    candidate_kind,
    character_from,
    find_mercenary,
    is_shared_candidate,
    read_item_record,
    read_owner_grids,
    read_stash_meta,
    shared_stash_state,
    shared_tabs,
)
from inventory_tracking.native.layout import HIRELING_CLASS_ID


FIXTURES = Path(__file__).parents[1] / 'fixtures'
MAIN = 125837056
TAB_A = 62918528  # order 200 → tab 2
TAB_B = 31459264  # order 100 → tab 1
MERC = 424242


def words_with(state_index):
    words = bytearray(24)
    index = state_index - 1
    struct.pack_into('<I', words, (index // 32) * 4, 1 << (index % 32))
    return bytes(words)


def test_shared_stash_state_is_word_5_bit_25():
    assert shared_stash_state(words_with(186))
    assert not shared_stash_state(words_with(185))
    assert not shared_stash_state(bytes(24))
    with pytest.raises(ValueError, match='unexpected size'):
        shared_stash_state(bytes(20))


class Memory:
    """Byte-addressed fake process memory for the reader-facing helpers."""

    def __init__(self):
        self.blocks: dict[int, bytes] = {}

    def put(self, address, data):
        self.blocks[address] = bytes(data)

    def read(self, address, size):
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return data[address - start : address - start + size]
        raise ValueError(f'unmapped read {address:#x}+{size}')


def unit_bytes(unit):
    raw = bytearray(0x160)
    struct.pack_into('<IIII', raw, 0, unit['type'], unit['txt_id'], unit['unit_id'], unit['mode'])
    struct.pack_into('<Q', raw, 0x10, unit['data_pointer'])
    struct.pack_into('<Q', raw, 0x38, unit['path_pointer'])
    struct.pack_into('<Q', raw, 0x88, unit['stats_pointer'])
    struct.pack_into('<Q', raw, 0x90, unit['inventory_pointer'])
    struct.pack_into('<Q', raw, 0x158, unit['next_pointer'])
    return raw


def player_unit(unit_id, *, address=0x1000, stats=0x5000, inventory=0x7000):
    return {
        'address': address,
        'type': 0,
        'txt_id': 7,
        'unit_id': unit_id,
        'mode': 0,
        'data_pointer': 0x3000,
        'path_pointer': 0,
        'stats_pointer': stats,
        'inventory_pointer': inventory,
        'next_pointer': 0,
        'details': {'name': 'Mule'},
        'identity_stable': True,
    }


def test_read_stash_meta_reads_order_and_state():
    unit = player_unit(TAB_A)
    raw = unit_bytes(unit)
    struct.pack_into('<Q', raw, STASH_ORDER_OFFSET, 200)
    memory = Memory()
    memory.put(unit['address'], raw)
    memory.put(unit['stats_pointer'] + STATES_OFFSET, words_with(186))
    meta = read_stash_meta(memory.read, unit)
    assert (meta['unit_id'], meta['order'], meta['state_bit'], meta['name']) == (TAB_A, 200, True, 'Mule')


def test_shared_candidates_are_same_name_units_without_level_or_life():
    main = {'unit_id': MAIN, 'type': 0, 'details': {'name': 'Mule', 'full_stats': [{'id': 12, 'raw': 91}]}}
    tab = {'unit_id': TAB_A, 'type': 0, 'details': {'name': 'Mule', 'full_stats': [{'id': 15, 'raw': 1}]}}
    empty_tab = {'unit_id': TAB_B, 'type': 0, 'details': {'name': 'Mule', 'full_stats': []}}
    party = {'unit_id': 777, 'type': 0, 'details': {'name': 'Caras', 'full_stats': [{'id': 12, 'raw': 95}]}}
    twin = {'unit_id': 778, 'type': 0, 'details': {'name': 'Mule', 'full_stats': [{'id': 6, 'raw': 1}]}}
    assert is_shared_candidate(tab, main)
    assert is_shared_candidate(empty_tab, main)
    assert not is_shared_candidate(main, main)
    assert not is_shared_candidate(party, main)
    assert not is_shared_candidate(twin, main)


def test_read_item_record_reads_the_stack_count_only_for_currency_units(monkeypatch):
    unit = {
        'address': 0x1000,
        'type': 4,
        'txt_id': 644,
        'unit_id': 9,
        'mode': 0,
        'data_pointer': 0x3000,
        'path_pointer': 0,
        'stats_pointer': 0,
        'inventory_pointer': 0,
        'next_pointer': 0,
        'details': {'quality': 2, 'owner_id': NO_OWNER, 'inventory_page': 4, 'body_location': 0},
    }
    memory = Memory()
    memory.put(unit['address'], unit_bytes(unit))
    data = bytearray(0x100)
    struct.pack_into('<I', data, 0, 2)
    struct.pack_into('<I', data, 0x0C, NO_OWNER)
    data[0x55] = 4
    struct.pack_into('<I', data, STACK_COUNT_OFFSET, 43)
    memory.put(unit['data_pointer'], data)
    monkeypatch.setattr(
        'inventory_tracking.collection.capture.read_socket_items', lambda read, u, c: {'complete': True, 'children': []}
    )
    row = read_item_record(memory.read, unit, [], stack=True)
    assert row['resource_stats']['stack_count'] == 43
    assert len(row['resource_stats']['item_data_hex']) == 0xC0
    assert 'stack_count' not in read_item_record(memory.read, unit, [])['resource_stats']


def test_read_stash_meta_rejects_a_changed_unit():
    unit = player_unit(TAB_A)
    raw = unit_bytes(unit)
    struct.pack_into('<I', raw, 8, TAB_A + 1)
    memory = Memory()
    memory.put(unit['address'], raw)
    memory.put(unit['stats_pointer'] + STATES_OFFSET, bytes(24))
    with pytest.raises(ValueError, match='changed'):
        read_stash_meta(memory.read, unit)


def test_read_owner_grids_walks_equipment_cells():
    unit = player_unit(MERC, address=0x9000, inventory=0xA000)
    unit.update(type=1, txt_id=HIRELING_CLASS_ID)
    memory = Memory()
    header = bytearray(0xB0)
    struct.pack_into('<I', header, 0, 1)
    struct.pack_into('<I', header, 8, MERC)
    struct.pack_into('<Q', header, 0x90, 0xA000)
    memory.put(0x9000, header)
    inventory = bytearray(0x48)
    struct.pack_into('<I', inventory, 0, 0x1020304)
    struct.pack_into('<Q', inventory, 8, 0x9000)
    struct.pack_into('<QQ', inventory, 0x20, 0xB000, 1)
    memory.put(0xA000, inventory)
    grid = bytearray(32)
    grid[0x10], grid[0x11] = 13, 1
    struct.pack_into('<Q', grid, 0x18, 0xC000)
    memory.put(0xB000, grid)
    cells = [0] * 13
    cells[3], cells[4] = 0xD100, 0xD200
    memory.put(0xC000, struct.pack('<13Q', *cells))
    grids = read_owner_grids(memory.read, unit)
    assert grids[0]['width'] == 13
    assert grids[0]['cells'][3:5] == [0xD100, 0xD200]


def test_read_owner_grids_rejects_foreign_inventory():
    unit = player_unit(MERC, address=0x9000, inventory=0xA000)
    memory = Memory()
    header = bytearray(0xB0)
    struct.pack_into('<I', header, 0, 0)
    struct.pack_into('<I', header, 8, MERC)
    struct.pack_into('<Q', header, 0x90, 0xA000)
    memory.put(0x9000, header)
    inventory = bytearray(0x48)
    struct.pack_into('<I', inventory, 0, 0x1020304)
    struct.pack_into('<Q', inventory, 8, 0x9999)
    memory.put(0xA000, inventory)
    with pytest.raises(ValueError, match='Inventory owner mismatch'):
        read_owner_grids(memory.read, unit)


@pytest.mark.parametrize(
    ('mode', 'page', 'owner', 'address', 'expected'),
    [
        (0, 0, MAIN, 1, 'player'),
        (0, 3, MAIN, 1, 'player'),
        (0, 4, MAIN, 1, 'player'),
        (1, 255, MAIN, 1, 'player'),
        (0, 4, TAB_A, 1, 'shared'),
        (0, 4, NO_OWNER, 1, 'materials'),
        (1, 255, NO_OWNER, 0xD100, 'mercenary'),
        (1, 255, NO_OWNER, 0xD999, None),  # not in the merc's equipment grid
        (2, 0, MAIN, 1, None),  # belt
        (6, 0, MAIN, 1, None),  # socket child
        (0, 0, NO_OWNER, 1, None),  # vendor page
        (0, 0, 777, 1, None),  # party member
    ],
)
def test_candidate_kind(mode, page, owner, address, expected):
    unit = {'address': address, 'mode': mode, 'details': {'quality': 2, 'owner_id': owner, 'inventory_page': page}}
    assert candidate_kind(unit, MAIN, {TAB_A, TAB_B}, {0xD100}) == expected


def test_find_mercenary_requires_the_local_players_hireling():
    def hireling(unit_id, owner, **extra):
        return {
            'type': 1,
            'txt_id': HIRELING_CLASS_ID,
            'unit_id': unit_id,
            'identity_stable': True,
            'details': {'monster_data_u32': [0] * 21 + [owner]},
            **extra,
        }

    snapshot = {'groups': {'monsters': {'complete': True, 'units': [hireling(1, 999), hireling(MERC, MAIN)]}}}
    merc = find_mercenary(snapshot, MAIN)
    assert merc is not None
    assert merc['unit_id'] == MERC
    snapshot['groups']['monsters']['complete'] = False
    assert find_mercenary(snapshot, MAIN) is None


def test_shared_tabs_follow_the_order_field_not_unit_ids():
    record = {
        'player_id': MAIN,
        'stash_units': [
            {'unit_id': MAIN, 'order': 0, 'shared_state': False},
            {'unit_id': TAB_A, 'order': 200, 'shared_state': True},
            {'unit_id': TAB_B, 'order': 100, 'shared_state': True},
            {'unit_id': 5, 'order': 50, 'shared_state': False},
        ],
    }
    assert shared_tabs(record) == {TAB_B: 1, TAB_A: 2}


@pytest.fixture
def insight_capture():
    return json.loads((FIXTURES / 'insight_bill.json').read_text())


def test_character_from_player_unit(insight_capture):
    main = next(u for u in insight_capture['snapshot']['groups']['players']['units'] if u['unit_id'] == MAIN)
    character = character_from(main)
    assert (character.name, character.class_id, character.class_name, character.level) == (
        'CybergrindAA',
        7,
        'Warlock',
        91,
    )


def record_from(insight_capture, *, merc=False):
    """A full-pass record: the Insight row placed in every container kind, plus an unknown base."""
    snapshot = copy.deepcopy(insight_capture['snapshot'])
    template = snapshot['resources']['items'][0]
    rows = []
    kinds = {}

    def add(unit_id, kind, **details):
        row = copy.deepcopy(template)
        row['unit_id'] = unit_id
        row['details'] = {**row['details'], **details}
        rows.append(row)
        kinds[str(unit_id)] = kind
        # decode_items looks the row up among the unit group by owner/page too.
        unit = next(u for u in snapshot['groups']['items']['units'] if u['unit_id'] == template['unit_id'])
        twin = copy.deepcopy(unit)
        twin.update(unit_id=unit_id, details=row['details'], mode=row['mode'])
        snapshot['groups']['items']['units'].append(twin)
        return row

    add(1001, 'player', owner_id=MAIN, inventory_page=4, x=0, y=6)
    add(1002, 'player', owner_id=MAIN, inventory_page=0, x=3, y=1)
    add(1003, 'shared', owner_id=TAB_A, inventory_page=4, x=2, y=2)
    add(1004, 'shared', owner_id=TAB_B, inventory_page=4, x=5, y=5)
    stack = add(1005, 'materials', owner_id=NO_OWNER, inventory_page=4, x=0, y=0)
    stack['resource_stats'] = dict(stack['resource_stats'], stack_count=43)
    broken = add(1006, 'player', owner_id=MAIN, inventory_page=3, x=0, y=0)
    broken['txt_id'] = 999999
    if merc:
        merc_row = add(1007, 'mercenary', owner_id=NO_OWNER, inventory_page=255, body_location=4, x=4, y=0)
        merc_row['mode'] = 1
        for unit in snapshot['groups']['items']['units']:
            if unit['unit_id'] == 1007:
                unit['mode'] = 1
        snapshot['groups']['monsters']['units'].append(
            {
                'address': 0x9000,
                'type': 1,
                'txt_id': HIRELING_CLASS_ID,
                'unit_id': MERC,
                'mode': 1,
                'identity_stable': True,
                'details': {'monster_data_u32': [0] * 21 + [MAIN]},
            }
        )
    snapshot['resources'] = {'complete': True, 'items': rows, 'kinds': kinds}
    return {
        'snapshot': snapshot,
        'player_id': MAIN,
        'stash_units': [
            {'unit_id': MAIN, 'order': 0, 'shared_state': False},
            {'unit_id': TAB_A, 'order': 200, 'shared_state': True},
            {'unit_id': TAB_B, 'order': 100, 'shared_state': True},
        ],
        'mercenary': {'unit_id': MERC, 'item_addresses': []} if merc else None,
        'spaces': [
            {
                'container': 'inventory',
                'tab': None,
                'width': 10,
                'height': 4,
                'free': 39,
                'occupied': 1,
                'rows': ['#' + '.' * 9] + ['.' * 10] * 3,
                'fits': {'2x4': 4},
                'owner_unit_id': None,
            },
            {
                'container': 'shared_stash',
                'tab': None,
                'width': 10,
                'height': 10,
                'free': 100,
                'occupied': 0,
                'rows': ['.' * 10] * 10,
                'fits': {'2x4': 10},
                'owner_unit_id': TAB_A,
            },
            {
                'container': 'shared_stash',
                'tab': None,
                'width': 10,
                'height': 10,
                'free': 0,
                'occupied': 100,
                'rows': ['#' * 10] * 10,
                'fits': {},
                'owner_unit_id': 424,
            },
        ],
        'location': 1,
        'issues': [],
        'timing': {'ms': 1.0, 'bytes_requested': 10},
    }


def test_build_sightings_places_every_container_and_isolates_failures(insight_capture):
    build = build_sightings(record_from(insight_capture), run_id='r1', captured_at='2026-09-25T12:00:00+00:00')
    assert build.character.name == 'CybergrindAA'
    assert build.tabs == {TAB_B: 1, TAB_A: 2}
    assert build.containers == [
        ('CybergrindAA', 'inventory', None),
        ('CybergrindAA', 'cube', None),
        ('CybergrindAA', 'equipped', None),
        ('CybergrindAA', 'stash', None),
        ('shared', 'shared_stash', 1),
        ('shared', 'shared_stash', 2),
        ('shared', 'materials', None),
    ]
    labels = sorted(s.location.label for s in build.sightings)
    assert labels == [
        'CybergrindAA · inventory (3,1)',
        'CybergrindAA · stash (0,6)',
        'shared · materials (0,0)',
        'shared · shared stash 1 (5,5)',
        'shared · shared stash 2 (2,2)',
    ]
    assert all(s.item.name == 'Insight' for s in build.sightings)
    [stack] = [s for s in build.sightings if s.location.container == 'materials']
    assert stack.item.quantity == 43
    assert 'Quantity: 43' in stack.item.stat_lines
    assert stack.item.fingerprint == next(
        s.item.fingerprint for s in build.sightings if s.location.container == 'stash'
    )
    assert len(build.issues) == 1
    assert '1006' in build.issues[0]
    assert 'Unknown item class' in build.issues[0]


def test_build_sightings_includes_the_mercenary_when_its_grid_was_read(insight_capture):
    build = build_sightings(record_from(insight_capture, merc=True), run_id='r1', captured_at='t')
    assert ('CybergrindAA', 'mercenary', None) in build.containers
    merc_items = [s for s in build.sightings if s.location.container == 'mercenary']
    assert [(s.location.x, s.location.y) for s in merc_items] == [(4, 0)]
    assert build.issues
    assert all('1006' in issue for issue in build.issues)
