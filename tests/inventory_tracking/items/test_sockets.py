from typing import Any

from inventory_tracking.items.sockets import annotate_sockets


def test_captured_socket_child_names_are_reported_separately_from_recipes():
    item: dict[str, Any] = {'socket_contents': None}
    rows: list[dict[str, Any]] = [{'status': 'decoded', 'memory_stat': {'id': 194}, 'value': 3, 'text': 'Sockets: 3'}]
    # Jewel class verified against the local misc.json catalog.
    child = {
        'position': 0,
        'item_data_hex': bytes(0x60).hex(),
        'unit': {'txt_id': 658, 'unit_id': 1, 'details': {'quality': 4}},
    }
    annotate_sockets(item, rows, {'socket_items': {'children': [child]}}, None)
    assert item['socket_items'][0]['name'] == 'Jewel'
    assert rows[0]['socket_source'] == 'captured_children'
    assert 'recipe' not in rows[0]['text']


def test_missing_socket_capture_does_not_claim_empty_sockets():
    item: dict[str, Any] = {'socket_contents': None}
    rows: list[dict[str, Any]] = [{'status': 'decoded', 'memory_stat': {'id': 194}, 'value': 3}]
    annotate_sockets(item, rows, {}, None)
    assert item['socket_contents'] is None
    assert 'contents not captured' in rows[0]['text']


def test_completed_empty_socket_scan_reports_open_sockets():
    item: dict[str, Any] = {'socket_contents': None}
    rows: list[dict[str, Any]] = [{'status': 'decoded', 'memory_stat': {'id': 194}, 'value': 3, 'text': 'Sockets: 3'}]
    annotate_sockets(item, rows, {'socket_items': {'children': [], 'complete': True}}, None)
    assert item['socket_contents'] == 'empty'
    assert item['empty_sockets'] == 3
    assert rows[0]['text'] == 'Sockets: 3 — 3 empty'


def test_empty_partial_socket_scan_does_not_claim_empty_sockets():
    item: dict[str, Any] = {'socket_contents': None}
    rows: list[dict[str, Any]] = [{'status': 'decoded', 'memory_stat': {'id': 194}, 'value': 3}]
    annotate_sockets(item, rows, {'socket_items': {'children': [], 'complete': False}}, None)
    assert item['socket_contents'] is None
