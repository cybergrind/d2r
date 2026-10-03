"""DS1 preset files: warp tiles are special (orientation 10/11) wall tiles whose main index 0-7
is the level's Vis/Warp slot (2026-10-03: Cave Entrance CaveDr1.ds1 main 5 = Cold Plains Vis5)."""

import struct

from inventory_tracking.levels.ds1 import warp_tiles


def cell(main, sub=0):
    return (sub << 8) | ((main & 0xF) << 20) | ((main >> 4) << 24) | 0x81  # prop1 0x81: a tile is set


def ds1(width, height, walls, objects=()):
    """A version-18 DS1: `walls` = one (cells, orientations) pair per wall layer, row by row."""
    w, h = width + 1, height + 1
    # version, width - 1, height - 1, act, tag type, one tile file, wall and floor layer counts
    header = struct.pack('<6i', 18, width, height, 0, 0, 1) + b'x.tg1\0' + struct.pack('<ii', len(walls), 1)
    body = b''
    for cells, orientations in walls:
        body += struct.pack(f'<{w * h}I', *cells) + struct.pack(f'<{w * h}I', *orientations)
    body += struct.pack(f'<{w * h}I', *([0] * w * h)) * 2  # floor, shadow
    body += struct.pack('<i', len(objects)) + b''.join(struct.pack('<5i', *o) for o in objects)
    return header + body


def test_warp_tiles_are_special_wall_tiles_with_a_slot_main_index():
    w = h = 3
    cells, orientations = [0] * (w * h), [0] * (w * h)
    cells[1 * w + 2], orientations[1 * w + 2] = cell(5, 21), 10  # a warp, slot 5, at tile (2, 1)
    cells[2 * w + 0], orientations[2 * w + 0] = cell(8, 23), 10  # main 8: a door marker, not a warp
    cells[0], orientations[0] = cell(30, 0), 10  # main 30: a town marker
    cells[4], orientations[4] = cell(1), 4  # a plain wall

    assert warp_tiles(ds1(2, 2, [(cells, orientations)])) == {5: [(2, 1)]}


def test_a_warp_spans_tiles_in_several_wall_layers():
    w = h = 3
    first, second = ([0] * (w * h), [0] * (w * h)), ([0] * (w * h), [0] * (w * h))
    first[0][4], first[1][4] = cell(0), 11
    second[0][5], second[1][5] = cell(0, 1), 11

    assert warp_tiles(ds1(2, 2, [first, second], objects=[(2, 17, 1, 1, 0)])) == {0: [(1, 1), (2, 1)]}
