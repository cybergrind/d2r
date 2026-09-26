import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.shop.capture import stock_members
from inventory_tracking.shop.service import assess, result_lines


FIXTURE = Path(__file__).with_name('drognan_stock.json')


def record():
    return json.loads(FIXTURE.read_text())


def owners(data):
    return [dict(o, grids={int(k): v for k, v in o['grids'].items()}) for o in data['owners']]


def test_captured_drognan_stock_decodes_all_four_tabs_without_ui():
    data = record()
    selected = stock_members(data['snapshot'], owners(data))
    assert {u['details']['inventory_page'] for _, u in selected} == {0, 1, 2, 3}
    result = assess(data)
    assert result['count'] == data['stock_count']
    assert result['vendors'] == ['Drognan']
    assert not result['issues']


def test_captured_fara_throwing_spear_stack_bonus_is_not_an_unknown_flag():
    data = record()
    data['rows'] = [json.loads(Path(__file__).with_name('fara_throwing_spear.json').read_text())]
    data['snapshot']['groups']['monsters']['units'] = [data['rows'][0]['owner_unit']]
    data['stock_count'] = 1
    result = assess(data)
    assert result['state'] == 'complete'
    assert result['count'] == 1
    assert result['vendors'] == ['Fara']
    assert not result['issues']


@pytest.mark.parametrize('change', ['owner', 'page', 'missing', 'unstable', 'duplicate'])
def test_shop_grid_ownership_is_required(change):
    data = record()
    grids = owners(data)
    unit = data['snapshot']['groups']['items']['units'][0]
    if change == 'owner':
        unit['details']['owner_id'] = 1
    elif change == 'page':
        unit['details']['inventory_page'] = 4
    elif change == 'missing':
        data['snapshot']['groups']['items']['units'].clear()
    elif change == 'unstable':
        unit['identity_stable'] = False
    else:
        grids.append(copy.deepcopy(grids[0]))
    with pytest.raises(ValueError, match=r'[Ss]hop'):
        stock_members(data['snapshot'], grids)


def test_unloaded_stock_and_incomplete_reads_never_claim_no_targets():
    result = assess(record())
    result.update(stock_count=0, count=0, hits=[], issues=[])
    assert 'not loaded' in result_lines(result)[0].text
    result.update(stock_count=4, count=3, issues=['unreadable item'])
    assert 'incomplete' in result_lines(result)[0].text
    assert not any('No shopping targets' in line.text for line in result_lines(result))


@pytest.mark.parametrize('mutation', ['none', 'grid', 'item', 'town', 'store_flag', 'invalid_flags', 'incomplete'])
def test_scan_rechecks_stock_and_never_treats_partial_reads_as_empty(monkeypatch, mutation):
    from inventory_tracking.shop import capture

    data = record()
    grid_owners = owners(data)
    owner = grid_owners[0]
    by_id = {entry['row']['unit_id']: entry['row'] for entry in data['rows']}
    calls = {'grids': 0, 'location': 0}

    def grids(read, unit):
        calls['grids'] += 1
        value = copy.deepcopy(owner['grids'])
        if mutation == 'grid' and calls['grids'] > 1:
            value[2]['cells'] = [0] * 100
        return value

    def location(*args):
        calls['location'] += 1
        return 1 if mutation == 'town' and calls['location'] > 1 else 40

    def row(read, unit, items):
        value = copy.deepcopy(by_id[unit['unit_id']])
        if mutation == 'store_flag':
            raw = bytearray.fromhex(value['resource_stats']['item_data_hex'])
            raw[0x18:0x1C] = (16).to_bytes(4, 'little')
            value['resource_stats']['item_data_hex'] = raw.hex()
        if mutation == 'invalid_flags':
            value['resource_stats']['item_data_hex'] = ''
        return value

    monkeypatch.setattr(capture, 'read_owner_grids', grids)
    monkeypatch.setattr(capture, 'read_location', location)
    monkeypatch.setattr(capture, 'read_item_record', row)
    monkeypatch.setattr(capture, 'unit_matches', lambda read, u: mutation != 'item' or u['type'] != 4)
    monkeypatch.setattr(capture, 'describe_item', lambda read, u: u['details'])
    if mutation == 'incomplete':
        data['snapshot']['groups']['items']['complete'] = False
    if mutation in ('grid', 'item', 'town', 'incomplete'):
        with pytest.raises(ValueError, match=r'changed|left|unstable'):
            capture.read_stock(None, data['snapshot'])
    else:
        result = capture.read_stock(None, data['snapshot'])
        assert result['stock_count'] == 4
        assert len(result['issues']) == (4 if mutation == 'invalid_flags' else 0)
        assert len(result['rows']) == (0 if mutation == 'invalid_flags' else 4)

        if mutation == 'invalid_flags':
            assert len(result['rejected_rows']) == 4
            assert result['rejected_rows'][0]['row']['resource_stats']['item_data_hex'] == ''
        elif mutation == 'store_flag':
            # Stable NPC grid membership remains authoritative for buyback stock.
            result['timing'] = {}
            assert assess(result)['state'] == 'complete'
            assert assess(result)['count'] == 4


# --- automatic watcher: stock order, gear sentinel and the cheap probe ---------------------------


def test_stock_order_is_vendor_tab_cell_and_first_gear_skips_consumables():
    from inventory_tracking.shop.capture import gear_sentinel

    data = record()
    selected = stock_members(data['snapshot'], owners(data))
    assert [u['details']['inventory_page'] for _, u in selected] == [0, 1, 2, 3]
    owner, unit = gear_sentinel(selected)
    assert (owner['name'], unit['txt_id']) == ('Drognan', 351)  # Spiked Shield, tab 1

    # A potion first in stock order is skipped; a stock of consumables only has no sentinel.
    potion = next(u for _, u in selected if u['txt_id'] == 611)
    assert gear_sentinel([(owner, potion), (owner, unit)])[1] is unit
    assert gear_sentinel([(owner, potion)]) is None


def test_sentinel_key_ignores_unit_identity_but_tracks_content_and_cell():
    from inventory_tracking.shop.capture import gear_sentinel, sentinel_key

    data = record()
    selected = stock_members(data['snapshot'], owners(data))
    owner, unit = gear_sentinel(selected)
    row = next(e['row'] for e in data['rows'] if e['row']['unit_id'] == unit['unit_id'])
    key = sentinel_key(owner, unit, row)
    assert key['vendor'] == 'Drognan'
    assert key['identified'] is True
    assert key['stats']

    reopened = copy.deepcopy(unit)
    reopened.update(unit_id=unit['unit_id'] + 1, address=unit['address'] + 0x1000, data_pointer=1)
    assert sentinel_key(owner, reopened, row) == key  # closing/reopening Trade keeps the key

    moved = copy.deepcopy(unit)
    moved['details']['x'] += 1
    assert sentinel_key(owner, moved, row) != key
    rerolled = copy.deepcopy(row)
    rerolled['resource_stats']['arrays'][0]['stats'][0]['raw'] += 1
    assert sentinel_key(owner, unit, rerolled) != key


def test_read_stock_records_the_sentinel(monkeypatch):
    from inventory_tracking.shop import capture

    data = record()
    grid_owners = owners(data)
    by_id = {entry['row']['unit_id']: entry['row'] for entry in data['rows']}
    monkeypatch.setattr(capture, 'read_owner_grids', lambda read, unit: copy.deepcopy(grid_owners[0]['grids']))
    monkeypatch.setattr(capture, 'read_location', lambda *args: 40)
    monkeypatch.setattr(capture, 'read_item_record', lambda read, unit, items: copy.deepcopy(by_id[unit['unit_id']]))
    monkeypatch.setattr(capture, 'unit_matches', lambda read, u: True)
    monkeypatch.setattr(capture, 'describe_item', lambda read, u: u['details'])
    result = capture.read_stock(None, data['snapshot'])
    assert result['sentinel']['txt_id'] == 351
    assert assess(result | {'timing': {}})['sentinel'] == result['sentinel']


@pytest.mark.parametrize('scenario', ['loaded', 'unloaded', 'no_gear', 'gamble', 'away', 'changed'])
def test_probe_reads_one_item_and_reports_stock_state(monkeypatch, scenario):
    from inventory_tracking.shop import capture

    data = record()
    grid_owners = owners(data)
    grids = copy.deepcopy(grid_owners[0]['grids'])
    by_id = {entry['row']['unit_id']: entry['row'] for entry in data['rows']}
    potion_pointer = next(u['address'] for u in data['snapshot']['groups']['items']['units'] if u['txt_id'] == 611)
    if scenario == 'unloaded':
        for grid in grids.values():
            grid['cells'] = [0] * 100
    if scenario == 'no_gear':
        for index, grid in grids.items():
            grid['cells'] = [potion_pointer if index == 5 and p else 0 for p in grid['cells']]
        potion = next(u for u in data['snapshot']['groups']['items']['units'] if u['txt_id'] == 611)
        potion['details']['inventory_page'] = 3
    reads = {'items': 0, 'grids': 0}

    def grid_reader(read, unit):
        reads['grids'] += 1
        if scenario == 'changed' and reads['grids'] > 1:
            return {}
        return copy.deepcopy(grids)

    def row_reader(read, unit, items):
        reads['items'] += 1
        row = copy.deepcopy(by_id[unit['unit_id']])
        if scenario == 'gamble':
            raw = bytearray.fromhex(row['resource_stats']['item_data_hex'])
            raw[0x18] &= ~0x10
            row['resource_stats']['item_data_hex'] = raw.hex()
        return row

    monkeypatch.setattr(capture, 'read_owner_grids', grid_reader)
    monkeypatch.setattr(capture, 'read_location', lambda *args: 2 if scenario == 'away' else 40)  # 2 = Blood Moor
    monkeypatch.setattr(capture, 'read_item_record', row_reader)
    monkeypatch.setattr(capture, 'unit_matches', lambda read, u: True)
    if scenario == 'changed':
        with pytest.raises(ValueError, match='changed'):
            capture.probe_stock(None, data['snapshot'])
        return
    probe = capture.probe_stock(None, data['snapshot'])
    assert probe['state'] == scenario
    if scenario == 'away':
        assert reads == {'items': 0, 'grids': 0}
    elif scenario in ('unloaded', 'no_gear'):
        assert reads['items'] == 0
        assert 'key' not in probe
    else:
        assert reads['items'] == 1  # one item record, never the whole stock
        assert probe['key']['txt_id'] == 351
        assert probe['key']['identified'] is (scenario == 'loaded')
        assert probe['stock_count'] == 4
