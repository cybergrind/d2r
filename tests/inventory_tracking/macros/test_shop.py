"""Town Portal scrolls and keys from Jamella (macros/shop.py; routes/lower-kurast-loop-plan.md phase 8)."""

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.shop import JAMELLA, KEY, SCROLL, restock, short
from inventory_tracking.macros.world import Carried, Monster, Pack, Stocked, Thing
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103
START = (5048.0, 5044.0)  # where every game of 2026-10-15 began, by the waypoint
JAMELLA_AT = (5083.5, 5058.5)  # in 63 of 101 takes of the Fortress
WAYPOINT = Thing(6, 398, 2, 5044.0, 5019.0)
# Her Misc tab as the player's screenshot of 21:16 shows it: the key in the last column's sixth row, the scrolls above
STOCK = (Stocked(KEY, 3, 9, 5), Stocked(SCROLL, 3, 9, 4), Stocked(SCROLL, 3, 9, 3))


def fortress(*, keys: int = 1, portals: int = 2) -> Game:
    jamella = Monster(77, JAMELLA, 1, *JAMELLA_AT, 0xFFFFFFFF)
    play = Game(world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]), monsters=(jamella,)))
    play.vendor, play.stock, play.thing = jamella, STOCK, WAYPOINT
    play.pack = Pack((Carried(1, CUBE_CLASS, 0, 0, (2, 2)),), ('...',) * 4, keys=keys, portals=portals)
    return play


def test_under_three_keys_or_portals_is_short_and_an_unread_count_is_not():
    assert short(Pack(keys=2, portals=20))
    assert short(Pack(keys=12, portals=2))
    assert not short(Pack(keys=3, portals=3))
    assert not short(Pack(keys=None, portals=None))
    assert not short(None)


def test_one_visit_buys_keys_and_scrolls_and_walks_back_to_the_waypoint():
    play = fortress()

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (12, 20)
    assert play.world.open_panels == ()
    assert play.said[0] == 'Shop: 1 keys, 2 portals'
    assert play.said[-1] == 'Shop: 12 keys, 20 portals'
    me = play.character
    assert abs(me.x - WAYPOINT.x) < 40  # back by the waypoint: its click is the next leg's


def test_a_click_beside_the_trade_line_is_not_tried_on_another_line():
    # Gamble is the next line down, and its window is a vendor panel too
    play = fortress()
    play.trade_line_off = 0.03

    with pytest.raises(Abort, match='her trade window did not open'):
        restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (1, 2)
    assert play.world.open_panels == ()


def test_nothing_is_bought_in_a_window_whose_stock_holds_no_key_and_no_scroll():
    play = fortress()
    play.stock = (Stocked(500, 3, 0, 0),)  # not her Misc tab: a gamble's stock, say

    with pytest.raises(Abort, match='no key and no scroll'):
        restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (1, 2)
    assert play.world.open_panels == ()


def test_the_loop_goes_to_her_before_lower_kurast_when_short():
    from inventory_tracking.macros.loop import SHOP, TO_THE_CHESTS, Loop, next_leg
    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress

    here = world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]))
    progress, loop = Progress(ROUTES, PERFORMED), Loop(on=True)
    assert next_leg(here, progress, loop) == TO_THE_CHESTS
    loop.short = True
    assert next_leg(here, progress, loop) == SHOP


def test_a_vendors_grids_give_each_item_its_tab_and_first_cell():
    from inventory_tracking.macros.world import stock_of

    misc = [0] * 100
    misc[5 * 10 + 9] = 0xA  # the key
    misc[3 * 10 + 9] = misc[4 * 10 + 9] = 0xB  # a two-cell item down the last column
    grids = {5: {'width': 10, 'height': 10, 'cells': misc}, 2: {'width': 10, 'height': 10, 'cells': [0] * 100}}
    units = {0xA: {'txt_id': KEY}, 0xB: {'txt_id': SCROLL}}

    assert stock_of(grids, units) == (Stocked(SCROLL, 3, 9, 3), Stocked(KEY, 3, 9, 5))
