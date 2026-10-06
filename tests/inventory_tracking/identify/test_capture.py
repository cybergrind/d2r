"""Pure parts of the identify probe: candidate selection, flag decoding, decoding of records."""

import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.identify import capture
from inventory_tracking.identify.capture import decode_records, identified_flag, inventory_candidates, probe_inventory
from inventory_tracking.items.identity import FLAGS_OFFSET, IDENTIFIED_FLAG, ITEM_DATA_SIZE


FIXTURES = Path(__file__).parents[1] / 'fixtures'
PLAYER = 104997884


def unit(unit_id, *, quality=4, page=0, mode=0, owner=PLAYER, data_pointer=0x1000):
    return {
        'unit_id': unit_id,
        'txt_id': 351,
        'mode': mode,
        'data_pointer': data_pointer,
        'details': {'quality': quality, 'owner_id': owner, 'inventory_page': page, 'x': 0, 'y': 0},
    }


def item_data(quality, identified):
    raw = bytearray(ITEM_DATA_SIZE)
    struct.pack_into('<I', raw, 0, quality)
    struct.pack_into('<I', raw, FLAGS_OFFSET, IDENTIFIED_FLAG if identified else 0)
    return bytes(raw)


def test_candidates_are_magic_or_better_main_inventory_items_of_the_player():
    snapshot = {
        'groups': {
            'items': {
                'units': [
                    unit(1),
                    unit(2, quality=7),
                    unit(3, quality=2),  # normal: never unidentified
                    unit(4, page=3),  # cube: Cain identifies it too
                    unit(5, mode=1),  # equipped
                    unit(6, owner=999),  # vendor / other owner
                    unit(7, page=4),  # stash
                ]
            }
        }
    }
    assert [u['unit_id'] for u in inventory_candidates(snapshot, PLAYER)] == [1, 2, 4]


def test_identified_flag_requires_the_quality_it_was_selected_by():
    assert identified_flag(item_data(4, True), 4)
    assert not identified_flag(item_data(4, False), 4)
    with pytest.raises(ValueError, match='changed'):
        identified_flag(item_data(5, True), 4)
    with pytest.raises(ValueError, match='changed'):
        identified_flag(item_data(4, True)[:-1], 4)


def test_probe_reports_identified_state_in_town_and_away_elsewhere(monkeypatch):
    units = [
        unit(1, data_pointer=0x1000),
        unit(2, quality=7, page=3, data_pointer=0x2000),
        unit(3, page=4),  # stash
        unit(4, mode=1),  # equipped
        unit(5, owner=999),  # vendor stock
    ]
    snapshot = {
        'status': 'research',
        'mappings_stable': True,
        'groups': {
            'players': {'complete': True, 'units': [{'unit_id': PLAYER, 'path_pointer': 0x50}]},
            'items': {'complete': True, 'units': units},
        },
    }
    memory = {0x1000: item_data(4, False), 0x2000: item_data(7, True)}
    location = {'value': 1}
    monkeypatch.setattr(capture, 'select_player', lambda players: (PLAYER, None))
    monkeypatch.setattr(capture, 'read_location', lambda read, pointer: location['value'])
    monkeypatch.setattr(capture, 'unit_matches', lambda read, u: True)
    monkeypatch.setattr(capture, 'describe_item', lambda read, u: u['details'])
    probe = probe_inventory(lambda address, size: memory[address][:size], snapshot)
    assert probe['state'] == 'ok'
    assert probe['items'] == {
        '1': {'identified': False, 'quality': 4, 'txt_id': 351, 'page': 0},
        '2': {'identified': True, 'quality': 7, 'txt_id': 351, 'page': 3},
    }
    # Everything the player holds anywhere: a gambled item is new to all of it, a stash item is not.
    assert probe['owned'] == ['1', '2', '3', '4']
    location['value'] = 46
    assert probe_inventory(lambda address, size: memory[address][:size], snapshot) == {
        'state': 'away',
        'location': 46,
        'player_id': PLAYER,
        'items': {},
    }
    snapshot['groups']['items']['complete'] = False
    with pytest.raises(ValueError, match='Incomplete'):
        probe_inventory(lambda address, size: memory[address][:size], snapshot)


def test_decode_records_yields_observations_and_keeps_read_issues():
    fixture = json.loads((FIXTURES / 'appraisal_ring.json').read_text())
    snapshot = fixture['snapshot']
    record = {'snapshot': snapshot, 'rows': snapshot['resources']['items'], 'issues': ['Item 9: gone']}
    observations, issues = decode_records(record)
    [observation] = observations
    assert observation['item']['name'] == 'Ring'
    assert observation['source']['position'] == [3, 0]
    assert issues == ['Item 9: gone']
