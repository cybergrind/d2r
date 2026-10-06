"""A character's key bindings from the game's own files.

D2R keeps bindings per character in Saved Games: `<name><account digits>.keyo` online,
`<name>.key` offline (2026-10-05). Layout: a u16 header (37), then 10-byte records: u32 action,
u16 Windows virtual-key code (0xFFFF unbound), u32 slot (1 primary, 0 secondary). Show Items
is action 37: Alt (0x12) primary in the 19 untouched files, Z (0x5A) for CybergrindAA, which
the user rebinds; Alt is never pressed (see MODIFIERS). Codes from 0x100 up are mouse buttons or modifier combinations.
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

NAMED = {
    0x09: 'Tab',
    0x0D: 'Return',
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
    """X11 key name of a Windows virtual-key code; None for mouse buttons, combinations and the rest."""
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
    modifier (the default Alt) is not pressable."""
    path = key_file(saved_games, name)
    if path is None:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    keys = (x11_name(code) for code in action_keys(data, SHOW_ITEMS))
    return next((key for key in keys if key and key not in MODIFIERS), None)
