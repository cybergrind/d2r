"""Read DS1 preset files (the game's map pieces, lvlprest File1..): warp tiles.

Layout per Paul Siramy's DS1 notes, checked against the installed game on 2026-10-03 (all 2277
files parse to their end): version, width - 1, height - 1, act (v8+), tag type (v10+), tile
file names (v3+), two skipped ints (v9-13), wall and floor layer counts (v4+, floors v16+),
then per wall layer its tiles and orientations, the floors, the shadow and the tags (tag type 1
or 2), each width x height u32 row by row. A wall cell's main index is bits 20-25, the sub
index bits 8-15; orientation is the low byte. Special tiles (orientation 10 and 11) with a
main index 0-7 are warps: the index is the level's Vis/Warp slot (levels.txt), e.g. the Cold
Plains Cave Entrance (CaveDr1.ds1) has main 5, and Cold Plains' Vis5 is Cave 1. Other main
indexes there are markers (doors 8-16, town 30-33). Positions are tiles from the preset origin.
"""

import struct
from collections import defaultdict


SPECIAL = (10, 11)
WARP_SLOTS = 8


def _layers(data: bytes):
    """(wall layers as (cells, orientations), width) of a DS1 file."""
    offset = 0

    def i32() -> int:
        nonlocal offset
        value = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        return value

    version, width, height = i32(), i32() + 1, i32() + 1
    if version >= 8:
        i32()  # act
    if version >= 10:
        i32()  # tag type: tags and objects follow the walls; warps need only the walls
    if version >= 3:
        for _ in range(i32()):
            offset = data.index(b'\0', offset) + 1
    if 9 <= version <= 13:
        offset += 8
    walls = i32() if version >= 4 else 1
    if version >= 16:
        i32()  # floor layers: not needed
    size = width * height
    layers = []
    for _ in range(walls):
        cells = struct.unpack_from(f'<{size}I', data, offset)
        orientations = struct.unpack_from(f'<{size}I', data, offset + 4 * size)
        offset += 8 * size
        layers.append((cells, orientations))
    return layers, width


def warp_tiles(data: bytes) -> dict[int, list[tuple[int, int]]]:
    """Warp slot -> its tiles (x, y from the preset origin), sorted."""
    layers, width = _layers(data)
    found: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for cells, orientations in layers:
        for index, (cell, orientation) in enumerate(zip(cells, orientations, strict=True)):
            if cell and orientation & 0xFF in SPECIAL:
                main = (cell >> 20) & 0x3F
                if main < WARP_SLOTS:
                    found[main].append((index % width, index // width))
    return {slot: sorted(tiles) for slot, tiles in found.items()}
