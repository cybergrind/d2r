import struct

import pytest

from inventory_tracking.hover.legacy import capture_selection, parse_hover, scan_hover


def test_signature_across_contiguous_blocks_but_not_gaps():
    code = b'\xc6\x84\xc2' + struct.pack('<I', 0x201) + b'\x00\x48\x8b\x74'
    assert scan_hover([(100, code[:5]), (105, code[5:])], 0, 4096) == [512]
    assert scan_hover([(100, code[:5]), (106, code[5:])], 0, 4096) == []


def test_empty_hover_ignores_stale_unit_id():
    assert parse_hover(struct.pack('<HHII', 0, 0, 4, 123)) is None
    assert parse_hover(struct.pack('<HHII', 1, 0, 4, 123)) == {'unit_type': 4, 'unit_id': 123}


def test_changed_hover_during_capture_is_rejected():
    values = iter([{'unit_type': 4, 'unit_id': 123}, None])
    with pytest.raises(ValueError, match='changed'):
        capture_selection(lambda: next(values), lambda: {'groups': {'items': {'units': []}}})


def test_selection_requires_matching_stable_item():
    def hover():
        return {'unit_type': 4, 'unit_id': 123}

    snapshot = {
        'status': 'research',
        'groups': {
            'items': {
                'complete': True,
                'units': [
                    {'unit_id': 123, 'identity_stable': True, 'txt_id': 537},
                ],
            }
        },
    }
    assert capture_selection(hover, lambda: snapshot)['item']['unit_id'] == 123
    snapshot['groups']['items']['units'][0]['identity_stable'] = False
    with pytest.raises(ValueError, match='stable'):
        capture_selection(hover, lambda: snapshot)


def test_discovery_accepts_live_reader_capture_summary(tmp_path):
    import json

    from inventory_tracking.probes.hover_legacy import discover_hover

    code = b'\xc6\x84\xc2' + struct.pack('<I', 0x201) + b'\x00\x48\x8b\x74'
    (tmp_path / 'image.bin').write_bytes(code)
    (tmp_path / 'capture.json').write_text(
        json.dumps(
            {
                'base': 0,
                'pe': {
                    'image_size': 4096,
                    'sections': [{'characteristics': 0x20000000, 'rva': 100, 'virtual_size': len(code)}],
                },
                'blocks': [{'address': 100, 'size': len(code), 'file_offset': 0, 'mapping_stable': True}],
            }
        )
    )
    assert discover_hover(tmp_path, {'status': 'captured', 'manifest': 'capture.json'}) == 512


def test_unexpected_probe_error_publishes_failed_completion(tmp_path, monkeypatch):
    import json

    from inventory_tracking.probes import hover_legacy as hover_probe

    def broken(*args):
        raise KeyError('blocks')

    monkeypatch.setattr(hover_probe.LiveReader, 'connect', broken)
    assert hover_probe.main(['--output', str(tmp_path)]) == 1
    reports = list(tmp_path.glob('*/report.json'))
    report = json.loads(reports[0].read_text())
    assert report['state'] == 'failed'
    assert report['finished_at']


def test_indexed_hover_reads_selected_slot_and_rejects_changed_selector():
    from inventory_tracking.hover.legacy import read_indexed_hover

    memory = {100: struct.pack('<I', 2), 232: struct.pack('<HHII', 1, 0, 4, 123)}
    result = read_indexed_hover(lambda address, size: memory[address], 200, 100)
    assert result['hover']['unit_id'] == 123
    assert result['slot'] == 2
    reads = 0

    def changing(address, size):
        nonlocal reads
        if address == 100:
            reads += 1
            return struct.pack('<I', 2 if reads == 1 else 3)
        return memory[address]

    with pytest.raises(ValueError, match='selector changed'):
        read_indexed_hover(changing, 200, 100)


def test_selector_is_resolved_from_indexing_instruction(tmp_path):
    import json

    from inventory_tracking.probes.hover_legacy import discover_selector

    code = b'\x8b\x0d' + struct.pack('<i', 300 - 106) + b'\x8b\xc1\x48\x03\xc0'
    code += b'\xc6\x84\xc2' + struct.pack('<I', 513) + b'\x01\x48\x8b\x74'
    (tmp_path / 'image.bin').write_bytes(code)
    (tmp_path / 'capture.json').write_text(
        json.dumps(
            {
                'base': 0,
                'pe': {
                    'image_size': 4096,
                    'sections': [{'characteristics': 0x20000000, 'rva': 100, 'virtual_size': len(code)}],
                },
                'blocks': [{'address': 100, 'size': len(code), 'file_offset': 0, 'mapping_stable': True}],
            }
        )
    )
    assert discover_selector(tmp_path, 512) == 300
