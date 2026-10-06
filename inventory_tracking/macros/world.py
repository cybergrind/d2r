"""What a macro may ask about the game, read fresh from memory in one pass.

Image addresses found with the record probe on 2026-10-06 (plan.md, findings): the skill slot
table, the game name and the in-game byte. The unit table is the one the service attached to;
it stays at the same address through the lobby and into the next game.
"""

import contextlib
import os
import re
import struct
from dataclasses import dataclass, field

from inventory_tracking.levels.memory import pointer
from inventory_tracking.native.layout import (
    DEAD_MODES,
    LEVEL_AREA_ID,
    PANEL_FLAGS,
    PATH_ROOM1,
    ROOM1_ROOM2,
    ROOM2_LEVEL,
    TOWN_IDS,
    UI_PANELS_RVA,
    UI_PANELS_SIZE,
)
from inventory_tracking.native.units import walk_units
from inventory_tracking.tracking.consume import read_consume


SKILL_SLOTS_RVA = 0x1E011B0
SKILL_SLOTS = 16
SKILL_SLOT_SIZE = 28
EMPTY_SLOT = 0xFFFFFFFF
GAME_NAME_RVA = 0x1E9A0B8
GAME_NAME_SIZE = 32
# Research: bytes that moved around the loading screen in the one recording. The two tried as
# "loading" (0x2122131) and "playable" (0x20D7DA0) both read wrong in loaded games on the host
# (2026-10-06), so none is relied on; their changes are logged against the moment the first
# summon works (routines.LoadTrace) to find one that really marks a playable game.
TRACE_RVAS = (
    0x20D7DA0, 0x25A5C41, 0x2121F39, 0x2121F81, 0x2121FE9, 0x2122011, 0x21220B1, 0x2122131,
    0x19DAB10, 0x1ABD6F1, 0x1AB8A71, 0x1AB8AEC, 0x1E3C410, 0x1E3C7F0, 0x1EC39BE, 0x1EC38EA,
    0x1EB3465, 0x1EB118D, 0x1EC3944, 0x1A7EC19,
)  # fmt: skip
# 255 in a game, 0 while a new game loads, back (254, then 255) when its view comes up: 6.5 s
# after Enter in the recording and 6.2 s and 6.6 s in two traced host runs (2026-10-06), where
# the first key was accepted. 0x1EB118D moves with it.
VIEW_RVA = 0x1EB3465
IN_GAME = 0x00  # byte of the panel array: 1 in a game, 0 from Save and Exit to the next game
MONSTER_OWNER = 84  # monster data u32[21]: the owning player's unit id (native/mercenary.py)
MONSTER_UNIT = 1
DEFILER_CLASS = 744
# Flags that mean something is open over the game view; the array also holds bytes that are
# set with nothing open (Show Items, belt rows and unnamed ones).
OPEN_PANELS = {name: offset for name, offset in PANEL_FLAGS.items() if name != 'belt_rows'}


@dataclass(frozen=True)
class Player:
    unit_id: int
    name: str
    mode: int
    area: int
    x: float  # world units
    y: float
    consume: bool | None  # None when the effect list could not be read

    @property
    def in_town(self) -> bool:
        return self.area in TOWN_IDS


@dataclass(frozen=True)
class Monster:
    unit_id: int
    txt_id: int
    mode: int
    x: float
    y: float
    owner: int
    raw: bytes = field(default=b'', compare=False, repr=False)  # unit and monster data, Defilers only


@dataclass(frozen=True)
class World:
    in_game: bool
    open_panels: tuple[str, ...]
    game_name: str
    slots: tuple[int | None, ...]  # skill id by slot
    trace: bytes = b''  # research: the bytes at TRACE_RVAS
    view: int = 255  # the byte at VIEW_RVA: 0 while a game loads
    player: Player | None = None
    monsters: tuple[Monster, ...] = ()  # alive, with a position

    @property
    def quit_menu(self) -> bool:
        return 'quit_menu' in self.open_panels


def decode_slots(raw: bytes) -> tuple[int | None, ...]:
    if len(raw) != SKILL_SLOTS * SKILL_SLOT_SIZE:
        raise ValueError('Short skill slot table')
    ids = [struct.unpack_from('<I', raw, slot * SKILL_SLOT_SIZE)[0] for slot in range(SKILL_SLOTS)]
    if any(skill != EMPTY_SLOT and skill >= 1024 for skill in ids):
        raise ValueError('Skill slot table does not hold skill ids')
    return tuple(None if skill == EMPTY_SLOT else skill for skill in ids)


def decode_name(raw: bytes) -> str:
    return raw.split(b'\0', 1)[0].decode('ascii', errors='replace')


def next_name(name: str) -> str:
    """cyber32 -> cyber33; only names a macro can type (lower-case letters, digits, a number last)."""
    found = re.fullmatch(r'([a-z0-9]*?)(\d+)', name)
    if not found:
        raise ValueError(f'game name {name!r} does not end in a number')
    return f'{found[1]}{int(found[2]) + 1}'


def position(path: bytes) -> tuple[float, float]:
    x_fraction, x, y_fraction, y = struct.unpack_from('<HHHH', path)
    return x + x_fraction / 65536, y + y_fraction / 65536


class GameMemory:
    """Keeps /proc/<pid>/mem open for one macro run."""

    def __init__(self, pid: int, base: int, table: int) -> None:
        self.base, self.table = base, table
        self.fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)

    def close(self) -> None:
        os.close(self.fd)

    def read(self, address: int, size: int) -> bytes:
        data = os.pread(self.fd, size, address)
        if len(data) != size:
            raise ValueError('short read')
        return data

    def _player(self) -> Player | None:
        heads = struct.unpack('<128Q', self.read(self.table, 1024))
        found = []
        for unit in walk_units(self.read, heads, 0)['units']:
            if not unit['path_pointer']:
                continue
            try:
                path = self.read(unit['path_pointer'], 0x28)
                room1 = struct.unpack_from('<Q', path, PATH_ROOM1)[0]
                level = pointer(self.read, pointer(self.read, room1 + ROOM1_ROOM2) + ROOM2_LEVEL)
                area = struct.unpack('<I', self.read(level + LEVEL_AREA_ID, 4))[0]
                name = decode_name(self.read(unit['data_pointer'], 16))
            except OSError, ValueError, struct.error:
                continue
            try:
                consume = read_consume(self.read, unit['stats_pointer']).active
            except OSError, ValueError, struct.error:
                consume = None
            found.append(Player(unit['unit_id'], name, unit['mode'], area, *position(path), consume))
        # Several player units may stand for the one character (levels/memory.py); a game with
        # another character in view is not handled.
        return min(found, key=lambda p: p.unit_id) if len({p.name for p in found}) == 1 else None

    def _monsters(self) -> tuple[Monster, ...]:
        heads = struct.unpack('<128Q', self.read(self.table + MONSTER_UNIT * 1024, 1024))
        found = []
        for unit in walk_units(self.read, heads, MONSTER_UNIT)['units']:
            if unit['mode'] in DEAD_MODES or not unit['path_pointer'] or not unit['data_pointer']:
                continue
            try:
                path = self.read(unit['path_pointer'], 8)
                owner = struct.unpack('<I', self.read(unit['data_pointer'] + MONSTER_OWNER, 4))[0]
            except OSError, ValueError:
                continue
            raw = b''
            if unit['txt_id'] == DEFILER_CLASS:
                with contextlib.suppress(OSError, ValueError):
                    raw = self.read(unit['address'], 0x160) + self.read(unit['data_pointer'], 0x80)
            found.append(Monster(unit['unit_id'], unit['txt_id'], unit['mode'], *position(path), owner, raw))
        return tuple(found)

    def world(self) -> World:
        panels = self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)
        in_game = panels[IN_GAME] == 1
        player, monsters = None, ()
        if in_game:
            try:
                player = self._player()
                monsters = self._monsters() if player is not None else ()
            except OSError, ValueError, struct.error:
                player, monsters = None, ()
        return World(
            in_game=in_game,
            open_panels=tuple(name for name, offset in OPEN_PANELS.items() if panels[offset] == 1),
            game_name=decode_name(self.read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE)),
            slots=decode_slots(self.read(self.base + SKILL_SLOTS_RVA, SKILL_SLOTS * SKILL_SLOT_SIZE)),
            trace=b''.join(self.read(self.base + rva, 1) for rva in TRACE_RVAS),
            view=self.read(self.base + VIEW_RVA, 1)[0],
            player=player,
            monsters=monsters,
        )
