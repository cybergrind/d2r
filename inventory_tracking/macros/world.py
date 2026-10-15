"""What a macro may ask about the game, read fresh from memory in one pass.

Image addresses found with the record probe on 2026-10-06 (plan.md, findings): the skill slot
table, the game name and the in-game byte. The unit table is the one the service attached to;
it stays at the same address through the lobby and into the next game.
"""

import contextlib
import functools
import json
import math
import os
import re
import struct
import threading
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path

from inventory_tracking.collection.capture import read_owner_grids
from inventory_tracking.common import LOG
from inventory_tracking.config import RESOURCE_READER
from inventory_tracking.items.metadata import item_base
from inventory_tracking.levels.doors import Door, door_sizes
from inventory_tracking.levels.memory import WAYPOINT_CLASSES, pointer
from inventory_tracking.levels.model import CLICKED, PORTAL, TOWN_PORTAL, WIRTS_BODY
from inventory_tracking.loot.ground import (
    GROUND_MODES,
    ground_materials,
    ground_runes,
    ground_shown,
    ground_uniques,
    item_units,
    static_position,
)
from inventory_tracking.loot.materials import appraised_classes
from inventory_tracking.loot.runes import is_valuable_rune, rune_name
from inventory_tracking.loot.shown import NAMED_QUALITIES, ShownRule
from inventory_tracking.native.layout import (
    BELT_ITEM_MODE,
    BELT_SIZE,
    CHARGED_SKILL_STAT,
    DEAD_MODES,
    LEVEL_AREA_ID,
    LIFE_STAT,
    MAX_LIFE_STAT,
    PANEL_FLAGS,
    PATH_ROOM1,
    PLAYER_DEAD_MODES,
    ROOM1_ROOM2,
    ROOM2_LEVEL,
    STAFF_CLASS_IDS,
    TELEPORT_SKILL,
    TERROR_SERVICE_RVA,
    TOWN_IDS,
    UI_PANELS_RVA,
    UI_PANELS_SIZE,
    WEAPON_SLOTS,
)
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import read_stats, walk_units
from inventory_tracking.tracking.belt import BeltColumns, remember
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
# (unit type, unit id) of the unit under the pointer: the one address the whole-data search found holding
# the item's pair on each of the pickup step's first five clicks (host, 18:46-18:54 on 2026-10-10), on
# three levels and two games. What it holds with nothing under the pointer is not known.
HOVER_RVA = 0x1E010A4
IN_GAME = 0x00  # byte of the panel array: 1 in a game, 0 from Save and Exit to the next game
MONSTER_OWNER = 84  # monster data u32[21]: the owning player's unit id (native/mercenary.py)
MONSTER_DATA = 0x58  # monster data bytes read per live monster: the type flags and the owner lie within
NO_OWNER = 0xFFFFFFFF
# Monster data byte +0x1A (terror/tracker.py, probe logs 2026-10-02/03): 0x08 unique (Heralds too),
# 0x04 champion, 0x02 super unique, 0x10 a minion of one of those.
TYPE_FLAGS = 0x1A
# Monster data bytes from +0x20: its special modifiers (monumod ids; 0 = none), the enchantments of a
# unique and what its minions inherit (terror/tracker.py FIRST_MODIFIER, MODIFIER_SLOTS).
MODIFIERS = slice(0x20, 0x29)
LEADER_FLAGS = 0x02 | 0x04 | 0x08
MINION_FLAG = 0x10
HERALD_TIER_STAT = 367  # itemstatcost `heraldtier`: on a Terror Zone's Herald and on its minions (terror/tracker.py)
ALIGNMENT_STAT = 172  # non-zero on allies: summons, the mercenary (terror/tracker.py)
# A unit's skill list (third-parties/d2go memory/player.go; the Defiler dump of 2026-10-09 holds a heap
# pointer there): pointers to the skill records on the left and right mouse button, each starting
# with a pointer to its skills.txt record, whose first u16 is the skill id.
SKILL_LIST = 0x100
LEFT_SKILL, RIGHT_SKILL = 0x08, 0x10
MONSTER_UNIT = 1
OBJECT_UNIT = 2  # doors among the objects (levels/doors.py)
OBJECT_PATH = 0x18  # an object's static path: x at 0x10, y at 0x14 (loot/ground.py static_position)
MISSILE_UNIT = 3  # blades and bolts in flight (combat/record.py dumps them raw: layout research)
# The unit hash table has twelve slots of 128 heads (MapAssist UnitType): the client's six, then the
# "server" six; the player's own missiles hang off the server missile slot, other units' off the
# client one (MapAssist GameMemory.cs: Missile and ServerMissile both hold type 3 units). The first
# Chaos Sanctuary take (2026-10-09) found slot 3 empty through 237 casts.
MISSILE_SLOTS = (3, 9)
UNIT_SLOTS = 12
MISSILE_RECORD = 0x160  # bytes of a missile unit record dumped
MISSILE_PATH = 0x30  # bytes of its path record dumped
# A monster's whole path record, for the movement research (combat/plan.md): after the position come
# the target point (0x10, 0x12), the waypoint count (0x34), the target unit (0x70) and, by the classic
# layout, the waypoints near 0xC8 (read from the client's code 2026-10-11; not yet checked live).
PATH_RECORD = 0x240
MISSILE_DATA = 0x80  # bytes of its data record (pUnitData) dumped on first sight: skill, velocity, target?
# A missile unit record's owner: its unit type, then its unit id (tests/.../arena/evidence/blows.py OWNER: 1,771 of
# 1,866 records of take 20261012T065226Z-130 hold a unit id of the take there and nowhere else).
MISSILE_OWNER = 0xE8
DATA_RVA, DATA_SIZE = 0x197A000, 0xC98000  # the image's writable data (record probe)
ITEM_UNIT = 4
TILE_UNIT = 5  # doors: warp tiles, with a static path like an object's
FULL_STATS = 0xE8  # the unit's full stat list (native/units.py describe_player)
EQUIPPED_MODE = 1
ITEM_OWNER, ITEM_BODY_LOCATION = 0x0C, 0x54  # item data (native/units.py describe_item)
# The weapon set in hand; the other set sits at 11 and 12 (config.py: staff 4 -> 11 on swap).
HANDS = frozenset((4, 5))
# An item's full stat list, where a staff's charged skills are (tracking/resources.py select_teleport).
TELEPORT_STATS = RESOURCE_READER.teleport_stats_offset
DEFILER_CLASS = 744
# The state bits of a unit, 32 to a word: tracking/consume.py reads state 208 (states.txt `consume`)
# as bit 16 of this word, so it holds states 192-223, and state 202 (`hexpurge`, the aurastate of skill
# 389) is its bit 10. Read from the tables on 2026-10-11; not yet seen to change in the game.
STATE_FLAGS = 0xB48
# Every state word of a unit, as that reading has them laid out: states 0-31 in the first word, six
# words before STATE_FLAGS, to 224-255 in the one after it. Only the word at STATE_FLAGS is confirmed;
# the recorder writes the whole run raw (combat/record.py `s`), for a curse on the character
# (states.txt `amplifydamage` 9, `ironmaiden` 55, `decrepify` 60, `lowerresist` 61), poison (2) and a
# skill's delay to be read off it once a take shows them change.
STATE_RUN = (STATE_FLAGS - 6 * 4, 8 * 4)
TICK_HEAD = 0x20
HEX_PURGE_BIT = 1 << (202 - 192)
PSYCHIC_WARD_BIT = 1 << (206 - 192)  # states.txt `psychicward`, the aurastate of skill 387
# State 185 `cooldown`, in the word before STATE_FLAGS (states 160-191): the character's casting delay. Set at
# a delayed skill's action frame and cleared when its delay is over: for Blade Warp 0.20 s after the key and
# 0.80 s long, 64 warps of 64 in the take of 12:33 on 2026-10-13 (rca/2026-10-13/run-1233-findings.md §3).
# Read with STATE_FLAGS in one read.
COOLDOWN_BIT = 1 << (185 - 160)
LYING_DEAD = 12  # monster mode: dead, the death animation (mode 0) over
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
    consume_node: bytes = field(default=b'', compare=False, repr=False)  # research: the buff's record
    left_skill: int | None = None  # the skill on the left mouse button; None when unreadable
    right_skill: int | None = None
    stats_at: int = field(
        default=0, compare=False, repr=False
    )  # the unit's stat list (combat/record.py reads life and mana)
    hex_purge: bool | None = None  # the Hex: Purge buff is on the character; None when unreadable
    ward: bool | None = None  # Psychic Ward likewise
    record: bytes = field(default=b'', compare=False, repr=False)  # the unit record as read (research)
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw (`skill_in_use`)
    # A casting delay runs on the character (state 185, COOLDOWN_BIT): the next delayed skill's key is
    # refused until it clears. None when unreadable (macros/travel.py then times the delay by the clock).
    cooldown: bool | None = field(default=None, compare=False)

    @property
    def in_town(self) -> bool:
        return self.area in TOWN_IDS

    @property
    def buffs(self) -> tuple[bool | None, ...]:
        """The buffs this reader knows of, in the order the combat recorder writes them (record.py `f`):
        Psychic Ward, Hex: Purge, Consume; None for one that could not be read."""
        return (self.ward, self.hex_purge, self.consume)


@dataclass(frozen=True)
class Monster:
    unit_id: int
    txt_id: int
    mode: int
    x: float
    y: float
    owner: int
    flags: int = 0  # type flags (TYPE_FLAGS byte)
    ally: bool = False  # alignment stat set: a summon or the mercenary
    life: int = 0  # whole points (stats 6 and 7); 0 when the stats were unreadable
    max_life: int = 0
    raw: bytes = field(default=b'', compare=False, repr=False)  # unit and monster data, Defilers only
    stats_at: int = field(default=0, compare=False, repr=False)  # the unit's stat list, for a full read
    path: bytes = field(default=b'', compare=False, repr=False)  # the whole path record, on request (PATH_RECORD)
    modifiers: tuple[int, ...] = field(default=(), compare=False)  # monumod ids: Lightning Enchanted is 17
    tier: int = field(default=0, compare=False)  # the tier of the Herald it is or follows (stat 367); 0: none
    # On request (`records`): the unit record and the monster data as this walk read them, for the fields
    # nobody has named yet (the animation frame, the skill in use: combat/record.py `records.jsonl`).
    record: bytes = field(default=b'', compare=False, repr=False)
    states: bytes = field(default=b'', compare=False, repr=False)  # its state words (STATE_RUN), with `records`
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw, in a striking mode

    @property
    def leader(self) -> bool:
        """A unique, champion or super unique: what the seek step hunts (macros/hunt.py); minions are not."""
        return bool(self.flags & LEADER_FLAGS) and not self.flags & MINION_FLAG


# The only rejuvenation potion worth a belt cell (user, 2026-10-10: "we need a full rejuv potion
# instead"); a plain one (530) lay where fourteen clicks could not take it (host, 19:37).
FULL_REJUVENATION = 531
# The only healing potion worth one (user, 2026-10-10: "only super hp or full rejuv"): the smaller sizes
# were gone for, and the loot filter hides them, so no click took them (host, 20:12 and 20:13).
SUPER_HEALING = 606
VALUABLE, HEALING, REJUVENATION = 'valuable', 'healing', 'rejuvenation'  # what a drop is to the pickup step
GOLD = 'gold'  # a pile the character takes by standing on it: gone to, never clicked
GOLD_CLASS = 538  # misc.txt `gld` (items/data/item_metadata.json bases)
GOLD_STAT = 14  # itemstatcost.txt `gold`: a pile's amount
BASE_STATS = 0x30  # the unit's own stat list (terror/monsters.py)
GOLD_SEEN: dict[int, int] = {}  # unit id -> amount, of the piles read


@dataclass(frozen=True)
class Drop:
    """An item on the ground worth a walk: one the loot marks point at, or a potion the belt may want."""

    unit_id: int
    x: float  # world units
    y: float
    label: str
    kind: str  # VALUABLE, GOLD, HEALING or REJUVENATION
    size: tuple[int, int] = (1, 1)  # cells across and down it takes in the inventory (loot/data/sizes.json)
    # One the loot marks point at (`prized`): with no room for it the pickup press stops; for the rest it
    # warns and goes on. True unless the read says otherwise: a drop of unknown worth stops the press.
    prized: bool = True


# The source of a unique or set item the loot filter shows (unidentified, or of any size): one a full inventory
# stops for, as for what the marks point at (the player, 2026-10-14: run-1214-findings.md §3.1).
NAMED = 'named'


def prized(source: str, *, marked: bool) -> bool:
    """Whether a drop is one a full inventory stops the pickup press for, and a level run stands by (user,
    2026-10-12: "allow moving when the item isn't very valuable"): what the loot marks point at — a rune from the
    marks' minimum up, a unique or set item worth a mark, a material of the marks — and every unique or set item
    the loot filter shows (`NAMED`, the player's ruling of 2026-10-14: the run walked past a Unique Plate Mail
    with the inventory full and the player fetched it by hand, rca/2026-10-14/run-1214-findings.md §3.1). Not
    what the pickup takes besides: the low runes, every ring and jewel, the gems and the magic, rare and white
    equipment the loot filter shows."""
    return source in ('unique', NAMED) or (source in ('rune', 'material') and marked)


def shown_source(quality: int) -> str:
    """The source (`prized`) of a ground item the loot filter shows, by its quality: a unique or set one is
    `NAMED`, the rest (magic, rare, white and gray) 'shown'."""
    return NAMED if quality in NAMED_QUALITIES else 'shown'


@dataclass(frozen=True)
class Loot:
    """What the pickup step decides on (macros/pickup.py): the drops near the character, its belt and its life."""

    drops: tuple[Drop, ...] = ()
    belt: tuple[int | None, ...] = (None,) * BELT_SIZE  # item class by cell; the first four are the hotkey row
    life: int = 0  # whole points; 0 when unreadable
    max_life: int = 0
    # The inventory's rows, '.' a free cell and '#' a taken one (collection/capture.py grids); None: unread.
    room: tuple[str, ...] | None = None
    stats: tuple[tuple[int, int], ...] = ()  # current set's full stats, already read with life
    game: tuple[str, int] | None = None  # (game name, the character's unit id) the belt is of; None: unread
    # What each belt column last held this game (tracking/belt.py `BeltColumns`), as the runner keeps it
    # (`BeltKept`): an emptied healing column stays one; None: the belt alone decides.
    columns: BeltColumns | None = None
    # The Horadric Cube's rows as `room` has the inventory's (grid 5, 3x4: rca/2026-10-13/pickup-cube.md §3); read
    # with the panels closed, wherever the cube is. None: unread, or no cube. Not yet a place the pickup puts
    # anything (that is the cube work of pickup-cube.md §6): it is said where a drop has no room in the inventory.
    cube: tuple[str, ...] | None = None
    # The drops (unit ids) taken only because the loot filter shows them (loot/shown.py): magic, rare and white
    # equipment nothing the marks or the pickup's own rules name. A level run does not stand by one for want of room
    # (the player, 2026-10-12: "allow moving when the item isn't very valuable"). A unique or set one the filter shows
    # is not among them: it is prized (`NAMED`, the player, 2026-10-14).
    shown: frozenset[int] = frozenset()
    # The unit ids of the items in the character's grids now (the inventory, the cube, the stash tabs: `held_items`),
    # read with `room`: what `PutDown` knows the player's own items by.
    carried: frozenset[int] = frozenset()
    # (unit id, item class: the game's classid) of the drops whose class was read: what `PutDown` knows an item by
    # once the game has given it a new unit id
    classes: tuple[tuple[int, int], ...] = ()


class BeltKept:
    """The belt's history across the presses of a runner: `see` folds a look at the belt into it
    (tracking/belt.py `remember`) and hands the loot on with it. A loot of no known game is passed as read."""

    def __init__(self) -> None:
        self.columns = BeltColumns()

    def see(self, loot: Loot) -> Loot:
        if loot.game is None:
            return loot
        self.columns = remember(self.columns, loot.belt, loot.game)
        return replace(loot, columns=self.columns)


class PutDown:
    """The items the player put down this game, kept across the presses of a runner as `BeltKept` keeps the
    belt: a ground item whose unit id the character carried this game (`Loot.carried`) was put down by the
    player, who has looked at it, and is not the macro's to pick up, stand by or warn about again (the player,
    2026-10-14: "we tried to pickup crystal sword that I've checked and dropped"; rca/2026-10-14/run-0025-findings.md
    §3, P1). The game streams it out and back in with a new unit id at the same place (00:29:04.9 and 00:30:35.9
    that game), so it is remembered by its class and place, within NEAR, for the rest of the game. `see` takes it
    out of a look's drops, so no reader of the loot names it (`choose`, a level run's side drop, `stay_by`,
    `worth_a_stop`, the "Inventory full" warning); `at` answers the HUD's ground marks (loot/watch.py). Said once a
    place. A drop the player wants back is picked up by hand. A loot of no known game is passed as read; the
    next game forgets. Read by the runner's thread and the service's, hence the lock."""

    NEAR = 1.0  # world units: the same place (an item's position is whole units)
    KEPT = 4000  # the carried unit ids kept at most in a game (a full stash and inventory hold under 600 items)

    def __init__(self) -> None:
        self.game: tuple[str, int] | None = None
        self.carried: set[int] = set()
        self.places: list[tuple[int | None, float, float]] = []  # (class, x, y) of each item put down
        self.lock = threading.Lock()

    def see(self, loot: Loot) -> Loot:
        if loot.game is None:
            return loot
        with self.lock:
            if loot.game != self.game:
                self.game, self.carried, self.places = loot.game, set(), []
            if len(self.carried) > self.KEPT:
                self.carried.clear()
            # The drops are tested against the items carried in earlier looks only: one `Loot` reads the drops
            # first and the grids last, so an item the macro picks up between the two is in both
            # (rca/2026-10-14/run-0305-findings.md §5.3: the Amulet "put down" while it was being picked up).
            kinds = dict(loot.classes)
            kept = []
            for drop in loot.drops:
                kind = kinds.get(drop.unit_id)
                if self._at(drop.x, drop.y, kind):
                    continue
                if drop.unit_id in self.carried:
                    self.places.append((kind, drop.x, drop.y))
                    LOG.info(
                        'Macro: put down: %s at (%.0f, %.0f), unit %d, was carried this game: the player put it '
                        'down; not picked up, stood by or warned about again this game',
                        drop.label, drop.x, drop.y, drop.unit_id,
                    )  # fmt: skip
                    continue
                kept.append(drop)
            self.carried |= loot.carried
        return loot if len(kept) == len(loot.drops) else replace(loot, drops=tuple(kept))

    def at(self, x: float, y: float, class_id: int | None = None) -> bool:
        """Whether an item the player put down this game lies at (x, y): of `class_id`, or of any class (None)."""
        with self.lock:
            return self._at(x, y, class_id)

    def _at(self, x: float, y: float, class_id: int | None) -> bool:
        return any(
            math.dist((x, y), (px, py)) <= self.NEAR and (class_id is None or kind is None or kind == class_id)
            for kind, px, py in self.places
        )


@dataclass(frozen=True)
class Teleport:
    """A staff with Teleport charges the character wears, in the set in hand or the other one."""

    charges: int
    maximum: int
    in_hand: bool


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
    doors: tuple[Door, ...] = ()  # door objects streamed around the character, open or closed
    dead: frozenset[int] = frozenset()  # unit ids of the monsters lying dead (a kill, where a unit only gone is not)

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


def plausible_life(read, stats_pointer: int) -> bool:
    """Whether the unit's full stat list holds a life within a positive maximum (tracking/state.py)."""
    try:
        stats = read_stats(read, stats_pointer + FULL_STATS)
    except OSError, ValueError, struct.error:
        return False
    life = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == LIFE_STAT]
    most = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == MAX_LIFE_STAT]
    return len(life) == len(most) == 1 and 0 <= life[0] <= most[0] and most[0] > 0


# Monster modes in which it strikes or casts (monmode.txt: A1 4, A2 5, the cast 7, S1-S4 8-11).
STRIKING_MODES = frozenset((4, 5, 7, 8, 9, 10, 11))
SKILL_IN_USE = 0x18  # in the skill list: the pointer to the skill being used
SKILL_RECORD = 0x50  # bytes of the skill record kept: its row pointer first, the points and base level within


def skill_in_use(read, record: bytes) -> bytes:
    """The skill a unit is using, raw: the two bytes its skills.txt row begins with (the skill id) and
    the skill record's first SKILL_RECORD bytes. From the client's code (rca/2026-10-13/re-findings.md),
    not yet seen to hold in a game: kept raw for that reason. Empty when any of the three reads fails."""
    try:
        skills = struct.unpack_from('<Q', record, SKILL_LIST)[0]
        used = struct.unpack('<Q', read(skills + SKILL_IN_USE, 8))[0] if skills else 0
        if not used:
            return b''
        kept = read(used, SKILL_RECORD)
        row = struct.unpack_from('<Q', kept)[0]
        return (read(row, 2) if row else b'\0\0') + kept
    except OSError, ValueError, struct.error:
        return b''


def monsters(
    read, table: int, *, dead: bool = False, paths: bool = False, records: bool = False
) -> tuple[Monster, ...]:
    """The live monsters with a position: type flags and owner from the monster data, ally by the
    alignment stat (unreadable stats: not an ally). Dead ones (unless `dead`) and those without a
    path are left out. `paths`: each with its whole path record, where it can be read to its end."""
    return monsters_and_dead(read, table, dead=dead, paths=paths, records=records)[0]


def monsters_and_dead(
    read, table: int, *, dead: bool = False, paths: bool = False, records: bool = False
) -> tuple[tuple[Monster, ...], frozenset[int]]:
    """`monsters`, and the unit ids of the monsters lying dead (from the same walk of the unit table)."""
    heads = struct.unpack('<128Q', read(table + MONSTER_UNIT * 1024, 1024))
    found = []
    corpses = set()
    for unit in walk_units(read, heads, MONSTER_UNIT, records=records)['units']:
        if unit['mode'] in DEAD_MODES:
            corpses.add(unit['unit_id'])
        if (unit['mode'] in DEAD_MODES and not dead) or not unit['path_pointer'] or not unit['data_pointer']:
            continue
        record = b''
        if paths:
            with contextlib.suppress(OSError, ValueError):
                record = read(unit['path_pointer'], PATH_RECORD)
        try:
            path = record[:8] or read(unit['path_pointer'], 8)
            data = read(unit['data_pointer'], MONSTER_DATA)
        except OSError, ValueError:
            continue
        owner = struct.unpack_from('<I', data, MONSTER_OWNER)[0]
        ally, life, max_life, tier = False, 0, 0, 0
        if unit['stats_pointer']:
            with contextlib.suppress(OSError, ValueError, struct.error):
                full = read_stats(read, unit['stats_pointer'] + FULL_STATS)
                stats = {s['id']: s['raw'] for s in full if s['layer'] == 0}
                ally = bool(stats.get(ALIGNMENT_STAT))
                tier = stats.get(HERALD_TIER_STAT, 0)
                life, max_life = stats.get(LIFE_STAT, 0) >> 8, stats.get(MAX_LIFE_STAT, 0) >> 8
        raw = b''
        if unit['txt_id'] == DEFILER_CLASS:
            with contextlib.suppress(OSError, ValueError):
                raw = read(unit['address'], 0x160) + read(unit['data_pointer'], 0x80)
        monster = Monster(unit['unit_id'], unit['txt_id'], unit['mode'], *position(path), owner, data[TYPE_FLAGS])
        monster = replace(monster, ally=ally, life=life, max_life=max_life, raw=raw, stats_at=unit['stats_pointer'])
        whole = states = skill = b''
        if records:
            whole = unit.get('record', b'') + data
            if unit['stats_pointer']:
                with contextlib.suppress(OSError, ValueError):
                    states = read(unit['stats_pointer'] + STATE_RUN[0], STATE_RUN[1])
            if unit['mode'] in STRIKING_MODES:
                skill = skill_in_use(read, unit.get('record', b''))
        monster = replace(monster, path=record, modifiers=tuple(mod for mod in data[MODIFIERS] if mod), tier=tier)
        found.append(replace(monster, record=whole, states=states, skill=skill))
    return tuple(found), frozenset(corpses)


def corpses(read, table: int) -> tuple[tuple[int, float, float], ...]:
    """The monsters lying dead (mode 12, the death animation over) as (unit id, x, y), world units.
    Its own walk of the unit table: asked for now and then (Engorge), not at every look at the world."""
    heads = struct.unpack('<128Q', read(table + MONSTER_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, MONSTER_UNIT)['units']:
        if unit['mode'] != LYING_DEAD or not unit['path_pointer']:
            continue
        with contextlib.suppress(OSError, ValueError):
            found.append((unit['unit_id'], *position(read(unit['path_pointer'], 8))))
    return tuple(found)


INVENTORY_GRID = 2  # the carried inventory among a player's grids (collection/capture.py GRID_CONTAINERS)
CUBE_GRID = 5  # the Horadric Cube's (the same table)


@functools.cache
def item_sizes() -> dict[int, tuple[int, int]]:
    table = json.loads((Path(__file__).parents[1] / 'loot' / 'data' / 'sizes.json').read_text())
    return {int(class_id): (size[0], size[1]) for class_id, size in table['sizes'].items()}


def item_size(class_id: int | None) -> tuple[int, int]:
    """Inventory cells (across, down) of an item class; one cell when the class is not known."""
    return item_sizes().get(class_id, (1, 1)) if class_id is not None else (1, 1)


def carried_rows(
    read, table: int, player_id: int
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None, frozenset[int]]:
    """The rows of the carried inventory and of the Horadric Cube, '.' a free cell, and the item pointers of all
    the character's grids (`held_items`), from one read of them; the rows None when they cannot be read (no cube:
    no grid of it)."""
    try:
        heads = struct.unpack('<128Q', read(table, 1024))
        unit = next((u for u in walk_units(read, heads, 0)['units'] if u['unit_id'] == player_id), None)
        grids = read_owner_grids(read, unit) if unit is not None else {}
    except OSError, ValueError, struct.error:
        return None, None, frozenset()
    return grid_rows(grids.get(INVENTORY_GRID)), grid_rows(grids.get(CUBE_GRID)), held_items(grids)


def held_items(grids: dict) -> frozenset[int]:
    """The item pointers in a unit's grids (collection/capture.py `read_owner_grids`: a cell holds the item lying
    on it): what the character carries in its inventory, its cube and its stash tabs."""
    return frozenset(cell for grid in grids.values() for cell in grid['cells'] if cell)


def grid_rows(grid: dict | None) -> tuple[str, ...] | None:
    """A grid's rows, '#' a taken cell and '.' a free one; None for no grid."""
    if grid is None:
        return None
    width, cells = grid['width'], grid['cells']
    return tuple(''.join('#' if cells[y * width + x] else '.' for x in range(width)) for y in range(grid['height']))


def has_room(rows: tuple[str, ...] | None, size: tuple[int, int]) -> bool:
    """Whether a free block of `size` cells is left in the rows; True when they were not read."""
    if rows is None:
        return True
    across, down = size
    return any(
        all(rows[y + dy][x + dx] == '.' for dy in range(down) for dx in range(across))
        for y in range(len(rows) - down + 1)
        for x in range(len(rows[0]) - across + 1)
    )


def doors(read, table: int) -> tuple[Door, ...]:
    """The door objects among the streamed object units, with their mode (closed or opened)."""
    heads = struct.unpack('<128Q', read(table + OBJECT_UNIT * 1024, 1024))
    sizes = door_sizes()
    found = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] not in sizes or not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        found.append(Door(unit['unit_id'], unit['txt_id'], unit['mode'], float(x), float(y)))
    return tuple(found)


@dataclass(frozen=True)
class Warp:
    """A door: a warp tile unit of the loaded rooms."""

    unit_id: int
    warp: int  # its lvlwarp Id (levels/presets.warp_box)
    x: float  # world units: what the door's click box hangs from
    y: float


def warps(read, table: int) -> tuple[Warp, ...]:
    """The doors among the streamed units. Seen on 2026-10-10 in the Forgotten Tower: the way out
    (Id 11) and the stairs down (Id 12), with the two doors of the levels just left still listed."""
    heads = struct.unpack('<128Q', read(table + TILE_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, TILE_UNIT)['units']:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        found.append(Warp(unit['unit_id'], unit['txt_id'], float(x), float(y)))
    return tuple(found)


# The objects a level's mark may name for a click (levels/model.py), the town portal the character opens
# (macros/portal.py) and the waypoints (macros/waypoint.py): each has its `Use` in macros/teleport.py. The combat
# recorder writes them (`operated`).
USED = frozenset((PORTAL, TOWN_PORTAL, WIRTS_BODY, *CLICKED, *WAYPOINT_CLASSES))


@dataclass(frozen=True)
class Thing:
    """An object a mark names for a click: an object unit of the loaded rooms."""

    unit_id: int
    txt_id: int  # objects.txt id
    mode: int  # 0 until it is operated (a body searched, a chest opened)
    x: float  # world units: what its picture and click box hang from
    y: float
    selectable: bool | None = field(default=None, compare=False)  # the game's own flag (UNIT_FLAGS); None: unread


# The unit's flag word. Bit 0x02 is "can be selected": Glacial Trail and Drifter Cavern, 09:30 on
# 2026-10-12, 113 object units of 21 classes: set on each of the 15 that objects.txt calls selectable in
# their mode (unopened chests, jars, shrines, a well, the evil urn), clear on the 98 others (the same
# chests and jars once opened, torches, fog, bubbles). Bit 0x04 was set on the unbroken jars only
# (`IsAttackable0`).
UNIT_FLAGS = 0x124
SELECTABLE_FLAG = 0x02


@functools.cache
def container_table() -> dict[int, tuple[str, frozenset[int]]]:
    """Object class id -> (objects.txt Class, the modes it can be clicked or struck in) of what is opened
    for what it holds: chests, caskets, urns, corpses and the like (data/containers.json,
    macros/build_containers.py)."""
    data = json.loads((Path(__file__).parent / 'data' / 'containers.json').read_text())
    return {int(txt): (row['class'], frozenset(row['modes'])) for txt, row in data['containers'].items()}


def container_names() -> dict[int, str]:
    return {txt: name for txt, (name, _modes) in container_table().items()}


def usable(thing: Thing) -> bool:
    """Whether the game lets the container be used as it stands: its own "can be selected" flag
    (UNIT_FLAGS), and when that is unread objects.txt's word on its mode (`Selectable0..7`,
    `IsAttackable0`). A chest is until it is opened."""
    row = container_table().get(thing.txt_id)
    if row is None:
        return False
    return thing.mode in row[1] if thing.selectable is None else thing.selectable


def containers() -> frozenset[int]:
    return frozenset(container_names())


def things(read, table: int, classes: frozenset[int] = USED) -> tuple[Thing, ...]:
    """The objects of `classes` among the streamed object units: by default those a mark may name."""
    heads = struct.unpack('<128Q', read(table + OBJECT_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] not in classes or not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        selectable = None
        with suppress(OSError, ValueError):
            selectable = bool(read(unit['address'] + UNIT_FLAGS, 1)[0] & SELECTABLE_FLAG)
        found.append(Thing(unit['unit_id'], unit['txt_id'], unit['mode'], float(x), float(y), selectable))
    return tuple(found)


def observe_things(pid, images, capture, classes: frozenset[int]) -> tuple[Thing, ...]:
    """The objects of `classes` near the player, opened read-only for this one read (the level guide's poll:
    a `use` mark's object operated by anyone, macros/card_goal.py)."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        found = things(ResearchReader(fd, process_mappings(pid)).read, next(iter(tables)), classes)
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the object read')
    return found


def gold_amount(read, unit: dict) -> int:
    """The gold in a pile on the ground; 0 when it cannot be read. Which of the unit's two stat lists
    holds it is not known yet (2026-10-11), so both are read and the first sight of a pile is logged."""
    if unit['unit_id'] in GOLD_SEEN:
        return GOLD_SEEN[unit['unit_id']]  # a pile's amount does not change, and the loot is read often
    for name, offset in (('full', FULL_STATS), ('base', BASE_STATS)):
        try:
            stats = read_stats(read, unit['stats_pointer'] + offset) if unit['stats_pointer'] else []
        except OSError, ValueError, struct.error:
            continue
        amount = next((s['raw'] for s in stats if s['id'] == GOLD_STAT and s['layer'] == 0), 0)
        if amount:
            if len(GOLD_SEEN) > 500:
                GOLD_SEEN.clear()
            GOLD_SEEN[unit['unit_id']] = amount
            if amount >= 1000:
                LOG.info('Macro: gold pile %d: %d gold (the %s stat list)', unit['unit_id'], amount, name)
            return amount
    return 0


def unit_stats(read, stats_at: int) -> dict[int, int]:
    """A unit's full stat list as {stat id: raw value} (layer 0 only); {} when unreadable."""
    try:
        return {s['id']: s['raw'] for s in read_stats(read, stats_at + FULL_STATS) if s['layer'] == 0}
    except OSError, ValueError, struct.error:
        return {}


def missiles(read, table: int) -> list[dict]:
    """Research (combat/plan.md stage 1): every missile unit of MISSILE_SLOTS as raw bytes: the
    unit record, its path record and the u16 pair at 0xC4 MapAssist calls X/Y, with the slot it
    hangs off. Nothing is interpreted yet."""
    found = []
    for slot in MISSILE_SLOTS:
        heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        for unit in walk_units(read, heads, MISSILE_UNIT)['units']:
            try:
                record = read(unit['address'], MISSILE_RECORD)
                path = read(unit['path_pointer'], MISSILE_PATH) if unit['path_pointer'] else b''
            except OSError, ValueError:
                continue
            data = b''
            if unit['data_pointer']:
                with contextlib.suppress(OSError, ValueError):
                    data = read(unit['data_pointer'], MISSILE_DATA)
            found.append(
                {
                    'unit_id': unit['unit_id'],
                    'txt_id': unit['txt_id'],
                    'mode': unit['mode'],
                    'slot': slot,
                    'xy': list(struct.unpack_from('<HH', record, 0xC4)),
                    'path': path.hex(),
                    'record': record.hex(),
                    'data': data.hex(),
                }
            )
    return found


def flights(read, table: int, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
    """The missiles in flight of the classes `kinds`, light: (owner unit id, class, x, y) from the unit record's
    owner (MISSILE_OWNER) and the head of its path record; the others are passed over after the unit header.
    What a read threat model prices (combat/threats; macros/safety.py `in_flight`)."""
    found = []
    for slot in MISSILE_SLOTS:
        heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        for unit in walk_units(read, heads, MISSILE_UNIT, records=True)['units']:
            if unit['txt_id'] not in kinds or not unit['path_pointer']:
                continue
            record = unit.get('record', b'')
            if len(record) < MISSILE_OWNER + 8:
                continue
            _kind, owner = struct.unpack_from('<II', record, MISSILE_OWNER)
            try:
                x, y = position(read(unit['path_pointer'], 8))
            except OSError, ValueError, struct.error:
                continue
            found.append((owner, unit['txt_id'], x, y))
    return tuple(found)


def unit_census(read, table: int) -> list[dict]:
    """Research: per slot of the unit hash table, how many heads are set and what the first unit
    says of itself (type, txt id, unit id, mode), the walk's unit count and its first error."""
    census = []
    for slot in range(UNIT_SLOTS):
        try:
            heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        except OSError, ValueError:
            census.append({'slot': slot, 'unreadable': True})
            continue
        first = next((head for head in heads if head), 0)
        entry: dict = {'slot': slot, 'heads': sum(1 for head in heads if head)}
        if first:
            try:
                entry['first'] = list(struct.unpack('<IIII', read(first, 16)))
            except OSError, ValueError:
                entry['first'] = None
            walked = walk_units(read, heads, entry['first'][0] if entry.get('first') else slot % 6)
            entry['units'] = len(walked['units'])
            if walked['errors']:
                entry['error'] = walked['errors'][0]['error']
        census.append(entry)
    return census


def mouse_skills(read, unit_address: int) -> tuple[int | None, int | None]:
    """(left, right) skill ids on the mouse buttons of the unit; None for a side that cannot be read."""
    try:
        skills = pointer(read, unit_address + SKILL_LIST)
    except OSError, ValueError, struct.error:
        return None, None
    if not skills:
        return None, None
    found = []
    for offset in (LEFT_SKILL, RIGHT_SKILL):
        try:
            record = pointer(read, skills + offset)
            found.append(struct.unpack('<H', read(pointer(read, record), 2))[0] if record else None)
        except OSError, ValueError, struct.error:
            found.append(None)
    return found[0], found[1]


def local_player(read, table: int) -> Player | None:
    """The character played, among the player units; None in menus or when it cannot be told."""
    heads = struct.unpack('<128Q', read(table, 1024))
    found = []
    for unit in walk_units(read, heads, 0, records=True)['units']:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 0x28)
            room1 = struct.unpack_from('<Q', path, PATH_ROOM1)[0]
            level = pointer(read, pointer(read, room1 + ROOM1_ROOM2) + ROOM2_LEVEL)
            area = struct.unpack('<I', read(level + LEVEL_AREA_ID, 4))[0]
            name = decode_name(read(unit['data_pointer'], 16))
        except OSError, ValueError, struct.error:
            continue
        consume, node = None, b''
        try:
            buff = read_consume(read, unit['stats_pointer'])
            consume = buff.active
            if buff.effect_id:
                node = read(buff.effect_id, 0x80)
        except OSError, ValueError, struct.error:
            pass
        left, right = mouse_skills(read, unit['address'])
        purge = ward = cooldown = None
        with suppress(OSError, ValueError, struct.error):
            delays, states = struct.unpack('<2I', read(unit['stats_pointer'] + STATE_FLAGS - 4, 8))
            purge, ward = bool(states & HEX_PURGE_BIT), bool(states & PSYCHIC_WARD_BIT)
            cooldown = bool(delays & COOLDOWN_BIT)
        player = Player(
            unit['unit_id'],
            name,
            unit['mode'],
            area,
            *position(path),
            consume,
            node,
            left,
            right,
            unit['stats_pointer'],
            purge,
            ward,
            unit.get('record', b''),
            skill_in_use(read, unit.get('record', b'')),
            cooldown,
        )
        found.append((player, unit['stats_pointer']))
    # Several player units may stand for the one character: the shared stash tabs carry its name
    # and no life (collection/research.md). With other players in the game (user, 2026-10-08)
    # the character is the one unit with a plausible life; another player's unit has none.
    # A corpse left on the level also carries the name, dead and without life, and may have the
    # lowest unit id (2026-10-11): with a dead unit among them the ones with a life go first.
    if len({player.name for player, _ in found}) == 1:
        if any(player.mode in PLAYER_DEAD_MODES for player, _ in found):
            found = [(player, stats) for player, stats in found if plausible_life(read, stats)] or found
        return min((player for player, _ in found), key=lambda p: p.unit_id)
    alive = [player for player, stats in found if plausible_life(read, stats)]
    return alive[0] if len(alive) == 1 else None


class GameMemory:
    """Keeps /proc/<pid>/mem open for one macro run."""

    def __init__(self, pid: int, base: int, table: int) -> None:
        self.base, self.table = base, table
        self.fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        self.hover_raw: tuple[int, int, int, int] | None = None  # the last record read whole (`hovered`)

    def close(self) -> None:
        os.close(self.fd)

    def read(self, address: int, size: int) -> bytes:
        data = os.pread(self.fd, size, address)
        if len(data) != size:
            raise ValueError('short read')
        return data

    def _player(self) -> Player | None:
        return local_player(self.read, self.table)

    def _monsters(self) -> tuple[tuple[Monster, ...], frozenset[int]]:
        return monsters_and_dead(self.read, self.table)

    def _doors(self) -> tuple[Door, ...]:
        return doors(self.read, self.table)

    def all_monsters(self, *, paths: bool = False, records: bool = False) -> tuple[Monster, ...]:
        """Live and dead monsters with a position (the recorder tells a death from an unload)."""
        return monsters(self.read, self.table, dead=True, paths=paths, records=records)

    def missiles(self) -> list[dict]:
        return missiles(self.read, self.table)

    def flights(self, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        return flights(self.read, self.table, kinds)

    def corpses(self) -> tuple[tuple[int, float, float], ...]:
        try:
            return corpses(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def warps(self) -> tuple[Warp, ...]:
        try:
            return warps(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def things(self) -> tuple[Thing, ...]:
        try:
            return things(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def operated(self) -> tuple[Thing, ...]:
        """Everything a mark may name for a click and every container, opened or not: what the combat
        recorder writes as the level's objects (a seal's mode says when it was opened)."""
        try:
            return things(self.read, self.table, USED | containers())
        except OSError, ValueError, struct.error:
            return ()

    def tick(self) -> bytes | None:
        """The head of the client's clock object, raw: by the client's code the time of the last whole
        tick in ms is the u32 at +0x0C (40 a tick) and the part of the tick under way the float at +0x18
        (rca/2026-10-13/re-findings.md; not yet seen to hold in a game). None when unread."""
        try:
            clock = struct.unpack('<Q', self.read(self.base + TERROR_SERVICE_RVA, 8))[0]
            return self.read(clock, TICK_HEAD) if clock else None
        except OSError, ValueError, struct.error:
            return None

    def states(self, stats_at: int) -> bytes | None:
        """The unit's state words raw (STATE_RUN); None when unread."""
        try:
            return self.read(stats_at + STATE_RUN[0], STATE_RUN[1]) if stats_at else None
        except OSError, ValueError, struct.error:
            return None

    def belt(self) -> tuple[int | None, ...] | None:
        """The item class in each belt cell of the character's (None: empty); None when unread."""
        try:
            player = self._player()
            if player is None:
                return None
            cells: list[int | None] = [None] * BELT_SIZE
            heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
            for unit in walk_units(self.read, heads, ITEM_UNIT)['units']:
                if unit['mode'] != BELT_ITEM_MODE or not unit['data_pointer'] or not unit['path_pointer']:
                    continue
                if struct.unpack_from('<I', self.read(unit['data_pointer'], 0x60), ITEM_OWNER)[0] != player.unit_id:
                    continue
                cell = struct.unpack_from('<H', self.read(unit['path_pointer'], 0x18), 0x10)[0]
                if cell < BELT_SIZE:
                    cells[cell] = unit['txt_id']
            return tuple(cells)
        except OSError, ValueError, struct.error:
            return None

    def containers(self) -> tuple[Thing, ...]:
        """The chests and the like the game shows now, opened or not (the pickup step opens them)."""
        try:
            return things(self.read, self.table, containers())
        except OSError, ValueError, struct.error:
            return ()

    def objects(self) -> list[dict]:
        """Research: every object unit the game shows, with its unit record and the head of its object
        data raw (which bytes say that it can be used is not known yet, 2026-10-12)."""
        found = []
        with suppress(OSError, ValueError, struct.error):
            heads = struct.unpack('<128Q', self.read(self.table + OBJECT_UNIT * 1024, 1024))
            for unit in walk_units(self.read, heads, OBJECT_UNIT)['units']:
                row = {key: unit[key] for key in ('unit_id', 'txt_id', 'mode')}
                with suppress(OSError, ValueError, struct.error):
                    path = self.read(unit['path_pointer'], OBJECT_PATH)
                    row['x'] = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF
                    row['y'] = struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
                    row['unit'] = self.read(unit['address'], 0x160).hex()
                    row['data'] = self.read(unit['data_pointer'], 0x40).hex()
                found.append(row)
        return found

    def census(self) -> list[dict]:
        return unit_census(self.read, self.table)

    def stats(self, stats_at: int) -> dict[int, int]:
        return unit_stats(self.read, stats_at)

    def loot(
        self,
        *,
        rune_minimum: str,
        unique_minimum: float | None,
        materials: dict[int, str],
        gold_minimum: int | None = None,
        shown: tuple[ShownRule, ...] = (),
        prized_rune_minimum: str | None = None,
        prized_materials: frozenset[int] | None = None,
    ) -> Loot:
        """The drops the loot marks would show (loot/ground.py, the same rules), the potions on the
        ground, the character's belt and life. An empty Loot when the character cannot be read."""
        try:
            player = self._player()
            if player is None:
                return Loot()
            read, table = self.read, self.table
            # Without the marks' own settings every rune and material counts as one of theirs (`prized`).
            drops = [
                Drop(
                    rune.unit_id, rune.x, rune.y, rune_name(rune.class_id), VALUABLE,
                    prized=prized(
                        'rune',
                        marked=prized_rune_minimum is None
                        or is_valuable_rune(rune.class_id, minimum=prized_rune_minimum),
                    ),
                )
                for rune in ground_runes(read, table, minimum=rune_minimum)
            ]  # fmt: skip
            marked = [*ground_materials(read, table, materials, appraised_classes())] if materials else []
            sources = dict.fromkeys((item.unit_id for item in marked), 'material')
            if shown:
                found = ground_shown(read, table, shown)
                marked += found
                sources.update({item.unit_id: shown_source(item.quality) for item in found})
            if unique_minimum is not None:
                found = ground_uniques(read, table, minimum=unique_minimum)
                marked += found
                sources.update(dict.fromkeys((item.unit_id for item in found), 'unique'))
            # One drop per unit: a unique ring is both a ring and a marked unique (the unique's label wins,
            # as it does over the label of a base the filter shows).
            labelled = {item.unit_id: item for item in marked}
            drops += [Drop(item.unit_id, item.x, item.y, item.label, VALUABLE) for item in labelled.values()]
            heads = struct.unpack('<128Q', read(table + ITEM_UNIT * 1024, 1024))
            items = walk_units(read, heads, ITEM_UNIT)['units']
            classes = {unit['unit_id']: unit['txt_id'] for unit in items}
            drops = [
                replace(
                    drop,
                    size=item_size(classes.get(drop.unit_id)),
                    prized=drop.prized
                    if drop.unit_id not in sources
                    else prized(
                        sources[drop.unit_id],
                        marked=prized_materials is None or classes.get(drop.unit_id) in prized_materials,
                    ),
                )
                for drop in drops
            ]
            for unit in items:
                if gold_minimum is None or unit['txt_id'] != GOLD_CLASS:
                    continue
                if unit['mode'] not in GROUND_MODES or not unit['path_pointer']:
                    continue
                amount = gold_amount(read, unit)
                if amount >= gold_minimum:
                    x, y = static_position(read, unit)
                    drops.append(Drop(unit['unit_id'], x, y, f'{amount} gold', GOLD, (0, 0)))
            for potion in item_units(read, table, {SUPER_HEALING, FULL_REJUVENATION}):
                if potion.mode in GROUND_MODES:
                    kind = REJUVENATION if potion.class_id == FULL_REJUVENATION else HEALING
                    drops.append(
                        Drop(
                            potion.unit_id,
                            potion.x,
                            potion.y,
                            f'a {"full rejuvenation" if kind == REJUVENATION else "super healing"} potion',
                            kind,
                        )
                    )
            belt: list[int | None] = [None] * BELT_SIZE
            for unit in items:
                if unit['mode'] != BELT_ITEM_MODE or not unit['data_pointer'] or not unit['path_pointer']:
                    continue
                if struct.unpack_from('<I', read(unit['data_pointer'], 0x60), ITEM_OWNER)[0] != player.unit_id:
                    continue
                cell = struct.unpack_from('<H', read(unit['path_pointer'], 0x18), 0x10)[0]
                if cell < BELT_SIZE:
                    belt[cell] = unit['txt_id']
            stats = unit_stats(read, player.stats_at) if player.stats_at else {}
            room, cube, held = carried_rows(read, table, player.unit_id)
            carried = frozenset(unit['unit_id'] for unit in items if unit['address'] in held)
            return Loot(
                tuple(drops),
                tuple(belt),
                stats.get(LIFE_STAT, 0) >> 8,
                stats.get(MAX_LIFE_STAT, 0) >> 8,
                room,
                tuple(sorted(stats.items())),
                (decode_name(read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE)), player.unit_id),
                cube=cube,
                shown=frozenset(unit for unit, source in sources.items() if source == 'shown'),
                carried=carried,
                classes=tuple((drop.unit_id, classes[drop.unit_id]) for drop in drops if drop.unit_id in classes),
            )
        except OSError, ValueError, struct.error:
            return Loot()

    def _equipped(self):
        """(unit, item data) of what the character wears; ValueError/OSError when unreadable."""
        player = self._player()
        if player is None:
            return
        heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
        for unit in walk_units(self.read, heads, ITEM_UNIT)['units']:
            if unit['mode'] != EQUIPPED_MODE or not unit['data_pointer']:
                continue
            data = self.read(unit['data_pointer'], 0x60)
            if struct.unpack_from('<I', data, ITEM_OWNER)[0] == player.unit_id:
                yield unit, data

    def hands(self) -> tuple[str, ...]:
        """Base codes of what the character holds in the weapon set in hand; () when unreadable."""
        try:
            held = []
            for unit, data in self._equipped():
                base = item_base(unit['txt_id']) if data[ITEM_BODY_LOCATION] in HANDS else None
                if base is not None:
                    held.append(base['code'])
            return tuple(sorted(held))
        except OSError, ValueError, struct.error:
            return ()

    def teleport(self) -> Teleport | None:
        """The worn staff with Teleport charges, in either weapon set; None without one or when unreadable."""
        if TELEPORT_STATS is None:
            return None
        try:
            for unit, data in self._equipped():
                if unit['txt_id'] not in STAFF_CLASS_IDS or data[ITEM_BODY_LOCATION] not in WEAPON_SLOTS:
                    continue
                for stat in read_stats(self.read, unit['stats_pointer'] + TELEPORT_STATS):
                    if stat['id'] == CHARGED_SKILL_STAT and stat['layer'] >> 6 == TELEPORT_SKILL:
                        raw = stat['raw'] & 0xFFFF
                        return Teleport(raw & 0xFF, raw >> 8, data[ITEM_BODY_LOCATION] in HANDS)
        except OSError, ValueError, struct.error:
            return None
        return None

    def hovered(self) -> tuple[int, int] | None:
        """(unit type, unit id) the game holds for the unit under the pointer (HOVER_RVA); None when
        unreadable, and when the record is known to be a leftover.

        The record keeps the last unit after the pointer has left it: of the pickup clicks made with
        the item "under the pointer" up to 2026-10-11, 87 of 130 took it at the aim 14 pixels above
        its ground and none of 21 at 6 (the pointer crosses the label on its way and stops on the
        ground below; the click then walks the character there). The record is 16 bytes in a table
        (hover/legacy.py: active, type, id; the three memory images in pricing/raw/re hold 0 in the
        first word with a unit in the next two). Confirmed in game, the Tower, 17:21 on 2026-10-11:
        the word read 0x101 at each of the 5 aims whose click took the item and 0 at the 7 aims that
        still named an item picked up before. The whole record is kept for the log (`hover_note`)."""
        try:
            flag, unit_type, unit_id, tail = struct.unpack('<IIII', self.read(self.base + HOVER_RVA - 4, 16))
        except OSError, ValueError, struct.error:
            return None
        self.hover_raw = (flag, unit_type, unit_id, tail)
        return (unit_type, unit_id) if flag else None

    def hover_note(self) -> str:
        """The record `hovered` read last, whole, for a log line."""
        if self.hover_raw is None:
            return 'unread'
        flag, unit_type, unit_id, tail = self.hover_raw
        return f'flag {flag:#x} type {unit_type} id {unit_id} tail {tail:#x}'

    def hover_candidates(self, unit_id: int, unit_type: int = MONSTER_UNIT) -> list[str]:
        """Research: image addresses holding (unit type, this unit id), as the record of the
        unit under the pointer would while the pointer is on it. Never raises."""
        try:
            data = b''.join(
                os.pread(self.fd, 0x100000, self.base + DATA_RVA + offset).ljust(0x100000, b'\0')
                for offset in range(0, DATA_SIZE, 0x100000)
            )
        except OSError:
            return []
        wanted, found, at = struct.pack('<II', unit_type, unit_id), [], -1
        while len(found) < 8 and (at := data.find(wanted, at + 1)) >= 0:
            found.append(hex(DATA_RVA + at))
        return found

    def place(self) -> tuple[str | None, int | None]:
        """(game name, level) for the journey: no name out of a game, no level when unreadable."""
        if self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)[IN_GAME] != 1:
            return None, None
        name = decode_name(self.read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE))
        try:
            player = self._player()
        except OSError, ValueError, struct.error:
            player = None
        return name, player.area if player is not None else None

    def world(self, light: bool = False) -> World:
        """The game as it is now. `light`: without the monsters and the doors, for a step that only
        asks where the character is and what it does. A teleport step looked at the game about six
        times before its key, 54 to 96 ms in all with nothing else in the way (22:11 on 2026-10-11),
        and every look walked all the monsters."""
        panels = self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)
        in_game = panels[IN_GAME] == 1
        player, monsters, doors, dead = None, (), (), frozenset()
        if in_game:
            try:
                player = self._player()
                if not light:
                    monsters, dead = self._monsters() if player is not None else ((), frozenset())
                    doors = self._doors() if player is not None else ()
            except OSError, ValueError, struct.error:
                player, monsters, doors, dead = None, (), (), frozenset()
        return World(
            in_game=in_game,
            open_panels=tuple(name for name, offset in OPEN_PANELS.items() if panels[offset] == 1),
            game_name=decode_name(self.read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE)),
            slots=decode_slots(self.read(self.base + SKILL_SLOTS_RVA, SKILL_SLOTS * SKILL_SLOT_SIZE)),
            trace=b''.join(self.read(self.base + rva, 1) for rva in TRACE_RVAS),
            view=self.read(self.base + VIEW_RVA, 1)[0],
            player=player,
            monsters=monsters,
            doors=doors,
            dead=dead,
        )
