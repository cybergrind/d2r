"""Read DS1 preset files (the game's map pieces, lvlprest File1..): warp tiles, monsters, objects.

Layout per Paul Siramy's DS1 notes; all 2277 installed files parse to their end (2026-10-03). A wall
cell's main index is bits 20-25, orientation the low byte. Special tiles (orientation 10, 11) with main
index 0-7 are warps: the index is the level's Vis/Warp slot (levels.txt; Cold Plains' CaveDr1.ds1 main 5 =
Vis5, Cave 1). Other main indexes are markers (doors 8-16, town 30-33). Tile positions from the preset origin.
"""

import struct
from collections import defaultdict


SPECIAL = (10, 11)
WARP_SLOTS = 8
MONSTER = 1  # object type: a monster, by its row in monpreset.txt
OBJECT = 2  # object type: an object, by its Index among its act's rows of objpreset.txt


def _read(data: bytes):
    """(wall layers as (cells, orientations), width, act, objects as (type, id, x, y)) of a DS1 file.
    Order: version, width-1, height-1, act (v8+), tag type (v10+), tile file names (v3+), 2 ints (v9-13),
    wall/floor layer counts (v4+/v16+), walls, floors, shadow, tags (type 1-2), objects (v2+, flags v6+)."""
    offset = 0

    def i32() -> int:
        nonlocal offset
        value = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        return value

    version, width, height = i32(), i32() + 1, i32() + 1
    act = i32() if version >= 8 else 0
    tag_type = i32() if version >= 10 else 0
    if version >= 3:
        for _ in range(i32()):
            offset = data.index(b'\0', offset) + 1
    if 9 <= version <= 13:
        offset += 8
    walls = i32() if version >= 4 else 1
    floors = i32() if version >= 16 else 1
    size = width * height
    layers = []
    for _ in range(walls):
        cells = struct.unpack_from(f'<{size}I', data, offset)
        orientations = struct.unpack_from(f'<{size}I', data, offset + 4 * size)
        offset += 8 * size
        layers.append((cells, orientations))
    offset += 4 * size * (floors + 1 + (tag_type in (1, 2)))  # floors, the shadow, the tags
    objects = []
    for _ in range(i32() if version >= 2 else 0):
        objects.append((i32(), i32(), i32(), i32()))
        if version > 5:
            i32()  # flags
    return layers, width, act, objects


def monster_presets(data: bytes) -> tuple[int, list[tuple[int, int, int]]]:
    """(act, 0-based; [(id, x, y)]) of the file's monsters: `id` the monpreset.txt row among its act's,
    x, y sub-tiles from the preset origin (within 0-21 units of first sightings, 2026-10-06)."""
    _layers, _width, act, objects = _read(data)
    return act, [(found, x, y) for kind, found, x, y in objects if kind == MONSTER]


def object_presets(data: bytes) -> tuple[int, list[tuple[int, int, int]]]:
    """(act, 0-based; [(id, x, y)]) of the file's objects: `id` the objpreset.txt Index among its act's
    rows, x, y sub-tiles from the preset origin (Catacombs 2 waypoint within 2 units, 2026-10-07)."""
    _layers, _width, act, objects = _read(data)
    return act, [(found, x, y) for kind, found, x, y in objects if kind == OBJECT]


def warp_tiles(data: bytes) -> dict[int, list[tuple[int, int]]]:
    """Warp slot -> its tiles (x, y from the preset origin), sorted."""
    layers, width, _act, _objects = _read(data)
    found: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for cells, orientations in layers:
        for index, (cell, orientation) in enumerate(zip(cells, orientations, strict=True)):
            if cell and orientation & 0xFF in SPECIAL:
                main = (cell >> 20) & 0x3F
                if main < WARP_SLOTS:
                    found[main].append((index % width, index // width))
    return {slot: sorted(tiles) for slot, tiles in found.items()}
