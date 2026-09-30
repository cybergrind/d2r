from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.sockets import annotate_sockets


def jewel_capture():
    txt, _base = next((k, b) for k, b in metadata()['bases'].items() if b['name'] == 'Jewel')
    return {
        'position': 0,
        'unit': {'txt_id': int(txt), 'unit_id': 8, 'details': {'quality': 4}},
        'item_data_hex': bytes(0x60).hex(),
        'stat_arrays': {
            'complete': True,
            'arrays': [{'header_offset': 0xE8, 'stats': [{'id': 93, 'layer': 0, 'raw': 15}]}],
        },
    }


def test_socket_annotation_preserves_child_stat_evidence():
    item = {}
    decoded = [{'memory_stat': {'id': 194}, 'status': 'decoded', 'value': 1}]
    child = jewel_capture()
    annotate_sockets(item, decoded, {'socket_items': {'complete': True, 'children': [child]}}, None)
    payload = item['socket_items'][0]
    assert payload['item_type'] == 'jewl'
    assert payload['stats']['93:0']['value'] == 15
    assert payload['stats_complete'] is True
    child.pop('stat_arrays')
    annotate_sockets(item, decoded, {'socket_items': {'complete': True, 'children': [child]}}, None)
    assert item['socket_items'][0]['stats_complete'] is False


def test_grouped_socket_stats_preserve_native_values():
    from inventory_tracking.items.socket_payload import decode_payload

    child = jewel_capture()
    child['stat_arrays']['arrays'][0]['stats'] = [
        {'id': stat, 'layer': 0, 'raw': raw}
        for stat, raw in ((17, 31), (18, 31), (93, 15), (57, 102), (58, 102), (59, 100), (326, 1))
    ]
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Jewel')
    payload = decode_payload(child, base)
    assert payload['stats_complete'] is True
    assert {key: row['value'] for key, row in payload['stats'].items()} == {
        '17:0': 31,
        '18:0': 31,
        '93:0': 15,
        '57:0': 102 / 256,
        '58:0': 102 / 256,
        '59:0': 4,
        '326:0': 1,
    }
    assert payload['stats']['59:0']['unit'] == 'seconds'
    assert payload['stats']['57:0']['unit'] == 'damage_per_frame'
