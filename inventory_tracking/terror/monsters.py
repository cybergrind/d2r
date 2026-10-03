"""Monster units streamed to the client, for the Terror Zone probe.

Online, the client only holds monsters in the rooms loaded around the player (about 9-35
Room1s, levels/memory.py), so this is a local view, never the whole level. Position is the
dynamic path x/y (+0x02/+0x06) and the level comes through path +0x20 Room1 -> Room2 ->
level -> area, as for the player (native/layout.py); rooms are named by their Room2 bounds
(x, y, w, h tiles), the key the level map uses. Monster data (unit +0x10), the full stat list
(stats +0xE8, as for the mercenary) and the base list (+0x30) are read only on first sight:
research material for the Herald (stat 367) and for a Terror Zone signal (plan.md R1: the
client's level stat stays at the area's normal level). Entering a level also keeps its
struct bytes for that research.
"""

import contextlib
import os
import struct
from dataclasses import dataclass

from inventory_tracking.levels.memory import MAX_LOADED, MAX_NEAR, MAX_ROOMS, player_room, pointer
from inventory_tracking.levels.model import Location
from inventory_tracking.native.layout import (
    LEVEL_AREA_ID,
    LEVEL_FIRST_ROOM2,
    PATH_ROOM1,
    ROOM1_NEAR,
    ROOM1_NEAR_COUNT,
    ROOM1_ROOM2,
    ROOM2_BOUNDS,
    ROOM2_LEVEL,
    ROOM2_NEXT,
)
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import read_stats, walk_units


MONSTER_UNIT = 1
MONSTER_DATA_SIZE = 0x80
FULL_STATS = 0xE8
BASE_STATS = 0x30
LEVEL_SIZE = 0x400  # as the Win+C research dump (levels/research.py)

Bounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class Monster:
    unit_id: int
    txt_id: int
    mode: int
    x: int
    y: int
    area: int | None
    room: Bounds | None
    data_hex: str | None = None  # first sight only
    stats: tuple[tuple[int, int, int], ...] | None = None  # (layer, stat id, raw); first sight only
    base_stats: tuple[tuple[int, int, int], ...] | None = None  # first sight only


@dataclass(frozen=True)
class MonsterSnapshot:
    location: Location | None
    room2s: frozenset[Bounds]  # bounds of the Room2s of the loaded Room1s in the player's level
    level_rooms: int | None  # the level's Room2 count, read only on entering a level
    monsters: tuple[Monster, ...]
    complete: bool = True  # False when the unit walk broke off: absent monsters may still be there
    level_hex: str | None = None  # the level struct, read only on entering a level (R1 research)


def room_bounds(read, room2) -> Bounds:
    x, y, w, h = struct.unpack('<IIII', read(room2 + ROOM2_BOUNDS, 16))
    return x, y, w, h


def room_area(read, room1, cache) -> tuple[int | None, Bounds | None]:
    """(area, Room2 bounds) of a Room1; (None, None) when the chain is unreadable."""
    if room1 not in cache:
        try:
            room2 = pointer(read, room1 + ROOM1_ROOM2)
            level = pointer(read, room2 + ROOM2_LEVEL)
            cache[room1] = (struct.unpack('<I', read(level + LEVEL_AREA_ID, 4))[0], room_bounds(read, room2))
        except OSError, ValueError, struct.error:
            cache[room1] = (None, None)
    return cache[room1]


def first_sight(read, unit) -> dict:
    details = {}
    with contextlib.suppress(OSError, ValueError):
        if unit['data_pointer']:
            details['data_hex'] = read(unit['data_pointer'], MONSTER_DATA_SIZE).hex()
    for name, offset in (('stats', FULL_STATS), ('base_stats', BASE_STATS)):
        with contextlib.suppress(OSError, ValueError, struct.error):
            if unit['stats_pointer']:
                stats = read_stats(read, unit['stats_pointer'] + offset)
                details[name] = tuple((s['layer'], s['id'], s['raw']) for s in stats)
    return details


def monster_units(read, table_address, *, known) -> tuple[list[Monster], bool]:
    """(monsters, complete); a chain the game changed mid-walk loses the units after the break."""
    heads = struct.unpack('<128Q', read(table_address + MONSTER_UNIT * 1024, 1024))
    rooms: dict[int, tuple[int | None, Bounds | None]] = {}
    found = []
    walked = walk_units(read, heads, MONSTER_UNIT)
    for unit in walked['units']:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 0x28)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<HxxH', path, 0x02)
        area, room = room_area(read, struct.unpack_from('<Q', path, PATH_ROOM1)[0], rooms)
        details = {} if unit['unit_id'] in known else first_sight(read, unit)
        found.append(Monster(unit['unit_id'], unit['txt_id'], unit['mode'], x, y, area, room, **details))
    return found, walked['complete']


def loaded_rooms(read, room1, level, *, max_rooms=MAX_LOADED) -> frozenset[Bounds]:
    """Bounds of the level's loaded rooms, reached through Room1 neighbours from `room1`."""
    found, seen, queue = set(), set(), [room1]
    while queue and len(seen) < max_rooms:
        room = queue.pop(0)
        if room in seen or not room:
            continue
        seen.add(room)
        try:
            room2 = pointer(read, room + ROOM1_ROOM2)
            if pointer(read, room2 + ROOM2_LEVEL) != level:
                continue
            data = read(room, ROOM1_NEAR_COUNT + 4)
            found.add(room_bounds(read, room2))
        except OSError, ValueError, struct.error:
            continue
        array = struct.unpack_from('<Q', data, ROOM1_NEAR)[0]
        count = struct.unpack_from('<I', data, ROOM1_NEAR_COUNT)[0]
        if array and 0 < count <= MAX_NEAR:
            with contextlib.suppress(OSError, ValueError, struct.error):
                queue.extend(struct.unpack(f'<{count}Q', read(array, 8 * count)))
    return frozenset(found)


def level_entry(read, level, *, max_rooms=MAX_ROOMS) -> tuple[int, str]:
    """(Room2 count, level struct hex) on entering a level."""
    count, seen = 0, set()
    room2 = pointer(read, level + LEVEL_FIRST_ROOM2)
    while room2 and room2 not in seen and count < max_rooms:
        seen.add(room2)
        count += 1
        room2 = pointer(read, room2 + ROOM2_NEXT)
    return count, read(level, LEVEL_SIZE).hex()


def observe_monsters(pid, images, capture, *, known, counted_level) -> MonsterSnapshot:
    """Read-only, bounded. The level's Room2s are counted only when it is not `counted_level`."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, process_mappings(pid)).read
        table = next(iter(tables))
        found = player_room(read, table)
        if found is None:
            snapshot = MonsterSnapshot(None, frozenset(), None, ())
        else:
            location, room1 = found
            level_rooms = level_hex = None
            if location.level != counted_level:
                with contextlib.suppress(OSError, ValueError, struct.error):
                    level_rooms, level_hex = level_entry(read, location.level)
            monsters, complete = monster_units(read, table, known=known)
            rooms = loaded_rooms(read, room1, location.level)
            snapshot = MonsterSnapshot(location, rooms, level_rooms, tuple(monsters), complete, level_hex)
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the monster read')
    return snapshot
