import struct

from inventory_tracking.hover.ui import collect_ui


def memory_reader():
    memory = bytearray(0x4000000)
    struct.pack_into('<Q', memory, 0x1EE5790, 0x3000000)
    struct.pack_into('<Q', memory, 0x30000D0, 0x3001000)
    struct.pack_into('<Q', memory, 0x3001178, 0x3002000)
    struct.pack_into('<Q', memory, 0x3002000, 0x1700000)
    struct.pack_into('<Q', memory, 0x17000C0, 0x21C6B0)
    return memory, lambda address, size: bytes(memory[address : address + size])


def test_collects_only_bounded_ui_path_and_retains_empty_focus():
    _, read = memory_reader()
    result = collect_ui(read, 0, 0x2789000)
    assert result['stable']
    assert result['widgets']['mouse']['address'] == 0x3002000
    assert result['widgets']['controller'] is None
    assert len(bytes.fromhex(result['widgets']['mouse']['raw_hex'])) == 0x700
    assert result['widgets']['mouse']['methods']['0xc0'] == 0x21C6B0
    assert result['validated'] is False


def test_changed_focus_is_retained_but_never_stable():
    memory, read = memory_reader()
    calls = 0

    def changing(address, size):
        nonlocal calls
        if address == 0x3001178:
            calls += 1
            if calls == 2:
                struct.pack_into('<Q', memory, address, 0)
        return read(address, size)

    result = collect_ui(changing, 0, 0x2789000)
    assert not result['stable']
    assert result['widgets']['mouse']['address'] == 0x3002000
    assert any(row['before_hex'] != row['after_hex'] for row in result['anchors'])


def test_unreadable_widget_preserves_focus_and_diagnostics():
    _, read = memory_reader()

    def partial(address, size):
        if address == 0x3002000:
            raise ValueError('unreadable widget')
        return read(address, size)

    result = collect_ui(partial, 0, 0x2789000)
    assert not result['stable']
    assert result['widgets']['mouse']['address'] == 0x3002000
    assert 'unreadable widget' in result['widgets']['mouse']['error']


def test_external_vtable_is_not_followed():
    memory, read = memory_reader()
    struct.pack_into('<Q', memory, 0x3002000, 0x3005000)
    result = collect_ui(read, 0, 0x2789000)
    assert 'methods' not in result['widgets']['mouse']
    assert result['widgets']['mouse']['vtable_in_image'] is False


def test_path_change_across_unit_snapshot_is_not_stable():
    from inventory_tracking.hover.sampling import capture_ui_sample

    values = iter(
        [
            {'stable': True, 'anchors': [{'address': 100, 'before_hex': 'aa'}]},
            {'stable': True, 'anchors': [{'address': 100, 'before_hex': 'bb'}]},
        ]
    )
    result = capture_ui_sample(lambda: next(values), lambda: {'status': 'research'})
    assert not result['ui_path_stable']
    assert not result['validated']
    assert result['before']['anchors'][0]['before_hex'] == 'aa'


def test_probe_failure_is_published_as_finished(tmp_path, monkeypatch):
    import json

    from inventory_tracking.probes import hover_ui as hover_ui_probe

    def broken(*args):
        raise ValueError('unsupported build')

    monkeypatch.setattr(hover_ui_probe.LiveReader, 'connect', broken)
    assert hover_ui_probe.main(['--output', str(tmp_path)]) == 1
    report = json.loads(next(tmp_path.glob('*/report.json')).read_text())
    assert report['state'] == 'failed'
    assert report['finished_at']
    assert not report['validated']


def test_mouse_move_during_unit_snapshot_invalidates_request():
    from inventory_tracking.hover.sampling import capture_ui_sample

    observations = iter(
        [
            {'stable': True, 'anchors': [], 'mouse_position_hex': 'aa'},
            {'stable': True, 'anchors': [], 'mouse_position_hex': 'bb'},
        ]
    )
    result = capture_ui_sample(lambda: next(observations), lambda: {'status': 'research'})
    assert not result['ui_path_stable']
