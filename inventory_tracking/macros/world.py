"""What a macro may ask about the game, read fresh from memory in one pass.

Image addresses found with the record probe on 2026-10-06 (plan.md, findings): the skill slot
table, the game name and the in-game byte. The unit table is the one the service attached to;
it stays at the same address through the lobby and into the next game.
"""

import contextlib
import os
import re
import struct
from dataclasses import dataclass, field, replace

from inventory_tracking.config import RESOURCE_READER
from inventory_tracking.items.metadata import item_base
from inventory_tracking.levels.doors import Door, door_sizes
from inventory_tracking.levels.memory import pointer
from inventory_tracking.loot.ground import GROUND_MODES, ground_materials, ground_runes, ground_uniques, item_units
from inventory_tracking.loot.runes import rune_name
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
    ROOM1_ROOM2,
    ROOM2_LEVEL,
    STAFF_CLASS_IDS,
    TELEPORT_SKILL,
    TOWN_IDS,
    UI_PANELS_RVA,
    UI_PANELS_SIZE,
    WEAPON_SLOTS,
)
from inventory_tracking.native.units import read_stats, walk_units
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
LEADER_FLAGS = 0x02 | 0x04 | 0x08
MINION_FLAG = 0x10
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
MISSILE_DATA = 0x80  # bytes of its data record (pUnitData) dumped on first sight: skill, velocity, target?
DATA_RVA, DATA_SIZE = 0x197A000, 0xC98000  # the image's writable data (record probe)
ITEM_UNIT = 4
FULL_STATS = 0xE8  # the unit's full stat list (native/units.py describe_player)
EQUIPPED_MODE = 1
ITEM_OWNER, ITEM_BODY_LOCATION = 0x0C, 0x54  # item data (native/units.py describe_item)
# The weapon set in hand; the other set sits at 11 and 12 (config.py: staff 4 -> 11 on swap).
HANDS = frozenset((4, 5))
# An item's full stat list, where a staff's charged skills are (tracking/resources.py select_teleport).
TELEPORT_STATS = RESOURCE_READER.teleport_stats_offset
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
    consume_node: bytes = field(default=b'', compare=False, repr=False)  # research: the buff's record
    left_skill: int | None = None  # the skill on the left mouse button; None when unreadable
    right_skill: int | None = None
    stats_at: int = field(
        default=0, compare=False, repr=False
    )  # the unit's stat list (combat/record.py reads life and mana)

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
    flags: int = 0  # type flags (TYPE_FLAGS byte)
    ally: bool = False  # alignment stat set: a summon or the mercenary
    life: int = 0  # whole points (stats 6 and 7); 0 when the stats were unreadable
    max_life: int = 0
    raw: bytes = field(default=b'', compare=False, repr=False)  # unit and monster data, Defilers only
    stats_at: int = field(default=0, compare=False, repr=False)  # the unit's stat list, for a full read

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


@dataclass(frozen=True)
class Drop:
    """An item on the ground worth a walk: one the loot marks point at, or a potion the belt may want."""

    unit_id: int
    x: float  # world units
    y: float
    label: str
    kind: str  # VALUABLE, HEALING or REJUVENATION


@dataclass(frozen=True)
class Loot:
    """What the pickup step decides on (macros/pickup.py): the drops near the character, its belt and its life."""

    drops: tuple[Drop, ...] = ()
    belt: tuple[int | None, ...] = (None,) * BELT_SIZE  # item class by cell; the first four are the hotkey row
    life: int = 0  # whole points; 0 when unreadable
    max_life: int = 0


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


def monsters(read, table: int, *, dead: bool = False) -> tuple[Monster, ...]:
    """The live monsters with a position: type flags and owner from the monster data, ally by the
    alignment stat (unreadable stats: not an ally). Dead ones (unless `dead`) and those without a
    path are left out."""
    return monsters_and_dead(read, table, dead=dead)[0]


def monsters_and_dead(read, table: int, *, dead: bool = False) -> tuple[tuple[Monster, ...], frozenset[int]]:
    """`monsters`, and the unit ids of the monsters lying dead (from the same walk of the unit table)."""
    heads = struct.unpack('<128Q', read(table + MONSTER_UNIT * 1024, 1024))
    found = []
    corpses = set()
    for unit in walk_units(read, heads, MONSTER_UNIT)['units']:
        if unit['mode'] in DEAD_MODES:
            corpses.add(unit['unit_id'])
        if (unit['mode'] in DEAD_MODES and not dead) or not unit['path_pointer'] or not unit['data_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 8)
            data = read(unit['data_pointer'], MONSTER_DATA)
        except OSError, ValueError:
            continue
        owner = struct.unpack_from('<I', data, MONSTER_OWNER)[0]
        ally, life, max_life = False, 0, 0
        if unit['stats_pointer']:
            with contextlib.suppress(OSError, ValueError, struct.error):
                full = read_stats(read, unit['stats_pointer'] + FULL_STATS)
                stats = {s['id']: s['raw'] for s in full if s['layer'] == 0}
                ally = bool(stats.get(ALIGNMENT_STAT))
                life, max_life = stats.get(LIFE_STAT, 0) >> 8, stats.get(MAX_LIFE_STAT, 0) >> 8
        raw = b''
        if unit['txt_id'] == DEFILER_CLASS:
            with contextlib.suppress(OSError, ValueError):
                raw = read(unit['address'], 0x160) + read(unit['data_pointer'], 0x80)
        monster = Monster(unit['unit_id'], unit['txt_id'], unit['mode'], *position(path), owner, data[TYPE_FLAGS])
        found.append(replace(monster, ally=ally, life=life, max_life=max_life, raw=raw, stats_at=unit['stats_pointer']))
    return tuple(found), frozenset(corpses)


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
    for unit in walk_units(read, heads, 0)['units']:
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
        )
        found.append((player, unit['stats_pointer']))
    # Several player units may stand for the one character: the shared stash tabs carry its name
    # and no life (collection/research.md). With other players in the game (user, 2026-10-08)
    # the character is the one unit with a plausible life; another player's unit has none.
    if len({player.name for player, _ in found}) == 1:
        return min((player for player, _ in found), key=lambda p: p.unit_id)
    alive = [player for player, stats in found if plausible_life(read, stats)]
    return alive[0] if len(alive) == 1 else None


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
        return local_player(self.read, self.table)

    def _monsters(self) -> tuple[tuple[Monster, ...], frozenset[int]]:
        return monsters_and_dead(self.read, self.table)

    def _doors(self) -> tuple[Door, ...]:
        return doors(self.read, self.table)

    def all_monsters(self) -> tuple[Monster, ...]:
        """Live and dead monsters with a position (the recorder tells a death from an unload)."""
        return monsters(self.read, self.table, dead=True)

    def missiles(self) -> list[dict]:
        return missiles(self.read, self.table)

    def census(self) -> list[dict]:
        return unit_census(self.read, self.table)

    def stats(self, stats_at: int) -> dict[int, int]:
        return unit_stats(self.read, stats_at)

    def loot(self, *, rune_minimum: str, unique_minimum: float | None, materials: dict[int, str]) -> Loot:
        """The drops the loot marks would show (loot/ground.py, the same rules), the potions on the
        ground, the character's belt and life. An empty Loot when the character cannot be read."""
        try:
            player = self._player()
            if player is None:
                return Loot()
            read, table = self.read, self.table
            drops = [
                Drop(rune.unit_id, rune.x, rune.y, rune_name(rune.class_id), VALUABLE)
                for rune in ground_runes(read, table, minimum=rune_minimum)
            ]
            marked = [*ground_materials(read, table, materials)] if materials else []
            if unique_minimum is not None:
                marked += ground_uniques(read, table, minimum=unique_minimum)
            drops += [Drop(item.unit_id, item.x, item.y, item.label, VALUABLE) for item in marked]
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
            heads = struct.unpack('<128Q', read(table + ITEM_UNIT * 1024, 1024))
            for unit in walk_units(read, heads, ITEM_UNIT)['units']:
                if unit['mode'] != BELT_ITEM_MODE or not unit['data_pointer'] or not unit['path_pointer']:
                    continue
                if struct.unpack_from('<I', read(unit['data_pointer'], 0x60), ITEM_OWNER)[0] != player.unit_id:
                    continue
                cell = struct.unpack_from('<H', read(unit['path_pointer'], 0x18), 0x10)[0]
                if cell < BELT_SIZE:
                    belt[cell] = unit['txt_id']
            stats = unit_stats(read, player.stats_at) if player.stats_at else {}
            return Loot(tuple(drops), tuple(belt), stats.get(LIFE_STAT, 0) >> 8, stats.get(MAX_LIFE_STAT, 0) >> 8)
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
        """(unit type, unit id) the game holds for the unit under the pointer (HOVER_RVA); None when unreadable."""
        try:
            unit_type, unit_id = struct.unpack('<II', self.read(self.base + HOVER_RVA, 8))
        except OSError, ValueError, struct.error:
            return None
        return unit_type, unit_id

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

    def world(self) -> World:
        panels = self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)
        in_game = panels[IN_GAME] == 1
        player, monsters, doors, dead = None, (), (), frozenset()
        if in_game:
            try:
                player = self._player()
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
