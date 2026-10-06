"""Current area and its preset rooms, through the confirmed level/room chain (layout.py)."""

import contextlib
import os
import struct

from inventory_tracking.levels.model import Location, Room, Walkable, pack_cells
from inventory_tracking.native.layout import (
    COLLISION_BLOCK_WALK,
    COLLISION_BOUNDS,
    COLLISION_MASK,
    LEVEL_AREA_ID,
    LEVEL_FIRST_ROOM2,
    PATH_ROOM1,
    PRESET_OBJECT_BOUNDS,
    PRESET_OBJECT_FILE,
    PRESET_RECORD_OBJECT,
    ROOM1_COLLISION,
    ROOM1_NEAR,
    ROOM1_NEAR_COUNT,
    ROOM1_ROOM2,
    ROOM2_BOUNDS,
    ROOM2_LEVEL,
    ROOM2_NEAR,
    ROOM2_NEAR_COUNT,
    ROOM2_NEXT,
    ROOM2_PRESET,
    TILE_UNITS,
)
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import walk_units


MAX_ROOMS = 1024
MAX_NEAR = 16  # observed 5-9 (a 3x3 neighbourhood)
MAX_LOADED = 64  # loaded Room1s: about 9-35 in the dumps
MAX_SUBTILES = 400 * 400
OBJECT_UNIT = 2
# Waypoint object classes: every d2data objects.json row with OperateFn 23 (all named 'Waypoint'), by *ID.
WAYPOINT_CLASSES = frozenset((119, 145, 156, 157, 237, 238, 288, 323, 324, 398, 402, 429, 494, 496, 511, 539))


def pointer(read, address):
    return struct.unpack('<Q', read(address, 8))[0]


def player_location(read, table_address) -> Location | None:
    """The area every player unit with a room agrees on; None in menus or while ambiguous."""
    found = player_room(read, table_address)
    return None if found is None else found[0]


def player_room(read, table_address) -> tuple[Location, int] | None:
    """(location, Room1) of the player units, when they agree on one level; else None."""
    heads = struct.unpack('<128Q', read(table_address, 1024))
    found = set()
    for unit in walk_units(read, heads, 0)['units']:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 0x28)
            room1 = struct.unpack_from('<Q', path, PATH_ROOM1)[0]
            level = pointer(read, pointer(read, room1 + ROOM1_ROOM2) + ROOM2_LEVEL)
            area = struct.unpack('<I', read(level + LEVEL_AREA_ID, 4))[0]
        except OSError, ValueError, struct.error:
            continue
        x, y = struct.unpack_from('<HxxH', path, 0x02)
        found.add((Location(area, level, x, y, unit['path_pointer']), room1))
    levels = {(loc.area_id, loc.level) for loc, _ in found}
    # Player-like units share the character's position; keep the first when they agree.
    return min(found, key=lambda item: (item[0].x, item[0].y)) if len(levels) == 1 else None


def preset_details(read, record):
    """(Def, file index, whole-preset bounds); the last two are None unless the object checks out."""
    preset = struct.unpack('<I', read(record, 4))[0]
    try:
        obj = struct.unpack('<Q', read(record + PRESET_RECORD_OBJECT, 8))[0]
        data = read(obj, PRESET_OBJECT_BOUNDS + 16)
    except OSError, ValueError, struct.error:
        return preset, None, None
    if struct.unpack_from('<I', data)[0] != preset:
        return preset, None, None
    variant = struct.unpack_from('<I', data, PRESET_OBJECT_FILE)[0]
    x, y, w, h = struct.unpack_from('<IIII', data, PRESET_OBJECT_BOUNDS)
    return preset, variant, (x, y, w, h)


def neighbour_areas(read, room2, data, level) -> tuple[int, ...]:
    """Areas of other levels among the room's neighbours: the level exits. Unreadable = ()."""
    array = struct.unpack_from('<Q', data, ROOM2_NEAR)[0]
    count = struct.unpack_from('<I', data, ROOM2_NEAR_COUNT)[0]
    if not array or not 0 < count <= MAX_NEAR:
        return ()
    try:
        neighbours = struct.unpack(f'<{count}Q', read(array, 8 * count))
    except OSError, ValueError, struct.error:
        return ()
    areas = []
    for neighbour in neighbours:
        if neighbour in (0, room2):
            continue
        try:
            other = pointer(read, neighbour + ROOM2_LEVEL)
            if other == level:
                continue
            area = struct.unpack('<I', read(other + LEVEL_AREA_ID, 4))[0]
        except OSError, ValueError, struct.error:
            continue
        if 0 < area < 256 and area not in areas:
            areas.append(area)
    return tuple(areas)


def walkable_tiles(read, room1) -> Walkable | None:
    """The room's sub-tiles, walkable when the collision mask does not block walking there."""
    try:
        grid = pointer(read, room1 + ROOM1_COLLISION)
        header = read(grid, COLLISION_MASK + 8)
        x, y, w, h = struct.unpack_from('<IIII', header, COLLISION_BOUNDS)
        if not (w and h and w * h <= MAX_SUBTILES and not x % 5 and not y % 5 and not w % 5 and not h % 5):
            return None
        mask = struct.unpack(f'<{w * h}H', read(struct.unpack_from('<Q', header, COLLISION_MASK)[0], w * h * 2))
    except OSError, ValueError, struct.error:
        return None
    return tiles_from_mask(x, y, w, h, mask)


def tiles_from_mask(x, y, w, h, mask) -> Walkable:
    """Sub-tile collision mask (x, y, w, h in sub-tiles) -> the room's walkable sub-tiles.

    Kept per sub-tile (user, 2026-10-06): a tile-by-majority map lost walls one sub-tile thick,
    such as most of a Lower Kurast hut.
    """
    cells = pack_cells(''.join('0' if value & COLLISION_BLOCK_WALK else '1' for value in mask))
    return Walkable(x // 5, y // 5, w // 5, h // 5, cells)


def loaded_walkable(read, room1, level, *, max_rooms=MAX_LOADED) -> list[Walkable]:
    """Walkable tiles of the level's loaded rooms, reached through Room1 neighbours from `room1`."""
    found, seen, queue = [], set(), [room1]
    while queue and len(seen) < max_rooms:
        room = queue.pop(0)
        if room in seen or not room:
            continue
        seen.add(room)
        try:
            if pointer(read, pointer(read, room + ROOM1_ROOM2) + ROOM2_LEVEL) != level:
                continue
            data = read(room, ROOM1_NEAR_COUNT + 4)
        except OSError, ValueError, struct.error:
            continue
        tiles = walkable_tiles(read, room)
        if tiles is not None:
            found.append(tiles)
        array, count = (
            struct.unpack_from('<Q', data, ROOM1_NEAR)[0],
            struct.unpack_from('<I', data, ROOM1_NEAR_COUNT)[0],
        )
        if array and 0 < count <= MAX_NEAR:
            with contextlib.suppress(OSError, ValueError, struct.error):
                queue.extend(struct.unpack(f'<{count}Q', read(array, 8 * count)))
    return found


def preset_rooms(read, level, *, max_rooms=MAX_ROOMS) -> list[Room]:
    rooms, seen = [], set()
    room2 = pointer(read, level + LEVEL_FIRST_ROOM2)
    while room2 and room2 not in seen:
        if len(seen) >= max_rooms:
            raise ValueError('Room2 traversal budget reached')
        seen.add(room2)
        data = read(room2, ROOM2_LEVEL + 8)
        if struct.unpack_from('<Q', data, ROOM2_LEVEL)[0] != level:
            raise ValueError('Room2 does not belong to the level')
        preset, variant, block = preset_details(read, struct.unpack_from('<Q', data, ROOM2_PRESET)[0])
        bounds = struct.unpack_from('<IIII', data, ROOM2_BOUNDS)
        rooms.append(Room(preset, *bounds, variant, block, neighbour_areas(read, room2, data, level)))
        room2 = struct.unpack_from('<Q', data, ROOM2_NEXT)[0]
    return rooms


def observe_level(pid, images, capture, *, rooms=False) -> tuple[Location | None, list[Room]]:
    """Read-only, bounded; rooms are read only when asked (once per area entry)."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, process_mappings(pid)).read
        location = player_location(read, next(iter(tables)))
        found = preset_rooms(read, location.level) if rooms and location else []
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the level read')
    return location, found


def nearby_waypoints(read, table_address) -> list[tuple[float, float]]:
    """Waypoint objects among the streamed object units (those near the player), in tiles.
    Object positions are the static path x/y (+0x10/+0x14, confirmed for shrines, loot/ground.py)."""
    heads = struct.unpack('<128Q', read(table_address + OBJECT_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] not in WAYPOINT_CLASSES or not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 0x18)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        found.append((x / TILE_UNITS, y / TILE_UNITS))
    return found


def observe_waypoints(pid, images, capture) -> list[tuple[float, float]]:
    """Waypoints near the player, in tiles (read-only, bounded)."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        found = nearby_waypoints(ResearchReader(fd, process_mappings(pid)).read, next(iter(tables)))
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the waypoint read')
    return found


def observe_walkable(pid, images, capture) -> list[Walkable]:
    """Walkable tiles of the loaded rooms around the player (read-only, bounded)."""
    tables = {x['table_address'] for x in capture['unit_table_candidates']}
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        read = ResearchReader(fd, process_mappings(pid)).read
        found = player_room(read, next(iter(tables)))
        grids = loaded_walkable(read, found[1], found[0].level) if found else []
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the walls read')
    return grids
