"""The loop's loot into the cube between games (macros/cube.py; routes/lower-kurast-loop-plan.md phase 9)."""

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import CUBE, CUBE_CLASS, INVENTORY, cell_point, own_of, plan, stash
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


def test_only_what_came_since_the_loop_began_moves_smaller_first_into_the_first_free_block():
    pack = Pack((GRAND, THE_CUBE, TOME, KEY, CHARM, RUNE), EMPTY_CUBE)

    assert plan(pack, OWN) == [(RUNE, (0, 0)), (CHARM, (1, 0))]
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
