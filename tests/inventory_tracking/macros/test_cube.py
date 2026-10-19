"""The loop's loot into the cube between games (macros/cube.py; routes/lower-kurast-loop-plan.md phase 9)."""

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import CUBE, CUBE_CLASS, INVENTORY, cell_point, overflow, own_of, plan, stash
from inventory_tracking.macros.stash import STASH_CUBE, STASH_PAGE
from inventory_tracking.macros.world import Carried, Pack
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


# The inventory of the player's screenshot of 21:16 on 2026-10-16, in part: a grand charm, the cube, the tome, a key
GRAND = Carried(1, class_of('Grand Charm'), 0, 0, (1, 3))
THE_CUBE = Carried(2, CUBE_CLASS, 1, 0, (2, 2))
TOME = Carried(3, class_of('Tome of Town Portal'), 9, 0, (1, 2))
KEY = Carried(4, class_of('Key'), 7, 0, (1, 1))
OWN = own_of((GRAND, THE_CUBE, TOME, KEY))
RUNE = Carried(11, class_of('Io Rune'), 4, 2, (1, 1))  # picked up by the loop
CHARM = Carried(12, class_of('Large Charm'), 5, 0, (1, 2))  # a large charm the loop picked up
EMPTY_CUBE = ('...', '...', '...', '...')


def test_only_what_came_since_the_loop_began_moves_larger_first_into_the_first_free_block():
    pack = Pack((GRAND, THE_CUBE, TOME, KEY, CHARM, RUNE), EMPTY_CUBE)

    assert plan(pack, OWN) == [(CHARM, (0, 0)), (RUNE, (1, 0))]
    assert plan(Pack((GRAND, THE_CUBE, TOME, KEY), EMPTY_CUBE), OWN) == []
    # The cube, a tome and the keys never move, even ones the loop did not see at its start
    spare_key, book = Carried(5, class_of('Key'), 8, 3, (1, 1)), Carried(6, class_of('Tome of Identify'), 6, 2, (1, 2))
    assert plan(Pack((spare_key, book), EMPTY_CUBE), OWN) == []


def test_what_fits_nowhere_in_the_cube_stays_and_no_cube_moves_nothing():
    full = ('###', '###', '###', '##.')
    assert plan(Pack((CHARM, RUNE), full), OWN) == [(RUNE, (2, 3))]
    assert plan(Pack((CHARM, RUNE), None), OWN) == []


def test_the_grids_are_where_the_layout_puts_them():
    window = (1920, 0, 2560, 1418)
    # The screenshot of 21:16 (2000 x 1125 of the 2560 x 1440 output, its top 22 pixels the desktop's bar): the
    # inventory's first cell centred at (1358, 605) of it
    x, y = cell_point(window, INVENTORY, (0, 0))
    assert x * 2000 == pytest.approx(1358, abs=3)
    assert (y * 1418 + 22) / 1.28 == pytest.approx(605, abs=4)
    # The cube's grid: 3 x 4 at (431, 534) of the left panel
    left, top = cell_point(window, CUBE, (0, 0), (0, 0))
    assert left == pytest.approx((236 + 431) * 1418 / 2160 / 2560)
    assert top == pytest.approx(0.397 + (534 - 651) / 2160)


@pytest.mark.parametrize(
    ('grid', 'at', 'pixel'),
    [
        (INVENTORY, (0, 0), (1725.3, 768.3)),
        (INVENTORY, (9, 3), (2313.3, 964.3)),
        (CUBE, (0, 0), (477.3, 526.3)),
        (CUBE, (2, 3), (608.0, 722.3)),
        (STASH_PAGE, (0, 0), (249.3, 316.3)),
        (STASH_PAGE, (9, 9), (837.3, 904.3)),
        (STASH_CUBE, (0, 0), (477.3, 693.0)),
    ],
)
def test_each_panels_corner_cells_sit_at_their_pinned_pixel(grid, at, pixel):
    # Literal pixels of a 2560 x 1440 window, as the live loop clicked them on 2026-10-19: the fakes compute their
    # clicks from these same constants (fakes.py), so a moved panel origin would pass every other test
    x, y = cell_point((0, 0, 2560, 1440), grid, at)
    assert (x * 2560, y * 1440) == pytest.approx(pixel, abs=0.1)


def fortress(pack: Pack) -> Game:
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.pack = pack
    return play


def test_the_loops_items_go_into_the_cube_and_the_panels_are_closed_again():
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, CHARM, RUNE), EMPTY_CUBE))

    moved = stash(play.run(), 'i', OWN)

    assert moved == 2
    assert play.pack is not None
    assert {item.unit_id for item in play.pack.items} == {1, 2, 3, 4}
    assert play.pack.cube_items == {RUNE.unit_id, CHARM.unit_id}
    assert play.cursor is None
    assert play.world.open_panels == ()
    assert play.said[-1] == 'Cube: 2 items put in'


def test_an_item_the_cube_does_not_take_is_put_back_and_the_run_stops():
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, RUNE), EMPTY_CUBE))
    play.cube_refuses = True

    with pytest.raises(Abort, match='did not go into the cube'):
        stash(play.run(), 'i', OWN)

    assert play.cursor is None  # nothing left on the pointer
    assert play.pack is not None
    assert RUNE in play.pack.items
    assert play.world.open_panels == ()


def test_with_nothing_of_the_loops_nothing_is_opened():
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY), EMPTY_CUBE))

    assert stash(play.run(), 'i', OWN) == 0
    assert play.pressed() == []


def test_the_grids_give_each_item_its_first_cell_and_the_cubes_rows():
    from inventory_tracking.macros.world import pack_of

    width = 10
    cells = [0] * (width * 4)
    for x, y in ((0, 0), (0, 1), (0, 2)):  # a grand charm down the first column
        cells[y * width + x] = 0xA
    for x, y in ((1, 0), (2, 0), (1, 1), (2, 1)):  # the cube, 2 x 2
        cells[y * width + x] = 0xB
    cells[2 * width + 4] = 0xC  # a rune
    cube = [0] * 12
    cube[0] = 0xD
    units = {
        0xA: {'unit_id': 1, 'txt_id': class_of('Grand Charm')},
        0xB: {'unit_id': 2, 'txt_id': CUBE_CLASS},
        0xC: {'unit_id': 3, 'txt_id': class_of('Io Rune')},
        0xD: {'unit_id': 4, 'txt_id': class_of('Ist Rune')},
    }
    grids = {2: {'width': width, 'height': 4, 'cells': cells}, 5: {'width': 3, 'height': 4, 'cells': cube}}

    pack = pack_of(grids, units)

    assert pack is not None
    assert [(item.unit_id, item.x, item.y, item.size) for item in pack.items] == [
        (1, 0, 0, (1, 3)), (2, 1, 0, (2, 2)), (3, 4, 2, (1, 1)),
    ]  # fmt: skip
    assert pack.cube == ('#..', '...', '...', '...')
    assert pack.cube_items == {4}
    assert pack_of({}, units) is None


def test_an_inventory_that_does_not_open_is_not_followed_by_escape():
    # Escape with nothing open opens the game's menu
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, RUNE), EMPTY_CUBE))

    with pytest.raises(Abort, match='the inventory did not open'):
        stash(play.run(), 'b', OWN)  # a key the fake game does not take

    assert play.world.open_panels == ()


def test_a_full_cube_is_said_and_nothing_is_opened():
    # The player, 2026-10-16: "moving items to the cube from inventory - seems not working. or working not always";
    # games 8 to 17 of 22:50 that day left with the loop's items and not a word
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, RUNE), ('###',) * 4))

    assert stash(play.run(), 'i', OWN) == 0
    assert play.pressed() == []
    assert play.said[-1] == "Cube full: 1 of the loop's items stay in the inventory"


def test_the_loops_items_stay_the_loops_from_one_loop_to_the_next_and_one_service_to_the_next(tmp_path):
    from inventory_tracking.macros.loop import Loop

    store = tmp_path / 'loop-items.json'
    loop = Loop(store=store)
    loop.start()
    loop.sort(own_of((GRAND, THE_CUBE, TOME, KEY)), 'CybergrindAA')
    loop.sort(own_of((GRAND, THE_CUBE, TOME, KEY, RUNE)), 'CybergrindAA')  # the rune picked up, the cube full
    assert loop.mine == own_of((RUNE,))

    loop.stop()
    loop.start()  # KP_6 off and on: the rune is still the loop's
    loop.sort(own_of((GRAND, THE_CUBE, TOME, KEY, RUNE)), 'CybergrindAA')
    assert loop.own == OWN

    later = Loop(store=store)  # the service started again
    later.start()
    later.sort(own_of((GRAND, THE_CUBE, TOME, KEY, RUNE, CHARM)), 'CybergrindAA')
    assert later.own == OWN | own_of((CHARM,))  # a charm the player put in meanwhile is theirs
    assert later.mine == own_of((RUNE,))


def test_an_empty_cube_whose_grid_reads_as_none_takes_the_loops_items():
    # 23:28 on 2026-10-16, every game: "the cube's grid is not read" with the cube empty (an empty grid has no cells,
    # and the grids read leave it out); the player: "still we don't use cube and it is empty"
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, CHARM, RUNE), None))

    assert stash(play.run(), 'i', OWN) == 2
    assert play.pack is not None
    assert play.pack.cube_items == {RUNE.unit_id, CHARM.unit_id}
    assert play.world.open_panels == ()


def test_a_cube_item_the_inventory_has_no_block_for_is_not_clicked():
    # 14:51:04-14 on 2026-10-17: with two cells free, three items were clicked for 3 s each before the stash
    from inventory_tracking.macros.cube import unpack

    filler = Carried(20, class_of('Grand Charm'), 0, 0, (1, 1))
    full = tuple(
        Carried(30 + x + 10 * y, filler.txt, x, y, (1, 1)) for y in range(4) for x in range(10) if (x, y) != (9, 3)
    )  # one cell free, (9, 3)
    blade = Carried(41, class_of('Blade'), 0, 0, (1, 3))
    rune = Carried(42, class_of('Io Rune'), 1, 0, (1, 1))
    cube = Carried(2, CUBE_CLASS, 0, 0, (2, 2))
    play = fortress(
        Pack((cube, *full[1:]), ('##.', '#..', '#..', '...'), in_cube=(blade, rune), cube_items=frozenset({41, 42}))
    )

    out = unpack(play.run(), 'i', [blade, rune])

    assert out == 1
    assert play.pack is not None
    assert play.pack.cube_items == {41}  # the Blade stays for the session's second stash
    from tests.inventory_tracking.macros.fakes import WINDOW

    at = cell_point(WINDOW, CUBE, (blade.x, blade.y), blade.size)
    on_blade = [
        e for e in play.keys.events if e[0] == 'click' and abs(e[1][0] - at[0]) < 0.01 and abs(e[1][1] - at[1]) < 0.02
    ]
    assert not on_blade


def test_an_empty_cube_takes_a_rune_a_one_by_three_and_a_two_by_two():
    # 16:39:01 on 2026-10-17: smaller first put the rune at (0, 0) and the Stilleto in the second column, the Antlers
    # fit nowhere, and the room read as low sent the loop to a whole trade session one game after the last
    stilleto = Carried(21, class_of('Stilleto'), 2, 2, (1, 3))
    antlers = Carried(22, class_of('Antlers'), 3, 2, (2, 2))
    rune = Carried(23, class_of('Io Rune'), 5, 2, (1, 1))
    pack = Pack((GRAND, THE_CUBE, TOME, KEY, stilleto, antlers, rune), EMPTY_CUBE)
    assert len(plan(pack, OWN)) == 3
    assert not overflow(pack, OWN)


def test_a_key_stack_that_splits_the_free_cells_is_moved_to_make_the_largest_block():
    # The player, 19:10 on 2026-10-17: "move key two cells left to make continuous 2x4 space"
    from dataclasses import replace

    from inventory_tracking.macros.cube import KEY_CLASS, arrange_keys, keys_move

    rest = Carried(30, 600, 4, 0, (6, 4))  # columns 4-9 taken: 16 cells free in columns 0-3
    stack = Carried(32, KEY_CLASS, 1, 1, (1, 1))  # in the middle of them
    pack = Pack((rest, stack))
    assert pack.inventory.largest_block() == 8
    move = keys_move(pack)
    assert move is not None
    assert move[0] is stack
    assert Pack((rest,)).inventory.take(move[1], (1, 1)).largest_block() == 12  # a 3 x 4 block beside it
    assert keys_move(Pack((rest, replace(stack, x=0, y=0)))) is None  # in a corner already: nothing better

    play = Game(world(103, player=player(103, x=5048.0, y=5044.0)))
    play.pack = pack
    assert arrange_keys(play.run(), 'i')
    moved = next(i for i in play.pack.items if i.unit_id == stack.unit_id)
    assert (moved.x, moved.y) == move[1]
    assert 'inventory' not in play.world.open_panels


def test_an_item_taken_only_to_identify_is_dropped_for_a_grand_charms_block():
    # 21:00:03 on 2026-10-17: the cube took what it could, no 1 x 3 block was left, and the loop stopped with a Grand
    # Charm on the ground. A magic dagger taken to identify (its loss costs a game nothing) is dropped for it
    from inventory_tracking.macros.cube import SURE_BLOCK, drop_for, droppable

    own = tuple(Carried(40 + x, 999 - x, x, 1, (1, 2)) for x in range(1, 10))  # the player's: rows 1-2 of columns 1-9
    dagger = Carried(50, 135, 0, 0, (1, 3), quality=4, identified=False)  # a magic Stilleto, the loop's: column 0
    charm = Carried(51, 618, 0, 3, (1, 1), quality=4, identified=False)  # a Small Charm, the loop's: a sure valuable
    kept = own_of(own)
    pack = Pack((*own, dagger, charm))
    assert not pack.inventory.has_room(SURE_BLOCK)
    assert droppable(pack, kept, SURE_BLOCK) is dagger
    assert droppable(Pack((*own, charm)), kept, SURE_BLOCK) is None  # room already: nothing dropped
    grand = Carried(52, 620, 0, 0, (1, 3), quality=4, identified=False)  # a Grand Charm in the dagger's place
    assert droppable(Pack((*own, grand, charm)), kept, SURE_BLOCK) is None  # a sure valuable is never dropped
    assert droppable(pack, kept | own_of((dagger,)), SURE_BLOCK) is None  # nor the player's own

    play = Game(world(79, player=player(79, x=5029.0, y=2860.0)))
    play.pack = pack
    assert drop_for(play.run(), 'i', kept, SURE_BLOCK) == dagger
    assert play.fallen == [dagger]
    assert play.pack.inventory.has_room(SURE_BLOCK)
    assert 'inventory' not in play.world.open_panels


# -- a full stack's flawless gems: three into a perfect one (the player, 2026-10-17: "for gems - we need to cube 3
# flawless -> perfect"; the Flawless Ruby and Sapphire stacks full at 04:30:31 on 2026-10-18) --

FLAWLESS_RUBY, PERFECT_RUBY = class_of('Flawless Ruby'), class_of('Perfect Ruby')


def rubies(*cells: tuple[int, int]) -> tuple[Carried, ...]:
    return tuple(Carried(40 + n, FLAWLESS_RUBY, x, y, (1, 1)) for n, (x, y) in enumerate(cells))


def test_three_flawless_gems_go_alone_into_the_cube_and_transmute_into_a_perfect_one():
    from inventory_tracking.macros.cube import perfect_of, transmute

    assert perfect_of(FLAWLESS_RUBY) == PERFECT_RUBY
    assert perfect_of(class_of('Perfect Ruby')) is None
    assert perfect_of(RUNE.txt) is None
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, *rubies((4, 2), (5, 2), (6, 2), (7, 2))), EMPTY_CUBE))

    assert transmute(play.run(), 'i', FLAWLESS_RUBY)

    assert play.transmutes == [(FLAWLESS_RUBY,) * 3]  # the button clicked with the three alone in the cube
    assert play.pack is not None
    assert [item.txt for item in play.pack.in_cube] == [PERFECT_RUBY]
    assert sum(item.txt == FLAWLESS_RUBY for item in play.pack.items) == 1  # the fourth stays
    assert play.world.open_panels == ()


def test_what_the_inventory_has_no_room_for_is_put_down_while_the_cube_transmutes():
    # 09:22-09:45 on 2026-10-18: 19 flawless gems of full stacks, the cube full of them, no transmute had the room to
    # empty it (the player: "drop on the ground then pickup and move to cube")
    from inventory_tracking.macros.cube import transmute

    emerald = class_of('Flawless Emerald')
    others = tuple(Carried(60 + n, emerald, n % 3, 1 + n // 3, (1, 1)) for n in range(9))
    cubed = (*rubies((0, 0), (1, 0), (2, 0)), *others)
    # the inventory: the player's, with two cells free
    own = tuple(Carried(80 + n, 999, n % 10, n // 10, (1, 1)) for n in range(38) if n not in (1, 2, 11, 12))
    play = fortress(Pack(()))
    play.pack = Pack(
        (THE_CUBE, *own), ('###',) * 4, in_cube=cubed, cube_items=frozenset(i.unit_id for i in cubed),
    )  # fmt: skip
    parked: list[int] = []

    assert transmute(play.run(), 'i', FLAWLESS_RUBY, parked.append)

    assert play.transmutes == [(FLAWLESS_RUBY,) * 3]
    assert len(parked) == 7  # two out into the inventory
    assert {i.unit_id for i in play.fallen} == set(parked)
    assert play.pack is not None
    assert [i.txt for i in play.pack.in_cube] == [PERFECT_RUBY]
    assert play.cursor is None
    assert play.world.open_panels == ()
    full = fortress(Pack(()))
    full.pack = Pack((THE_CUBE, *own), ('###',) * 4, in_cube=cubed, cube_items=frozenset(i.unit_id for i in cubed))
    assert not transmute(full.run(), 'i', FLAWLESS_RUBY)  # no `park`: nothing put down, not clicked
    assert full.fallen == []
    assert full.transmutes == []


def test_what_else_is_in_the_cube_comes_out_first_and_with_too_few_gems_nothing_is_clicked():
    from inventory_tracking.macros.cube import transmute

    cubed = (Carried(50, class_of('Large Charm'), 2, 0, (1, 2)), *rubies((0, 0), (1, 0)))
    play = fortress(Pack(()))
    play.pack = Pack(
        (GRAND, THE_CUBE, TOME, KEY, Carried(43, FLAWLESS_RUBY, 4, 2, (1, 1))),
        ('###', '#..', '...', '...'),
        in_cube=cubed,
        cube_items=frozenset(i.unit_id for i in cubed),
    )

    assert transmute(play.run(), 'i', FLAWLESS_RUBY)

    assert play.transmutes == [(FLAWLESS_RUBY,) * 3]  # the charm out before the click
    assert play.pack is not None
    assert any(item.unit_id == 50 for item in play.pack.items)
    few = fortress(Pack((GRAND, THE_CUBE, *rubies((4, 2), (5, 2))), EMPTY_CUBE))
    assert not transmute(few.run(), 'i', FLAWLESS_RUBY)
    assert few.transmutes == []
    assert few.keys.events == []


def test_the_keys_move_out_of_the_only_two_by_four_block_before_a_larger_square():
    # 12:36 on 2026-10-18: a Unique Brandistock (2 x 4) found no room; the loop's keys at (3, 0) stood in columns 3-4,
    # the only 2 x 4 the player's charms leave (the player: "in this particular case we even have all the required
    # space to get it inside the inventory")
    from inventory_tracking.macros.cube import BIG_BLOCK, KEY_CLASS, keys_move

    def at(unit, x, y, size=(1, 1), txt=603):
        return Carried(unit, txt, x, y, size)

    items = (
        at(1, 0, 0, (1, 3), 620), at(2, 1, 0, (2, 2), 564), at(3, 3, 0, txt=KEY_CLASS), at(4, 5, 0), at(5, 6, 0),
        at(6, 7, 0, txt=KEY_CLASS), at(7, 8, 0, (1, 2), 534), at(8, 9, 0), at(9, 5, 1, (1, 3), 620), at(10, 6, 1),
        at(11, 7, 1), at(12, 9, 1), at(13, 1, 2, (1, 2), 604), at(14, 6, 2, (1, 2), 604), at(15, 7, 2),
        at(16, 8, 2, (1, 2), 604), at(17, 9, 2), at(18, 0, 3), at(19, 7, 3), at(20, 9, 3),
    )  # fmt: skip
    pack = Pack(items)
    assert not pack.inventory.has_room(BIG_BLOCK)
    move = keys_move(pack)
    assert move is not None
    key, cell = move
    assert (key.x, key.y) == (3, 0)
    without = Pack(tuple(i for i in items if i is not key))
    assert without.inventory.take(cell, (1, 1)).has_room(BIG_BLOCK)


def test_only_the_wanted_loop_items_go_into_the_cube():
    """A fourth kept Flawless Ruby left carried after a transmute (07:26 on 2026-10-19: the block taken) goes into the
    cube alone; the loop's other items stay where they are; with none wanted nothing is opened."""
    from inventory_tracking.macros.cube import stash_only

    gem = rubies((4, 2))[0]
    play = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, CHARM, gem), EMPTY_CUBE))

    assert stash_only(play.run(), 'i', OWN, lambda item: item.txt == FLAWLESS_RUBY) == 1

    assert play.pack is not None
    assert play.pack.cube_items == {gem.unit_id}
    assert CHARM in play.pack.items
    assert play.world.open_panels == ()
    idle = fortress(Pack((GRAND, THE_CUBE, TOME, KEY, CHARM), EMPTY_CUBE))
    assert stash_only(idle.run(), 'i', OWN, lambda item: item.txt == FLAWLESS_RUBY) == 0
    assert idle.pressed() == []


def test_no_action_gives_up_an_item_the_guard_protects(caplog):
    # Every action that gives an item up asks engine.py `protected` first (cleanup-plan.md phase 0): with every item
    # the player's, nothing is dropped nor put down; the sale's own test is test_shop's
    from inventory_tracking.macros.cube import SURE_BLOCK, drop_for, transmute

    own = tuple(Carried(40 + x, 999 - x, x, 1, (1, 2)) for x in range(1, 10))
    dagger = Carried(50, 135, 0, 0, (1, 3), quality=4, identified=False)
    charm = Carried(51, 618, 0, 3, (1, 1), quality=4, identified=False)
    play = Game(world(79, player=player(79, x=5029.0, y=2860.0)))
    play.pack = Pack((*own, dagger, charm))
    run = play.run()
    run.players_item = lambda _item: True
    assert drop_for(run, 'i', own_of(own), SURE_BLOCK) is None
    assert play.fallen == []

    emerald = class_of('Flawless Emerald')
    others = tuple(Carried(60 + n, emerald, n % 3, 1 + n // 3, (1, 1)) for n in range(9))
    cubed = (*rubies((0, 0), (1, 0), (2, 0)), *others)
    mine = tuple(Carried(80 + n, 999, n % 10, n // 10, (1, 1)) for n in range(38) if n not in (1, 2, 11, 12))
    full = fortress(Pack(()))
    full.pack = Pack(
        (THE_CUBE, *mine), ('###',) * 4, in_cube=cubed, cube_items=frozenset(i.unit_id for i in cubed),
    )  # fmt: skip
    run = full.run()
    run.kept_item = lambda _item: '+2 skills'
    parked: list[int] = []
    with caplog.at_level('INFO'):
        assert not transmute(run, 'i', FLAWLESS_RUBY, parked.append)
    assert 'is kept by its stats (+2 skills): never put down' in caplog.text
    assert parked == []
    assert full.fallen == []


def test_an_inventory_already_open_is_not_closed_by_its_key():
    # cube.py tapped the inventory key unconditionally: with the inventory open the tap closed it (rca/2026-10-19
    # cleanup/tests.md gaps); `open_inventory` taps only a closed one
    from dataclasses import replace

    from inventory_tracking.macros.cube import unpack

    rune = Carried(42, class_of('Io Rune'), 1, 0, (1, 1))
    cube = Carried(2, CUBE_CLASS, 0, 0, (2, 2))
    play = fortress(Pack((cube,), ('...',) * 4, in_cube=(rune,), cube_items=frozenset({42})))
    play.world = replace(play.world, open_panels=('inventory',))

    assert unpack(play.run(), 'i', [rune]) == 1
    assert 'i' not in play.pressed()
