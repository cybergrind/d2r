"""A character's key bindings from the game's own files.

D2R keeps bindings per character in Saved Games: `<name><account digits>.keyo` online,
`<name>.key` offline (2026-10-05). Layout: a u16 header (37), then 10-byte records: u32 action,
u16 Windows virtual-key code (0xFFFF unbound), u32 slot (1 primary, 0 secondary). Show Items
is action 37: Alt (0x12) primary in the 19 untouched files, Z (0x5A) for CybergrindAA, which
the user rebinds; Alt is never pressed (see MODIFIERS). Codes from 0x100 up are mouse buttons or
modifier combinations: the untouched files bind 0x100-0x104 by default (0x101 is Show Items' second
key, 0x103/0x104 actions 39/40), CybergrindAA has Sigil: Lethargy on 0x102 (2026-10-09). They are
taken as the buttons beyond left and right in the game's order: middle, mouse 4, mouse 5, wheel up,
wheel down, named by their X11 button numbers (`Button2`, `Button8`, `Button9`, `Button4`,
`Button5`); unverified until a macro presses one. 0x1000 and 0x2000 on a code are modifier flags
(the defaults hold 0x1009 and 0x2009 on Tab), which no macro presses.
"""

import re
import struct
from pathlib import Path


SHOW_ITEMS = 37
UNBOUND = 0xFFFF
HEADER = 2
RECORD = struct.Struct('<IHI')
PRIMARY = 1
# Never pressed on their own: Alt switches the keyboard layout on the user's desktop (user,
# 2026-10-06), and Shift/Control/Caps Lock are modifiers too.
MODIFIERS = frozenset(('Alt_L', 'Shift_L', 'Control_L', 'Caps_Lock'))
BUTTON_PREFIX = 'Button'
MOUSE_BUTTONS = {0x100: 2, 0x101: 8, 0x102: 9, 0x103: 4, 0x104: 5}  # key file code -> X11 button

NAMED = {
    0x08: 'BackSpace',
    0x09: 'Tab',
    0x0C: 'KP_Begin',  # VK_CLEAR: the keypad 5 with Num Lock off
    0x0D: 'Return',
    0x1B: 'Escape',
    0x21: 'Prior',
    0x22: 'Next',
    0x23: 'End',
    0x24: 'Home',
    0x25: 'Left',
    0x26: 'Up',
    0x27: 'Right',
    0x28: 'Down',
    0x2D: 'Insert',
    0x2E: 'Delete',
    # The keypad with Num Lock on (VK_NUMPAD0-9 and the operators; the user puts Teleport on KP_5,
    # 2026-10-09). KP_5 and KP_Begin share a key code, so the game sees whichever Num Lock makes of it.
    **{0x60 + digit: f'KP_{digit}' for digit in range(10)},
    0x6A: 'KP_Multiply',
    0x6B: 'KP_Add',
    0x6D: 'KP_Subtract',
    0x6E: 'KP_Decimal',
    0x6F: 'KP_Divide',
    0x10: 'Shift_L',
    0x11: 'Control_L',
    0x12: 'Alt_L',
    0x14: 'Caps_Lock',
    0x20: 'space',
    0xBA: 'semicolon',
    0xBB: 'equal',
    0xBC: 'comma',
    0xBD: 'minus',
    0xBE: 'period',
    0xBF: 'slash',
    0xC0: 'grave',
    0xDB: 'bracketleft',
    0xDC: 'backslash',
    0xDD: 'bracketright',
    0xDE: 'apostrophe',
}


def action_keys(data: bytes, action: int) -> list[int]:
    """Virtual-key codes bound to `action`, primary first; unbound slots left out."""
    slots = [
        (slot, code)
        for found, code, slot in (
            RECORD.unpack_from(data, offset) for offset in range(HEADER, len(data) - RECORD.size + 1, RECORD.size)
        )
        if found == action and code != UNBOUND
    ]
    return [code for slot, code in sorted(slots, key=lambda pair: pair[0] != PRIMARY)]


def x11_name(code: int) -> str | None:
    """X11 key name of a Windows virtual-key code, or `Button<n>` for a mouse button; None for
    modifier combinations and the rest."""
    if code in MOUSE_BUTTONS:
        return f'{BUTTON_PREFIX}{MOUSE_BUTTONS[code]}'
    if 0x41 <= code <= 0x5A:
        return chr(code).lower()
    if 0x30 <= code <= 0x39:
        return chr(code)
    if 0x70 <= code <= 0x87:
        return f'F{code - 0x6F}'
    return NAMED.get(code)


def key_file(saved_games: Path, name: str) -> Path | None:
    """The character's own key file; a longer name sharing its start (CybergrindAAB) is another one."""
    pattern = re.compile(re.escape(name) + r'\d*\.keyo?')
    try:
        found = [path for path in saved_games.iterdir() if pattern.fullmatch(path.name)]
    except OSError:
        return None
    return max(found, key=lambda path: path.stat().st_mtime) if found else None


def show_items_key(saved_games: Path, name: str) -> str | None:
    """X11 name of the first pressable key bound to Show Items for this character, if any; a
    modifier (the default Alt) and a mouse button (the default second key) are not pressable."""
    path = key_file(saved_games, name)
    if path is None:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    keys = (x11_name(code) for code in action_keys(data, SHOW_ITEMS))
    return next((key for key in keys if key and key not in MODIFIERS and button_number(key) is None), None)


def button_number(name: str) -> int | None:
    """The X11 button of a `Button<n>` name; None for a key name."""
    if name.startswith(BUTTON_PREFIX) and name[len(BUTTON_PREFIX) :].isdigit():
        return int(name[len(BUTTON_PREFIX) :])
    return None
