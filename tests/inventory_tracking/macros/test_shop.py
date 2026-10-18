"""Town Portal scrolls and keys from Jamella (macros/shop.py; routes/lower-kurast-loop-plan.md phase 8)."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.portal import FROM_SLING
from inventory_tracking.macros.shop import JAMELLA, KEY, SCROLL, restock, short
from inventory_tracking.macros.skills import SLING_TOWN_PORTAL
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


def test_with_the_slings_town_portal_the_portals_are_no_stock_and_the_keys_still_are():
    # The player, 2026-10-18: "when we have sling ring equipped - we don't need to run any logic in regard of town
    # portal (do not track, do not buy)"
    assert not short(Pack(keys=12, portals=0), FROM_SLING)  # no tome carried
    assert not short(Pack(keys=12, portals=None), FROM_SLING)
    assert short(Pack(keys=2, portals=20), FROM_SLING)
    assert short(Pack(keys=12, portals=0))  # the tome's, as before


def test_with_the_sling_worn_and_no_tome_a_visit_buys_keys_and_no_scroll():
    play = fortress(keys=1, portals=0)  # no tome: `carried_items` reads 0
    play.worn = frozenset({SLING_TOWN_PORTAL})

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 0)  # a scroll clicked would read 20 in the fake
    scrolls = {(item.x, item.y) for item in STOCK if item.txt == SCROLL}
    buys = [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]
    assert buys
    assert all(play.stock_cell(*e[2]) not in scrolls for e in buys)  # the keys' alone
    assert play.said[0] == 'Shop: 1 keys, portals from the Sling'
    assert play.said[-1] == 'Shop: 24 keys, portals from the Sling'


def test_one_visit_buys_keys_and_scrolls_and_walks_back_to_the_waypoint():
    play = fortress()

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)
    assert play.world.open_panels == ()
    assert play.said[0] == 'Shop: 1 keys, 2 portals'
    assert play.said[-1] == 'Shop: 24 keys, 20 portals'
    me = play.character
    assert abs(me.x - WAYPOINT.x) < 40  # back by the waypoint: its click is the next leg's


def test_she_is_clicked_where_she_is_drawn_as_she_walks():
    # The player, 2026-10-16: "they are moving, so you cannot expect to find them at the same location"
    play = fortress()
    play.vendor_drift = 1.5

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)
    assert play.vendor is not None
    assert play.vendor.x > JAMELLA_AT[0] + 1.0


def test_she_is_clicked_when_the_games_record_does_not_name_her_and_her_menu_says_it_took():
    # 23:07:04 on 2026-10-16: the record named her at none of the three aims and the loop stopped with no click
    play = fortress()
    play.vendor_named = False

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)


def test_a_full_key_stack_is_not_bought_again_and_each_buy_is_checked_by_the_count():
    # The player: "when you buy tp scrolls or keys: check inventory number. you can bulk buy with (shift+right click)"
    play = fortress(keys=24, portals=2)  # two stacks full (shop.py KEYS_WANTED)
    assert play.pack is not None
    play.pack = replace(play.pack, key_room=False)  # every stack full: a key bought would take a new cell
    play.full = {SCROLL: ('portals', 20)}

    restock(play.run())

    assert (play.pack.keys, play.pack.portals) == (24, 20)
    buys = [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]
    assert len(buys) == 1  # the scrolls only


def test_a_buy_the_count_does_not_show_is_made_once_more_and_no_more():
    play = fortress()
    play.full = {SCROLL: ('portals', 20)}  # her key does not come, click as it may

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (1, 20)
    buys = [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]
    assert len(buys) == 3  # the key twice, the scrolls once


def test_her_stock_is_waited_for_after_her_trade_window_shows():
    # 23:57:55 and 23:58:04 on 2026-10-16: read 0.05 and 0.1 s after her window showed, her stock held nothing and the
    # loop stopped on "not her trade window"
    play = fortress()
    play.stock_delay = 0.5

    restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)


def test_her_menu_open_already_is_not_clicked_shut():
    # 23:57:48 on 2026-10-16: the walk click toward her landed on her and the game opened her menu as it walked the
    # character there; the click on her body that followed closed it
    play = fortress()
    me = replace(play.character, x=JAMELLA_AT[0] - 3.0, y=JAMELLA_AT[1])
    play.world = replace(play.world, player=me, open_panels=('npc_interact',))

    restock(play.run())

    assert play.menu_shut == 0
    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)


def test_a_click_beside_the_trade_line_is_not_tried_on_another_line():
    # Gamble is the next line down, and its window is a vendor panel too
    play = fortress()
    play.trade_line_off = 0.03

    with pytest.raises(Abort, match='her trade window did not open'):
        restock(play.run())

    assert play.pack is not None
    assert (play.pack.keys, play.pack.portals) == (1, 2)
    assert play.world.open_panels == ()


def test_the_trade_line_half_a_line_off_the_measured_place_is_found_and_kept():
    # 00:37:00 on 2026-10-17: the click TRADE_ABOVE over her opened Gamble, the next line (the player: "maybe clicks a
    # few pixels off")
    from inventory_tracking.macros import shop

    play = fortress()
    play.trade_line_off = -0.016  # her Trade line about half a line higher than measured
    shop.LIFT = shop.TRADE_ABOVE
    try:
        restock(play.run())
        assert play.pack is not None
        assert (play.pack.keys, play.pack.portals) == (24, 20)  # two stacks (shop.py KEYS_WANTED)
        assert shop.lifts()[0] == pytest.approx(shop.TRADE_ABOVE + shop.LINE / 4, abs=1e-4)  # within the line
    finally:
        shop.LIFT = shop.TRADE_ABOVE


def test_nothing_is_bought_in_a_window_whose_stock_holds_no_key_and_no_scroll():
    play = fortress()
    play.stock = (Stocked(500, 3, 0, 0),)  # not her Misc tab: a gamble's stock, say

    with pytest.raises(Abort, match='did not open at any line tried'):
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


def test_the_tome_of_identify_alone_is_no_visit():
    # Cain identifies (macros/cain.py); the tome is filled on a visit made anyway (the player: "keep bare refills at
    # minimum")
    assert not short(Pack(keys=12, portals=20, identifies=0))


def test_a_kind_full_already_gets_no_tab_click():
    # 14:38:57-58 on 2026-10-17: each full kind took a tab click and its wait, 0.7 s, on every visit
    play = fortress(keys=24, portals=20)
    assert play.pack is not None
    play.pack = replace(play.pack, key_room=False)

    restock(play.run())

    from inventory_tracking.macros.shop import panel_point, tab_point
    from tests.inventory_tracking.macros.fakes import WINDOW

    misc = panel_point(WINDOW, *tab_point(STOCK[0].tab))
    tabs = [e for e in play.keys.events if e[0] == 'click' and math.dist(e[1], misc) < 0.02]
    buys = [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]
    assert not buys
    assert not tabs


def selling(gold: int, level: int = 90) -> tuple[Game, Carried]:
    from inventory_tracking.macros.world import Loot

    play = fortress(keys=12, portals=20)
    assert play.pack is not None
    junk = Carried(9, 418, 4, 2, (2, 2), 4, identified=True)  # a magic Circlet appraised vendor
    play.pack = replace(play.pack, items=(*play.pack.items, junk), key_room=False)
    play.loot = Loot(stats=((12, level), (14, gold)))
    return play, junk


def test_junk_is_sold_while_the_gold_carried_stays_under_the_cap():
    play, junk = selling(gold=500_000)

    restock(play.run(), sell=(junk,))

    assert play.pack is not None
    assert junk not in play.pack.items
    assert dict(play.loot.stats)[14] == 510_000


def test_no_sale_may_take_the_gold_carried_over_the_cap():
    # The player, 2026-10-17: "selling things over this gold limit - just drops extra gold on the ground"; the cap is
    # the level x 10,000 (900,000 at level 90), and a sale brings 35,000 at most
    play, junk = selling(gold=870_000)

    restock(play.run(), sell=(junk,))

    assert play.pack is not None
    assert junk in play.pack.items
    assert dict(play.loot.stats)[14] == 870_000


def test_with_the_level_unread_nothing_is_sold():
    play, junk = selling(gold=10_000, level=0)

    restock(play.run(), sell=(junk,))

    assert play.pack is not None
    assert junk in play.pack.items


def test_a_second_key_stack_is_bought_with_the_first_full():
    # The player, 2026-10-17: "probably we need to carry 2 sets of keys, instead of 12 => 24"
    play = fortress(keys=12, portals=20)
    assert play.pack is not None
    play.pack = replace(play.pack, key_room=False)  # the first stack full: the next takes a cell of its own

    restock(play.run())

    assert play.pack.keys == 24


def test_a_click_that_buys_nothing_between_ones_that_do_does_not_end_the_keys_top_up():
    # 01:47:20 and 01:57:00 on 2026-10-18: 2 -> 12, nothing, 15, nothing: the top-up ended at 15 of 24
    play = fortress(keys=2, portals=20)
    assert play.pack is not None
    play.buys_take = [True, False, True, False, True, False, True, True]

    restock(play.run())

    assert play.pack.keys == 24
