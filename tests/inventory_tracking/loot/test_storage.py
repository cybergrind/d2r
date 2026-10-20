"""The loop's room (loot/storage.py `room`, `room_low`, `occupied`; loot/design.md §2.3, §7 M3): the count the town
visit waits on, the player's rule kept (§8 Q3: town when under TRADE_ROOM cells free, or no 1 x 3 free), and the share
of the loop's room its items take. The planning moved from cube.py and town.py is replayed in test_storage_replay.py.
"""

import pytest

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import storage
from inventory_tracking.loot.storage import (
    CUBE_CLASS,
    TRADE_ROOM,
    Room,
    Storage,
    cells_low,
    occupied,
    room,
    room_low,
)
from inventory_tracking.macros import cube, town


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


THE_CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
TOME = Carried(2, class_of('Tome of Town Portal'), 9, 0, (1, 2))
GRAND = Carried(3, class_of('Grand Charm'), 2, 0, (1, 3))  # the player's
OWN = frozenset((i.txt, i.x, i.y) for i in (THE_CUBE, TOME, GRAND))
EMPTY_CUBE = ('...', '...', '...', '...')
FULL_CUBE = ('###', '###', '###', '###')


def loop_item(unit: int, x: int, y: int, size: tuple[int, int]) -> Carried:
    return Carried(unit, class_of('Large Charm') if size == (1, 2) else class_of('Ring'), x, y, size)


def test_the_moved_names_are_the_same_objects_in_cube_and_town():
    # Thin re-exports: every importer of cube.py and town.py keeps working
    for name in ('plan', 'overflow', 'keys_move', 'loot', 'roomed', 'KEPT', 'SURE_BLOCK', 'BIG_BLOCK', 'perfect_of'):
        assert getattr(cube, name) is getattr(storage, name)
    for name in ('place', 'surplus', 'after', 'Holdings', 'StashStop', 'Put', 'TRADE_ROOM', 'PARK_JUNK', 'BER'):
        assert getattr(town, name) is getattr(storage, name)


def test_room_counts_the_inventory_and_the_cube_together():
    pack = Pack((THE_CUBE, TOME, GRAND, loop_item(10, 4, 0, (1, 1))), EMPTY_CUBE)
    # 40 cells less 4 + 2 + 3 + 1 carried; the cube's 12 free
    assert room(Storage(pack, OWN)) == Room(30, 12, 42, EMPTY_CUBE)
    assert not room_low(Storage(pack, OWN))


def test_an_unread_cube_grid_of_a_carried_cube_is_empty_and_no_cube_is_no_cube_room():
    pack = Pack((THE_CUBE, TOME), None)
    assert room(Storage(pack, OWN)).cube == 12
    no_cube = Pack((TOME,), None)
    assert room(Storage(no_cube, OWN)) == Room(38, 0, 38, ())


def test_under_trade_room_cells_free_is_low():
    # The inventory filled but for 5 cells, the cube full: 5 < TRADE_ROOM
    rows = [loop_item(10 + n, x, y, (1, 1)) for n, (x, y) in enumerate((x, y) for y in range(4) for x in range(3, 9))]
    filler = [*rows, loop_item(40, 9, 2, (1, 1)), loop_item(41, 9, 3, (1, 1))]
    pack = Pack((THE_CUBE, TOME, GRAND, *filler), FULL_CUBE)
    space = room(Storage(pack, OWN))
    assert (space.inventory, space.cube) == (40 - 4 - 2 - 3 - 26, 0)
    assert space.free < TRADE_ROOM
    assert space.low
    assert room_low(Storage(pack, OWN))


def test_cube_room_in_pieces_no_loop_item_fits_is_no_room():
    # 7 inventory cells free (under TRADE_ROOM), 6 in the cube with a 1 x 3 among them, but the loop's 2 x 2 fits
    # nowhere in it: the inventory's 7 alone count
    pieces = ('.#.', '.#.', '.#.', '###')
    big = Carried(20, class_of('Ring'), 3, 0, (2, 2))
    singles = [
        loop_item(30 + n, x, y, (1, 1)) for n, (x, y) in enumerate((x, y) for y in range(4) for x in range(5, 9))
    ]
    singles += [loop_item(50 + n, 3, y, (1, 1)) for n, y in enumerate((2, 3))]
    singles += [loop_item(60 + n, 4, y, (1, 1)) for n, y in enumerate((2, 3))]
    pack = Pack((THE_CUBE, TOME, GRAND, big, *singles), pieces)
    space = room(Storage(pack, OWN))
    assert space.inventory < TRADE_ROOM
    assert cube.overflow(pack, OWN)
    assert space.free == space.inventory
    assert space.low


def test_no_sure_block_free_anywhere_is_low_whatever_the_count():
    # 19 cells free in the inventory, none three down; the cube's 3 free cells a row: no 1 x 3 anywhere
    checker = [loop_item(70 + n, x, y, (1, 1)) for n, (x, y) in enumerate(
        (x, y) for y in range(4) for x in range(3, 9) if (x + y) % 2 == 0
    )]  # fmt: skip
    pack = Pack((THE_CUBE, TOME, GRAND, *checker), ('###', '###', '###', '...'))
    space = room(Storage(pack, OWN))
    assert space.inventory + space.cube >= TRADE_ROOM
    assert space.free == TRADE_ROOM - 1
    assert room_low(Storage(pack, OWN))


def test_cells_low_is_trade_room():
    assert cells_low(TRADE_ROOM - 1)
    assert not cells_low(TRADE_ROOM)


def test_occupied_is_the_share_of_the_loops_room_its_items_take():
    # The loop's room: 40 cells less the player's 4 + 2 + 3 = 31 in the inventory, and the cube's 12
    empty = Pack((THE_CUBE, TOME, GRAND), EMPTY_CUBE)
    assert occupied(Storage(empty, OWN)) == 0.0
    charm = loop_item(10, 4, 0, (1, 2))
    cubed = ('##.', '...', '...', '...')  # two cells taken in the cube
    assert occupied(Storage(Pack((THE_CUBE, TOME, GRAND, charm), cubed), OWN)) == pytest.approx(4 / 43)
    # The player's items never count as the loop's
    assert occupied(Storage(Pack((THE_CUBE, TOME, GRAND), cubed), OWN)) == pytest.approx(2 / 43)


def test_occupied_with_no_room_at_all_is_full():
    every = [loop_item(n, x, y, (1, 1)) for n, (x, y) in enumerate((x, y) for y in range(4) for x in range(10))]
    assert occupied(Storage(Pack(tuple(every)), frozenset((i.txt, i.x, i.y) for i in every))) == 1.0
    assert occupied(Storage(Pack(tuple(every)), frozenset())) == 1.0
