"""Wall library: walkable tiles learned per preset layout, drawn for unvisited rooms of the same layout.

A preset room's walls come from its DS1 file, so (preset, DS1 variant, chunk offset in the preset)
fixes them. Rooms of generated terrain (preset 0) or without a readable variant are never learned.
"""

from inventory_tracking.levels.model import Room, Walkable, pack_cells, pack_tiles
from inventory_tracking.levels.walls import WallLibrary


CAVE_EW = 55


def test_a_layout_seen_once_is_drawn_wherever_it_appears_again(tmp_path):
    library = WallLibrary(tmp_path / 'walls.json')
    seen = Room(CAVE_EW, 100, 200, 8, 8, 1, (100, 200, 8, 8))
    library.learn([seen], [Walkable(100, 200, 8, 8, pack_tiles('10' * 32, 8))])

    elsewhere = Room(CAVE_EW, 40, 16, 8, 8, 1, (40, 16, 8, 8))
    other_variant = Room(CAVE_EW, 48, 16, 8, 8, 0, (48, 16, 8, 8))

    assert library.known([elsewhere, other_variant]) == [Walkable(40, 16, 8, 8, pack_tiles('10' * 32, 8))]


def test_chunks_of_a_large_preset_are_keyed_by_their_offset_in_it(tmp_path):
    library = WallLibrary(tmp_path / 'walls.json')
    block = (100, 200, 16, 16)
    library.learn([Room(618, 108, 200, 8, 8, 1, block)], [Walkable(108, 200, 8, 8, pack_tiles('1' * 64, 8))])

    same_chunk = Room(618, 8, 0, 8, 8, 1, (0, 0, 16, 16))
    other_chunk = Room(618, 0, 0, 8, 8, 1, (0, 0, 16, 16))

    assert library.known([same_chunk, other_chunk]) == [Walkable(8, 0, 8, 8, pack_tiles('1' * 64, 8))]


def test_generated_terrain_and_unknown_variants_are_not_learned(tmp_path):
    library = WallLibrary(tmp_path / 'walls.json')
    rooms = [Room(0, 0, 0, 8, 8), Room(55, 8, 0, 8, 8)]  # preset 0; no variant
    library.learn(rooms, [Walkable(0, 0, 8, 8, pack_tiles('1' * 64, 8)), Walkable(8, 0, 8, 8, pack_tiles('1' * 64, 8))])

    assert library.known(rooms) == []
    assert not (tmp_path / 'walls.json').exists()


def test_the_library_survives_a_restart(tmp_path):
    path = tmp_path / 'walls.json'
    room = Room(CAVE_EW, 100, 200, 8, 8, 1, (100, 200, 8, 8))
    WallLibrary(path).learn([room], [Walkable(100, 200, 8, 8, pack_tiles('0' * 64, 8))])

    assert WallLibrary(path).known([room]) == [Walkable(100, 200, 8, 8, pack_tiles('0' * 64, 8))]


def test_a_grid_that_matches_no_room_is_ignored(tmp_path):
    library = WallLibrary(tmp_path / 'walls.json')
    room = Room(CAVE_EW, 100, 200, 8, 8, 1, (100, 200, 8, 8))

    library.learn([room], [Walkable(300, 200, 8, 8, pack_tiles('1' * 64, 8))])

    assert library.known([room]) == []


def test_a_research_dump_teaches_the_library(tmp_path):
    # Win+C dumps keep collision candidates per loaded Room1 (research.collision_candidates); the
    # confirmed one is Room1 +0x38 -> grid +0x00 bounds, +0x20 mask. Other candidates are ignored.
    import json
    import struct

    from inventory_tracking.levels.walls import learn_from_dumps

    open_cells = [0] * 25 + [1] * 25  # 10x5 sub-tiles: west tile open, east tile rock
    mask = struct.pack('<50H', *[v for row in range(5) for v in open_cells[row * 5 : row * 5 + 5] + [1] * 5])
    candidate = {'room1_offset': 56, 'coords_offset': 0, 'mask_offset': 32, 'origin': [500, 1000], 'size': [10, 5]}
    dump = {
        'evidence': {'rooms': [[CAVE_EW, 100, 200, 2, 1, 1, 100, 200, 2, 1]]},
        'room1s': [
            {'collision': [candidate | {'mask_hex': mask.hex()}]},
            {'collision': [candidate | {'room1_offset': None, 'mask_hex': (b'\0' * 100).hex()}]},
        ],
    }
    path = tmp_path / 'level.json'
    path.write_text(json.dumps(dump))
    library = WallLibrary(tmp_path / 'walls.json')

    assert learn_from_dumps(library, [path]) == 1
    assert library.known([Room(CAVE_EW, 7, 7, 2, 1, 1, (7, 7, 2, 1))]) == [
        Walkable(7, 7, 2, 1, pack_tiles('10', 2), pack_tiles('11', 2))  # the dump's masks: nothing stops a missile
    ]


def test_a_wall_one_sub_tile_thick_is_kept(tmp_path):
    # User, 2026-10-06: a Lower Kurast hut showed one wall of four; the others are one sub-tile
    # thick, which a cell per tile cannot hold.
    library = WallLibrary(tmp_path / 'walls.json')
    room = Room(CAVE_EW, 100, 200, 1, 1, 1, (100, 200, 1, 1))
    thin_wall = pack_cells('01111' * 5)

    library.learn([room], [Walkable(100, 200, 1, 1, thin_wall)])

    assert WallLibrary(tmp_path / 'walls.json').known([room]) == [Walkable(100, 200, 1, 1, thin_wall)]


def test_a_library_of_whole_tiles_is_read_as_sub_tiles_and_saved_that_way(tmp_path):
    import json

    path = tmp_path / 'walls.json'
    path.write_text(json.dumps({'schema_version': 1, 'layouts': {f'{CAVE_EW}:1:0:0:2x1': '10'}}))
    old, new = Room(CAVE_EW, 0, 0, 2, 1, 1, (0, 0, 2, 1)), Room(CAVE_EW, 0, 0, 1, 1, 0, (0, 0, 1, 1))

    library = WallLibrary(path)

    assert library.known([old]) == [Walkable(0, 0, 2, 1, pack_cells('1111100000' * 5))]
    library.learn([new], [Walkable(0, 0, 1, 1, pack_cells('1' * 25))])
    assert json.loads(path.read_text())['schema_version'] == 2
    assert WallLibrary(path).known([old]) == [Walkable(0, 0, 2, 1, pack_cells('1111100000' * 5))]


def test_the_flight_layer_is_learned_from_the_masks_with_door_cells_open(tmp_path):
    from inventory_tracking.levels.model import pack_cells, pack_masks

    # A 1x1 room: the west column blocks walking and missiles (0x5), the east one is a closed door
    # (0x0807, missile-blocking now) that must not stay shut in the library, the rest is floor.
    mask = [0x0005 if c == 0 else 0x0807 if c == 4 else 0x0000 for _ in range(5) for c in range(5)]
    cells = pack_cells(''.join('0' if v & 0x1 else '1' for v in mask))
    flight = pack_cells(''.join('0' if v & 0x4 else '1' for v in mask))
    room = Room(500, 100, 200, 1, 1, 2, (100, 200, 1, 1))
    path = tmp_path / 'walls.json'
    WallLibrary(path).learn([room], [Walkable(100, 200, 1, 1, cells, flight, pack_masks(mask))])

    [known] = WallLibrary(path).known([room])
    assert known.cells == cells
    assert known.masks == ''
    assert known.flight == pack_cells(''.join('0' if c == 0 else '1' for _ in range(5) for c in range(5)))
    assert WallLibrary(path).known([Room(500, 7, 7, 1, 1, 2, (7, 7, 1, 1))])[0].flight == known.flight
