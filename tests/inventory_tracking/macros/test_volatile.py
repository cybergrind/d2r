"""The inventory's volatile cells (macros/volatile.py): the player's items told by the cells they held at the start,
kept across a new game, a loop toggle and a restart of the service; the stats guard for what cannot be undone."""

from dataclasses import replace

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.macros.cube import CUBE_CLASS, loot
from inventory_tracking.macros.loop import Loop
from inventory_tracking.macros.volatile import (
    STORE_FILE,
    Volatile,
    cells_of,
    empty,
    is_players,
    own_of,
    picture,
    print_of,
)


CHARM_SMALL, CHARM_LARGE, CHARM_GRAND, RING = 603, 604, 605, 522
THE_CUBE = Carried(1, CUBE_CLASS, 1, 0, (2, 2))
# The player's charms as at 00:37:16 on 2026-10-19, simplified: a Grand Charm in column 0, charms in columns 5-9
CHARMS = (
    Carried(2, CHARM_GRAND, 0, 0, (1, 3), quality=7, unique=359),
    *(Carried(10 + y * 10 + x, CHARM_SMALL, x, y, (1, 1), quality=4) for x in range(5, 10) for y in range(4)),
)
START = Pack((THE_CUBE, *CHARMS))
LIFE = {7: 35 << 8, 41: 6}  # +35 Life, +6% Fire Resist (a Large Charm's)


def store(tmp_path) -> Volatile:
    return Volatile(tmp_path / STORE_FILE)


def test_the_cells_the_start_left_empty_are_volatile_and_kept(tmp_path):
    cells = store(tmp_path).seed('Cyber', START.items, 'test')

    assert (3, 0) not in cells  # the 2 x 4 block and the 2 x 1 left of it
    assert (4, 3) not in cells
    assert (2, 3) not in cells
    assert (1, 0) in cells
    assert (0, 2) in cells
    assert (9, 3) in cells
    again = store(tmp_path).protected('Cyber')  # another service: the same file
    assert again == cells
    assert picture(cells).split('/')[0] == '###..#####'


def test_a_character_with_none_kept_is_not_seeded_and_reset_forgets(tmp_path):
    kept = store(tmp_path)
    assert kept.protected('Cyber') is None
    kept.seed('Cyber', START.items, 'test')
    assert kept.reset('Cyber')
    assert kept.protected('Cyber') is None


def test_an_item_on_a_protected_cell_is_the_players_one_on_volatile_cells_the_loops(tmp_path):
    cells = store(tmp_path).seed('Cyber', START.items, 'test')
    pickup = Carried(90, RING, 3, 0, (1, 1), quality=4)  # in the 2 x 4 block
    pack = replace(START, items=(*START.items, pickup))

    own = own_of(pack, cells)

    assert loot(pack, own) == [pickup]
    # A charm the player moved into the block is the loop's by its cell: the volatile cells are the loop's
    moved = replace(CHARMS[1], x=4, y=1)
    later = replace(START, items=(THE_CUBE, moved))
    assert moved in loot(later, own_of(later, cells))


def test_an_emptied_protected_cell_is_told(tmp_path):
    cells = store(tmp_path).seed('Cyber', START.items, 'test')
    without = replace(START, items=tuple(i for i in START.items if i.unit_id != 10 + 5))

    assert empty(without, cells) == frozenset({(5, 0)})


def test_the_loop_tells_its_items_from_the_kept_cells_across_a_restart(tmp_path):
    loop = Loop(store=tmp_path / 'loop-items.json')
    loop.tell(START, 'Cyber')
    assert loop.own == own_of(START, loop.volatile.protected('Cyber') or frozenset())

    # A new game, the service restarted (a new Loop): a pickup in the block is the loop's, the charms the player's
    pickup = Carried(90, RING, 3, 0, (1, 1), quality=4)
    pack = replace(START, items=(*START.items, pickup), in_cube=(Carried(91, RING, 0, 0, (1, 1), quality=4),))
    again = Loop(store=tmp_path / 'loop-items.json')
    again.tell(pack, 'Cyber')

    assert loot(pack, again.own or frozenset()) == [pickup]
    assert all((i.txt, i.x, i.y) in (again.own or ()) for i in CHARMS)


def test_the_first_look_seeds_without_the_loops_stored_items_nor_loose_ones(tmp_path):
    rune = Carried(95, 610, 3, 1, (1, 1), quality=2)
    loop = Loop(store=tmp_path / 'loop-items.json')
    loop.tell(replace(START, items=(*START.items, rune)), 'Cyber', loose=frozenset({(610, 3, 1)}))

    assert (3, 1) not in (loop.volatile.protected('Cyber') or frozenset())


def test_the_players_items_are_known_by_their_stats_in_the_cube_too(tmp_path):
    charm = Carried(30, CHARM_LARGE, 6, 2, (1, 2), quality=4)
    start = Pack((THE_CUBE, *CHARMS[:1], charm))
    loop = Loop(store=tmp_path / 'loop-items.json')
    loop.tell(start, 'Cyber', item_stats=lambda unit: dict(LIFE) if unit == 30 else {})

    # The next game: the same charm (a new unit id) moved into the cube by hand
    in_cube = replace(charm, unit_id=77, x=0, y=0)
    assert loop.players_item(in_cube, {**LIFE, 72: 10})  # durability changes: not part of the print
    assert not loop.players_item(replace(in_cube, txt=CHARM_SMALL), {7: 20 << 8})
    assert not loop.players_item(in_cube, {7: 20 << 8})


def test_a_new_item_in_the_same_cell_is_learnt_too(tmp_path):
    # 06:02 on 2026-10-19: the Gheed's swap put the new Gheed's Fortune (36% MF) where the player's old one (34%) was:
    # the same class and cell, so its stats were not learnt; the unit ids tell it
    old = Carried(30, CHARM_LARGE, 6, 2, (1, 2), quality=7)
    loop = Loop(store=tmp_path / 'loop-items.json')
    stats = {30: {80: 34}, 31: {80: 36}}
    loop.tell(Pack((THE_CUBE, *CHARMS[:1], old)), 'Cyber', item_stats=lambda unit: stats.get(unit, {}))
    loop.tell(
        Pack((THE_CUBE, *CHARMS[:1], replace(old, unit_id=31))), 'Cyber', item_stats=lambda unit: stats.get(unit, {})
    )

    assert loop.players_item(replace(old, unit_id=99, x=0, y=0), {80: 36})
    assert loop.players_item(replace(old, unit_id=98, x=0, y=0), {80: 34})


def test_unread_stats_hold_an_item_of_a_players_class_and_quality():
    prints = frozenset({print_of(Carried(1, CHARM_LARGE, 0, 0, (1, 2), quality=4), LIFE)})

    assert is_players(Carried(2, CHARM_LARGE, 0, 0, (1, 2), quality=4), {}, prints)
    assert not is_players(Carried(3, RING, 0, 0, (1, 1), quality=4), {}, prints)
    assert not is_players(Carried(3, RING, 0, 0, (1, 1), quality=4), {}, frozenset())


def test_cells_of_an_item():
    assert cells_of(Carried(1, CHARM_GRAND, 0, 1, (1, 3))) == frozenset({(0, 1), (0, 2), (0, 3)})
