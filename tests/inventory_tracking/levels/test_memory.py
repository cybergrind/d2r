"""Confirmed level/room chain: current area from player units, preset rooms from the level."""

import struct

import pytest

from inventory_tracking.levels.memory import player_location, preset_rooms
from inventory_tracking.levels.model import Location, Room


TABLE, PLAYER, PATH, ROOM1, ROOM2_A, ROOM2_B, LEVEL = (
    0x100000,
    0x200000,
    0x210000,
    0x300000,
    0x310000,
    0x310200,
    0x400000,
)
PRESET_A, PRESET_B, OBJECT = 0x320000, 0x320100, 0x330000


class Memory:
    def __init__(self):
        self.blocks = {}

    def block(self, address, size):
        self.blocks[address] = bytearray(size)
        return self.blocks[address]

    def read(self, address, size):
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return bytes(data[address - start : address - start + size])
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')


@pytest.fixture
def memory():
    memory = Memory()
    struct.pack_into('<Q', memory.block(TABLE, 1024), 8, PLAYER)
    unit = memory.block(PLAYER, 0x160)
    struct.pack_into('<IIII', unit, 0, 0, 7, 1, 0)
    struct.pack_into('<Q', unit, 0x38, PATH)
    path = memory.block(PATH, 0x28)
    struct.pack_into('<HxxH', path, 0x02, 25450, 5442)
    struct.pack_into('<Q', path, 0x20, ROOM1)
    struct.pack_into('<Q', memory.block(ROOM1, 0x100), 0x18, ROOM2_A)
    for room2, following, preset, x in ((ROOM2_A, ROOM2_B, PRESET_A, 5084), (ROOM2_B, 0, PRESET_B, 5168)):
        data = memory.block(room2, 0x100)
        struct.pack_into('<Q', data, 0x40, preset)
        struct.pack_into('<Q', data, 0x48, following)
        struct.pack_into('<IIII', data, 0x60, x, 1000, 12, 12)
        struct.pack_into('<Q', data, 0x90, LEVEL)
    struct.pack_into('<I', memory.block(PRESET_A, 4), 0, 527)
    struct.pack_into('<I', memory.block(PRESET_B, 4), 0, 510)
    level = memory.block(LEVEL, 0x200)
    struct.pack_into('<Q', level, 0x10, ROOM2_A)
    struct.pack_into('<I', level, 0x1F8, 74)
    return memory


def test_player_location_follows_path_room_level(memory):
    assert player_location(memory.read, TABLE) == Location(74, LEVEL, 25450, 5442)


def test_player_without_a_path_has_no_location(memory):
    struct.pack_into('<Q', memory.blocks[PLAYER], 0x38, 0)

    assert player_location(memory.read, TABLE) is None


def test_preset_rooms_walk_the_level_list(memory):
    assert preset_rooms(memory.read, LEVEL) == [
        Room(527, 5084, 1000, 12, 12),
        Room(510, 5168, 1000, 12, 12),
    ]
    assert Room(527, 5084, 1000, 12, 12).center == (25450.0, 5030.0)


def test_room_from_another_level_is_rejected(memory):
    struct.pack_into('<Q', memory.blocks[ROOM2_B], 0x90, 0x999000)

    with pytest.raises(ValueError, match='does not belong'):
        preset_rooms(memory.read, LEVEL)


def test_preset_object_gives_variant_and_whole_preset_bounds(memory):
    # Record {Def, pad, object}; object {Def, file index, ..., +0x18 x, y, w, h} (dumps 2026-09-30).
    record = memory.block(PRESET_A, 0x10)
    struct.pack_into('<IIQ', record, 0, 864, 0, OBJECT)
    obj = memory.block(OBJECT, 0x28)
    struct.pack_into('<II', obj, 0, 864, 3)
    struct.pack_into('<IIII', obj, 0x18, 2500, 1000, 84, 84)

    first, second = preset_rooms(memory.read, LEVEL)

    assert (first.preset, first.variant, first.block) == (864, 3, (2500, 1000, 84, 84))
    assert (second.variant, second.block) == (None, None)  # no readable object: tolerated


def test_object_of_another_preset_is_ignored(memory):
    record = memory.block(PRESET_A, 0x10)
    struct.pack_into('<IIQ', record, 0, 527, 0, OBJECT)
    struct.pack_into('<II', memory.block(OBJECT, 0x28), 0, 999, 1)

    first, _ = preset_rooms(memory.read, LEVEL)

    assert (first.variant, first.block) == (None, None)


FOREIGN_ROOM, FOREIGN_LEVEL, NEAR_A = 0x500000, 0x510000, 0x340000


def test_rooms_touching_another_level_name_the_area_they_lead_to(memory):
    # Room2 +0x10 neighbour array, +0x18 count, self included (dump 20260930T124726Z-e166c530:
    # edge rooms list Room2s of another level).
    near = memory.block(NEAR_A, 24)
    struct.pack_into('<QQQ', near, 0, ROOM2_A, ROOM2_B, FOREIGN_ROOM)
    struct.pack_into('<QI', memory.blocks[ROOM2_A], 0x10, NEAR_A, 3)
    struct.pack_into('<Q', memory.block(FOREIGN_ROOM, 0x100), 0x90, FOREIGN_LEVEL)
    struct.pack_into('<I', memory.block(FOREIGN_LEVEL, 0x200), 0x1F8, 4)

    first, second = preset_rooms(memory.read, LEVEL)

    assert first.leads_to == (4,)
    assert second.leads_to == ()  # no neighbour list


def test_an_unreadable_neighbour_list_is_tolerated(memory):
    struct.pack_into('<QI', memory.blocks[ROOM2_A], 0x10, 0xDEAD000, 3)

    first, _ = preset_rooms(memory.read, LEVEL)

    assert first.leads_to == ()


def test_room_rows_round_trip_the_exit_areas():
    plain = Room(5, 0, 0, 8, 8, None, None, (4, 17))
    chunked = Room(5, 0, 0, 8, 8, 3, (0, 0, 8, 8), (4,))

    assert Room.from_row(plain.row()) == plain
    assert Room.from_row(chunked.row()) == chunked
    assert Room(5, 0, 0, 8, 8).row() == [5, 0, 0, 8, 8]


GRID, MASK, ROOM1_OTHER, ROOM2_OTHER, OTHER_LEVEL, NEAR_1 = 0x600000, 0x610000, 0x620000, 0x630000, 0x640000, 0x650000


def test_loaded_rooms_give_walkable_tiles_from_their_collision_mask(memory):
    # Win+C dump 20260930T135418Z-6b2890e1 (Cave 2): Room1 +0x38 -> grid {+0x00 x, y, w, h in
    # sub-tiles; +0x20 -> w x h u16 mask}; bit 0x1 blocks walking (the mask drew the cave's walls).
    from inventory_tracking.levels.memory import loaded_walkable
    from inventory_tracking.levels.model import Walkable

    room1 = memory.blocks[ROOM1]
    struct.pack_into('<QI', room1, 0x00, NEAR_1, 0)
    struct.pack_into('<I', room1, 0x40, 2)
    struct.pack_into('<QQ', memory.block(NEAR_1, 16), 0, ROOM1, ROOM1_OTHER)
    struct.pack_into('<Q', room1, 0x38, GRID)
    grid = memory.block(GRID, 0x28)
    struct.pack_into('<IIII', grid, 0, 25000, 5000, 10, 5)  # 2 x 1 tiles
    struct.pack_into('<Q', grid, 0x20, MASK)
    mask = memory.block(MASK, 10 * 5 * 2)
    for row in range(5):
        for column in range(5, 10):  # the east tile is rock; 0x8000 (a unit) does not block
            struct.pack_into('<H', mask, (row * 10 + column) * 2, 0x5)
    struct.pack_into('<H', mask, 0, 0x8000)
    # A neighbour in another level is not read.
    struct.pack_into('<Q', memory.block(ROOM1_OTHER, 0x100), 0x18, ROOM2_OTHER)
    struct.pack_into('<Q', memory.block(ROOM2_OTHER, 0x100), 0x90, OTHER_LEVEL)

    assert loaded_walkable(memory.read, ROOM1, LEVEL) == [Walkable(5000, 1000, 2, 1, '10')]


def test_a_room_without_a_readable_grid_is_skipped(memory):
    from inventory_tracking.levels.memory import loaded_walkable

    struct.pack_into('<Q', memory.blocks[ROOM1], 0x38, 0xDEAD000)

    assert loaded_walkable(memory.read, ROOM1, LEVEL) == []


def test_player_room_is_the_room1_the_location_came_from(memory):
    from inventory_tracking.levels.memory import player_room

    assert player_room(memory.read, TABLE) == (Location(74, LEVEL, 25450, 5442), ROOM1)
