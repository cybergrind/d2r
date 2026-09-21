"""UI candidates must be unique and stable before potion keys are allowed."""

import struct

from inventory_tracking.game_ui import UI_SIGNATURE, read_ui_state, scan_ui_flags


def test_signature_handles_contiguous_split_and_signed_displacement():
    code = UI_SIGNATURE + struct.pack('<i', -0x100)
    assert scan_ui_flags([(0x2000, code[:5]), (0x2005, code[5:])], 0x1000, 0x4000) == [0x1F00]
    assert scan_ui_flags([(0x2000, code[:5]), (0x2006, code[5:])], 0x1000, 0x4000) == []


def test_unknown_chat_loading_and_changing_flags_block_input():
    assert not read_ui_state(lambda a, n: bytes(n), [])['ready']
    assert read_ui_state(lambda a, n: bytes(n), [4096])['ready']
    for offset in [5, 0x168, 0x1E]:
        data = bytearray(0x16D)
        data[offset] = 1
        assert not read_ui_state(lambda a, n, data=data: bytes(data), [4096])['ready']
    reads = iter([bytes(0x16D), bytes([1]) + bytes(0x16C)])
    assert not read_ui_state(lambda a, n: next(reads), [4096])['ready']
