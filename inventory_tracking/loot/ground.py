"""Valuable runes and expensive uniques on the ground, from streamed item units (only items near the player exist).

Item modes: 0 stored, 1 equipped, 2 belt (confirmed here, layout.py/layout_notes.md); 3 on
the ground and 5 dropping per MapAssist ItemMode. Position is the item's static path x/y
(+0x10/+0x14, as for objects) in world units. Ground mode and position are UNCONFIRMED on this
build until a Win+C next to a dropped rune checks them (levels/research.py records ground items).

A unique- or set-quality ground item is named from its base (loot/uniques.py). Its ItemData +0x34 table
index is logged with it: whether that is filled before identification is UNCONFIRMED on this build.

Shrines are object units: object data (unit +0x10) holds the shrine type at +0x08 and a shrine
table pointer at +0x10 (native/layout.py, confirmed with a Stamina Shrine 2026-09-30); object
positions (static path) were confirmed by the same dump. An unused shrine was in mode 0; that
used shrines leave mode 0 is the classic game's behaviour, not yet seen on this build.

Super chests (the glowing ones) are object class 397 (d2data objects.json 'sparklychest'): Win+C
dump 20260930T135418Z-6b2890e1 had one in Cave 2, mode 0 while closed. Lower Kurast's hut super
chests are ordinary jungle chests; the level guide marks those (levels/handlers/lower_kurast.py).
"""

import os
import struct
from dataclasses import dataclass, field

from inventory_tracking.items.identity import (
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
)
from inventory_tracking.levels.memory import player_location
from inventory_tracking.levels.model import Location
from inventory_tracking.loot.runes import is_valuable_rune
from inventory_tracking.loot.shrines import SHRINE_NAMES
from inventory_tracking.loot.uniques import BASES, unique_drop
from inventory_tracking.native.layout import OBJECT_SHRINE_TABLE, OBJECT_SHRINE_TYPE
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import walk_units


OBJECT_UNIT, ITEM_UNIT = 2, 4
UNUSED_SHRINE_MODE = 0
SPARKLY_CHEST = 397  # d2data objects.json *ID 397, Name 'chest', description 'sparklychest'
CLOSED_CHEST_MODE = 0
GROUND_MODES = frozenset((3, 5))  # on the ground, dropping


@dataclass(frozen=True)
class GroundRune:
    class_id: int
    unit_id: int
    x: int
    y: int


@dataclass(frozen=True)
class GroundUnique:
    label: str
    unit_id: int
    x: int
    y: int
    table_id: int | None = field(default=None, compare=False)  # ItemData +0x34 as read, for the log


@dataclass(frozen=True)
class Shrine:
    shrine_type: int
    unit_id: int
    x: int
    y: int

    @property
    def label(self) -> str:
        return SHRINE_NAMES[self.shrine_type]


@dataclass(frozen=True)
class SuperChest:
    unit_id: int
    x: int
    y: int
    label = 'Super chest'


def static_position(read, unit):
    path = read(unit['path_pointer'], 0x18)
    return struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF


def nearby_super_chests(read, table_address) -> list[SuperChest]:
    """Closed glowing chests among the streamed object units."""
    heads = struct.unpack('<128Q', read(table_address + OBJECT_UNIT * 1024, 1024))
    chests = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] != SPARKLY_CHEST or unit['mode'] != CLOSED_CHEST_MODE:
            continue
        try:
            x, y = static_position(read, unit)
        except OSError, ValueError:
            continue
        chests.append(SuperChest(unit['unit_id'], x, y))
    return chests


def nearby_shrines(read, table_address, *, types: frozenset[int]) -> list[Shrine]:
    """Unused shrines of the wanted types among the streamed object units."""
    heads = struct.unpack('<128Q', read(table_address + OBJECT_UNIT * 1024, 1024))
    shrines = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['mode'] != UNUSED_SHRINE_MODE:
            continue
        try:
            data = read(unit['data_pointer'], OBJECT_SHRINE_TABLE + 8)
            path = read(unit['path_pointer'], 0x18)
        except OSError, ValueError:
            continue
        table = struct.unpack_from('<Q', data, OBJECT_SHRINE_TABLE)[0]
        if not 0x10000 <= table < 2**47 or data[OBJECT_SHRINE_TYPE] not in types:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        shrines.append(Shrine(data[OBJECT_SHRINE_TYPE], unit['unit_id'], x, y))
    return shrines


def ground_runes(read, table_address, *, minimum: str) -> list[GroundRune]:
    heads = struct.unpack('<128Q', read(table_address + ITEM_UNIT * 1024, 1024))
    runes = []
    for unit in walk_units(read, heads, ITEM_UNIT)['units']:
        if unit['mode'] not in GROUND_MODES or not is_valuable_rune(unit['txt_id'], minimum=minimum):
            continue
        try:
            path = read(unit['path_pointer'], 0x18)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        runes.append(GroundRune(unit['txt_id'], unit['unit_id'], x, y))
    return runes


def ground_uniques(read, table_address, *, minimum: float) -> list[GroundUnique]:
    """Unique- and set-quality ground items whose base has such an item asking `minimum` Ist or more."""
    heads = struct.unpack('<128Q', read(table_address + ITEM_UNIT * 1024, 1024))
    uniques = []
    for unit in walk_units(read, heads, ITEM_UNIT)['units']:
        if unit['mode'] not in GROUND_MODES or unit['txt_id'] not in BASES:
            continue
        try:
            data = read(unit['data_pointer'], ITEM_DATA_SIZE)
            x, y = static_position(read, unit)
        except OSError, ValueError:
            continue
        quality = struct.unpack_from('<I', data, QUALITY_OFFSET)[0]
        table_id = struct.unpack_from('<I', data, IDENTITY_OFFSET)[0]
        identified = bool(struct.unpack_from('<I', data, FLAGS_OFFSET)[0] & IDENTIFIED_FLAG)
        label = unique_drop(unit['txt_id'], minimum=minimum, table_id=table_id, identified=identified, quality=quality)
        if label is not None:
            uniques.append(GroundUnique(label, unit['unit_id'], x, y, table_id))
    return uniques


def observe_ground(
    pid,
    images,
    capture,
    *,
    minimum: str,
    shrine_types: frozenset[int],
    super_chests: bool = True,
    unique_minimum: float | None = None,
) -> tuple[Location | None, list[GroundRune], list[GroundUnique | Shrine | SuperChest]]:
    """(location, valuable runes, marked spots: expensive uniques, wanted shrines, then super chests)."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, process_mappings(pid)).read
        table = next(iter(tables))
        location = player_location(read, table)
        runes = ground_runes(read, table, minimum=minimum) if location else []
        shrines = nearby_shrines(read, table, types=shrine_types) if location and shrine_types else []
        chests = nearby_super_chests(read, table) if location and super_chests else []
        uniques = ground_uniques(read, table, minimum=unique_minimum) if location and unique_minimum is not None else []
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the ground read')
    return location, runes, [*uniques, *shrines, *chests]
