"""Per-character key bindings from the game's .keyo/.key files (Saved Games, 2026-10-05): a u16
header, then 10-byte records (u32 action, u16 Windows virtual-key code, u32 1 primary/0
secondary); 0xFFFF is unbound. Show Items is action 37: Alt (0x12) in the 19 default files,
Z (0x5A) for CybergrindAA."""

import struct

import pytest

from inventory_tracking.input.keybindings import (
    SHOW_ITEMS,
    action_keys,
    button_number,
    key_file,
    show_items_key,
    x11_name,
)


def key_data(*records, header=37):
    return struct.pack('<H', header) + b''.join(struct.pack('<IHI', *record) for record in records)


def test_records_give_the_primary_key_first_and_skip_unbound_slots():
    data = key_data((1, 0x49, 1), (1, 0x42, 0), (SHOW_ITEMS, 0xFFFF, 1), (SHOW_ITEMS, 0x5A, 0), (0, 0xFFFF, 1))

    assert action_keys(data, 1) == [0x49, 0x42]
    assert action_keys(data, SHOW_ITEMS) == [0x5A]
    assert action_keys(data, 0) == []


@pytest.mark.parametrize(
    ('code', 'name'),
    [
        (0x5A, 'z'),
        (0x41, 'a'),
        (0x37, '7'),
        (0x12, 'Alt_L'),
        (0x10, 'Shift_L'),
        (0x11, 'Control_L'),
        (0x70, 'F1'),
        (0x7B, 'F12'),
        (0xC0, 'grave'),
        (0x09, 'Tab'),
        (0x20, 'space'),
        (0x100, 'Button2'),  # the middle mouse button
        (0x101, 'Button8'),  # mouse 4
        (0x102, 'Button9'),  # mouse 5: CybergrindAA's Sigil: Lethargy (2026-10-09)
        (0x103, 'Button4'),  # wheel up
        (0x104, 'Button5'),
        (0x1009, None),
    ],
)
def test_virtual_key_codes_become_x11_key_names(code, name):
    # 0x1000 and up are modifier combinations: not something to press.
    assert x11_name(code) == name


def test_button_names_give_their_x11_button_and_keys_give_none():
    assert button_number('Button9') == 9
    assert button_number('Button') is None
    assert button_number('KP_5') is None
    assert button_number('b') is None


def test_the_key_file_is_the_characters_own_not_a_longer_name_sharing_its_start(tmp_path):
    for name in ('CybergrindAA194867311.keyo', 'CybergrindAAB5.keyo', 'CyberOA.key', 'CybergrindAA.ctlo'):
        (tmp_path / name).write_bytes(b'')

    assert key_file(tmp_path, 'CybergrindAA') == tmp_path / 'CybergrindAA194867311.keyo'
    assert key_file(tmp_path, 'CyberOA') == tmp_path / 'CyberOA.key'  # offline character
    assert key_file(tmp_path, 'Nobody') is None


def test_show_items_key_of_a_character(tmp_path):
    (tmp_path / 'CybergrindAA194867311.keyo').write_bytes(key_data((SHOW_ITEMS, 0x5A, 1), (SHOW_ITEMS, 0xFFFF, 0)))
    (tmp_path / 'AmazonAA219512753.keyo').write_bytes(key_data((SHOW_ITEMS, 0x12, 1), (SHOW_ITEMS, 0x101, 0)))
    (tmp_path / 'Mouse1.keyo').write_bytes(key_data((SHOW_ITEMS, 0x101, 1)))

    assert show_items_key(tmp_path, 'CybergrindAA') == 'z'
    assert show_items_key(tmp_path, 'AmazonAA') is None  # the default Alt: never pressed
    assert show_items_key(tmp_path, 'Mouse') is None  # bound to a mouse button only
    assert show_items_key(tmp_path, 'Nobody') is None


def test_modifier_keys_are_never_the_show_items_key(tmp_path):
    # Alt switches the keyboard layout on the user's desktop (user, 2026-10-06); Shift and Control
    # are modifiers too. A secondary key that is safe to press still counts.
    (tmp_path / 'Alt1.keyo').write_bytes(key_data((SHOW_ITEMS, 0x12, 1), (SHOW_ITEMS, 0x5A, 0)))
    (tmp_path / 'Shift1.keyo').write_bytes(key_data((SHOW_ITEMS, 0x10, 1)))

    assert show_items_key(tmp_path, 'Alt') == 'z'
    assert show_items_key(tmp_path, 'Shift') is None


@pytest.mark.parametrize(
    ('code', 'name'),
    [
        (0x65, 'KP_5'),  # VK_NUMPAD5: the user's Teleport key (2026-10-09)
        (0x60, 'KP_0'),
        (0x69, 'KP_9'),
        (0x0C, 'KP_Begin'),  # the same key with Num Lock off
        (0x6B, 'KP_Add'),
        (0x6F, 'KP_Divide'),
        (0x21, 'Prior'),
        (0x2E, 'Delete'),
        (0x1B, 'Escape'),
    ],
)
def test_keypad_and_navigation_keys_have_x11_names(code, name):
    assert x11_name(code) == name
