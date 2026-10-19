"""Valuable runes, materials (loot/materials.py) and expensive uniques on the ground, from streamed
item units (only items near the player exist).

A look walks the item table once (game/units.py) and reads each ground item's place and data once (`on_ground`);
the classifiers (`runes_among`, `materials_among`, `shown_among`, `uniques_among`, `sightings_among`) are pure
functions of those rows. Each `ground_*` function is one of them over a walk of its own.

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

import struct
from contextlib import suppress
from dataclasses import dataclass, field
from typing import ClassVar

from inventory_tracking.game.units import walked
from inventory_tracking.items.identity import (
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
)
from inventory_tracking.levels.memory import player_location
from inventory_tracking.levels.model import Location
from inventory_tracking.loot.materials import appraised_classes
from inventory_tracking.loot.runes import is_valuable_rune
from inventory_tracking.loot.shown import filter_rules, hides, shown_label
from inventory_tracking.loot.shrines import SHRINE_NAMES
from inventory_tracking.loot.uniques import BASES, unique_drop
from inventory_tracking.native.layout import OBJECT_SHRINE_TABLE, OBJECT_SHRINE_TYPE
from inventory_tracking.native.memory import game_read


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
class GroundMaterial:
    label: str
    unit_id: int
    x: int
    y: int
    quality: int = field(default=0, compare=False)  # ItemData quality as read; 0 when not read


@dataclass(frozen=True)
class ItemSighting:
    """An item unit of a watched class, wherever it is: on the ground, carried or stored."""

    class_id: int
    unit_id: int
    mode: int
    x: int  # static path position: where it lies, for a ground item
    y: int


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
    label: ClassVar[str] = 'Super chest'


def static_position(read, unit):
    path = read(unit['path_pointer'], 0x18)
    return struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF


def nearby_super_chests(read, table_address) -> list[SuperChest]:
    """Closed glowing chests among the streamed object units."""
    chests = []
    for unit in walked(read, table_address, OBJECT_UNIT)['units']:
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
    shrines = []
    for unit in walked(read, table_address, OBJECT_UNIT)['units']:
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


def item_units(read, table_address, class_ids) -> list[ItemSighting]:
    """Every streamed item unit of the given classes (terror/shards.py tells drops from carried ones)."""
    found = []
    for unit in walked(read, table_address, ITEM_UNIT)['units']:
        if unit['txt_id'] not in class_ids:
            continue
        try:
            x, y = static_position(read, unit) if unit['path_pointer'] else (0, 0)
        except OSError, ValueError:
            continue
        found.append(ItemSighting(unit['txt_id'], unit['unit_id'], unit['mode'], x, y))
    return found


@dataclass(frozen=True)
class GroundItem:
    """An item unit on the ground or dropping (GROUND_MODES) and what one look read of it, once for every
    classifier below: its static path position and its ItemData's (quality, flags, table index at +0x34). Either
    is None when the unit has no pointer to it or the read failed; the classifiers tell the two apart by the
    unit's pointer where they treat them apart (`materials_among`)."""

    unit: dict  # the walk's row (native/units.py `walk_units`)
    at: tuple[int, int] | None
    data: tuple[int, int, int] | None

    @property
    def txt(self) -> int:
        return self.unit['txt_id']

    @property
    def unit_id(self) -> int:
        return self.unit['unit_id']


def on_ground(read, units) -> list[GroundItem]:
    """The walked item units on the ground or dropping, in the walk's order, each read once (`GroundItem`)."""
    found = []
    for unit in units:
        if unit['mode'] not in GROUND_MODES:
            continue
        at = data = None
        if unit['path_pointer']:
            with suppress(OSError, ValueError):
                at = static_position(read, unit)
        if unit['data_pointer']:
            with suppress(OSError, ValueError):
                raw = read(unit['data_pointer'], ITEM_DATA_SIZE)
                fields = (QUALITY_OFFSET, FLAGS_OFFSET, IDENTITY_OFFSET)
                quality, flags, table_id = (struct.unpack_from('<I', raw, offset)[0] for offset in fields)
                data = (quality, flags, table_id)
        found.append(GroundItem(unit, at, data))
    return found


def runes_among(ground: list[GroundItem], *, minimum: str) -> list[GroundRune]:
    """The valuable runes (loot/runes.py) whose place was read."""
    return [
        GroundRune(item.txt, item.unit_id, *item.at)
        for item in ground
        if item.at is not None and is_valuable_rune(item.txt, minimum=minimum)
    ]


def materials_among(ground: list[GroundItem], classes: dict[int, str], appraised=frozenset()) -> list[GroundMaterial]:
    """Ground items of the given classes (class ID -> label, loot/materials.py). Of the `appraised`
    classes only the unidentified ones: an identified charm on the ground is one the player read and
    dropped (an item whose flags cannot be read counts as unidentified). One with no path lies at (0, 0);
    one whose path is unread is left out; one whose data is unread has quality 0."""
    found = []
    for item in ground:
        if item.txt not in classes:
            continue
        at = item.at if item.unit['path_pointer'] else (0, 0)
        if at is None:
            continue
        # The quality for the pickup mode's rare rings (macros/pickmode.py), the flags for the appraised classes
        quality, flags, _ = item.data or (0, 0, 0)
        if item.txt in appraised and flags & IDENTIFIED_FLAG:
            continue
        found.append(GroundMaterial(classes[item.txt], item.unit_id, *at, quality))
    return found


def shown_among(ground: list[GroundItem], rules) -> list[GroundMaterial]:
    """Ground items a rule of the loot filter shows (loot/shown.py `pickup_rules`), read whole."""
    classes = frozenset().union(*(rule.classes for rule in rules))
    found = []
    for item in ground:
        if item.txt not in classes or item.at is None or item.data is None:
            continue
        quality, flags, _ = item.data
        label = shown_label(rules, item.txt, quality, flags)
        if label is not None:
            found.append(GroundMaterial(label, item.unit_id, *item.at, quality))
    return found


def uniques_among(ground: list[GroundItem], *, minimum: float, rules=None) -> list[GroundUnique]:
    """Unique- and set-quality ground items whose base has such an item asking `minimum` Ist or more.

    Not one the loot filter hides (`rules`, loot/shown.py; the filter's own by default): the filter
    goes by sales and the mark by asks, and a mark on a drop without a label points at nothing to click
    (user, 2026-10-12: Tarnhelm asked 2.58 Ist on 2026-09-18 and sold at a median of 0.20 on 2026-10-09)."""
    rules = filter_rules() if rules is None else rules
    uniques = []
    for item in ground:
        if item.txt not in BASES or item.at is None or item.data is None:
            continue
        quality, flags, table_id = item.data
        if hides(rules, item.txt, quality):
            continue
        identified = bool(flags & IDENTIFIED_FLAG)
        label = unique_drop(item.txt, minimum=minimum, table_id=table_id, identified=identified, quality=quality)
        if label is not None:
            uniques.append(GroundUnique(label, item.unit_id, *item.at, table_id))
    return uniques


def sightings_among(ground: list[GroundItem], class_ids) -> list[ItemSighting]:
    """The ground items of the given classes as `item_units` sees them: one with no path at (0, 0), one whose path
    is unread left out."""
    found = []
    for item in ground:
        at = item.at if item.unit['path_pointer'] else (0, 0)
        if item.txt in class_ids and at is not None:
            found.append(ItemSighting(item.txt, item.unit_id, item.unit['mode'], *at))
    return found


def ground_items(read, table_address) -> list[GroundItem]:
    """`on_ground` of a walk of its own of the item table."""
    return on_ground(read, walked(read, table_address, ITEM_UNIT)['units'])


def ground_runes(read, table_address, *, minimum: str) -> list[GroundRune]:
    return runes_among(ground_items(read, table_address), minimum=minimum)


def ground_materials(read, table_address, classes: dict[int, str], appraised=frozenset()) -> list[GroundMaterial]:
    """`materials_among` of a walk of its own."""
    return materials_among(ground_items(read, table_address), classes, appraised)


def ground_shown(read, table_address, rules) -> list[GroundMaterial]:
    """`shown_among` of a walk of its own."""
    return shown_among(ground_items(read, table_address), rules)


def ground_uniques(read, table_address, *, minimum: float, rules=None) -> list[GroundUnique]:
    """`uniques_among` of a walk of its own."""
    return uniques_among(ground_items(read, table_address), minimum=minimum, rules=rules)


def observe_ground(
    pid,
    images,
    capture,
    *,
    minimum: str,
    shrine_types: frozenset[int],
    super_chests: bool = True,
    unique_minimum: float | None = None,
    materials: dict[int, str] | None = None,
) -> tuple[Location | None, list[GroundRune], list[GroundUnique | GroundMaterial | Shrine | SuperChest]]:
    """(location, valuable runes, marked spots: expensive uniques, materials, wanted shrines, then super chests)."""
    with game_read(pid, images, capture, changed='Game process changed during the ground read') as (read, table):
        location = player_location(read, table)
        ground = ground_items(read, table) if location else []
        runes = runes_among(ground, minimum=minimum)
        shrines = nearby_shrines(read, table, types=shrine_types) if location and shrine_types else []
        chests = nearby_super_chests(read, table) if location and super_chests else []
        uniques = uniques_among(ground, minimum=unique_minimum) if location and unique_minimum is not None else []
        found = materials_among(ground, materials, appraised_classes()) if location and materials else []
    return location, runes, [*uniques, *found, *shrines, *chests]
