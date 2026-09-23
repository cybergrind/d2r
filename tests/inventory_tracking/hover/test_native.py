import struct

from inventory_tracking.hover.native import collect_native


def fixture():
    memory = bytearray(0x2000000)
    widget = bytearray(0x700)
    struct.pack_into('<Q', widget, 0x30, 0x1000)
    struct.pack_into('<II', widget, 0x5C4, 123, 0)
    struct.pack_into('<III', memory, 0x2000, 0, 7, 123)
    struct.pack_into('<Q', memory, 0x2090, 0x3000)
    struct.pack_into('<I', memory, 0x3000, 0x1020304)
    struct.pack_into('<QQ', memory, 0x3020, 0x4000, 3)
    memory[0x4050:0x4052] = bytes([10, 4])
    struct.pack_into('<Q', memory, 0x4058, 0x5000)
    struct.pack_into('<Q', memory, 0x5000, 0x6000)
    ui = {'widgets': {'mouse': {'address': 0x7000, 'raw_hex': widget.hex()}, 'controller': None}}
    memory[0x7000:0x7700] = widget
    units = {
        'groups': {'players': {'units': [{'address': 0x2000, 'type': 0, 'unit_id': 123, 'identity_stable': True}]}}
    }
    return memory, ui, units


def test_native_capture_uses_typed_owner_and_bounded_grid():
    memory, ui, units = fixture()
    units['groups']['items'] = {'units': [{'address': 0x9000, 'type': 4, 'unit_id': 123, 'identity_stable': True}]}
    result = collect_native(lambda a, n: bytes(memory[a : a + n]), 0, ui, units)
    assert not result['errors']
    assert result['stable']
    assert any(b['address'] == 0x5000 and len(bytes.fromhex(b['raw_hex'])) == 320 for b in result['blocks'])
    assert result['owners'][0]['unit_id'] == 123
    assert result['validated'] is False


def test_parent_cycle_is_bounded_and_preserved():
    memory, ui, units = fixture()
    struct.pack_into('<Q', memory, 0x1030, 0x1000)
    result = collect_native(lambda a, n: bytes(memory[a : a + n]), 0, ui, units)
    assert any('cycle' in error for error in result['errors'])
    assert not result['stable']


def test_corrupt_grid_dimensions_never_trigger_large_read():
    memory, ui, units = fixture()
    memory[0x4050] = 255
    reads = []

    def read(a, n):
        reads.append((a, n))
        return bytes(memory[a : a + n])

    result = collect_native(read, 0, ui, units)
    assert any('dimensions' in error for error in result['errors'])
    assert not any(a == 0x5000 for a, n in reads)


def test_panel_probe_captures_equipment_grid_even_with_unknown_widget_page():
    memory, ui, units = fixture()
    memory[0x4010:0x4012] = bytes([13, 1])
    struct.pack_into('<Q', memory, 0x4018, 0x5800)
    struct.pack_into('<Q', memory, 0x5800, 0x6000)
    memory[0x7630] = 255
    ui['widgets']['mouse']['raw_hex'] = bytes(memory[0x7000:0x7700]).hex()
    result = collect_native(lambda a, n: bytes(memory[a : a + n]), 0, ui, units, all_grids=True)
    assert not result['errors']
    assert any(b['address'] == 0x5800 and len(bytes.fromhex(b['raw_hex'])) == 104 for b in result['blocks'])


def test_production_capture_targets_equipment_grid_without_panel_probe_mode():
    memory, ui, units = fixture()
    ui['widgets']['mouse']['vtable'] = 0x17129D0
    memory[0x4010:0x4012] = bytes([13, 1])
    struct.pack_into('<Q', memory, 0x4018, 0x5800)
    result = collect_native(lambda a, n: bytes(memory[a : a + n]), 0, ui, units)
    assert not result['errors']
    addresses = {b['address'] for b in result['blocks']}
    assert 0x5800 in addresses
    assert 0x5000 not in addresses
