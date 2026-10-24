"""Town Portal scrolls and keys from Jamella (macros/shop.py; routes/lower-kurast-loop-plan.md phase 8)."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.game.records import VALUABLE, Carried, Drop, Monster, Pack, Stocked, Thing
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.portal import FROM_SLING
from inventory_tracking.macros.shop import JAMELLA, KEY, SCROLL, restock, short
from inventory_tracking.macros.skills import SLING_TOWN_PORTAL
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
    from inventory_tracking.macros.loop import TO_THE_CHESTS, TOWN, Loop, next_leg
    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress

    here = world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]))
    progress, loop = Progress(ROUTES, PERFORMED), Loop(on=True)
    assert next_leg(here, progress, loop) == TO_THE_CHESTS
    loop.short = True
    assert next_leg(here, progress, loop) == TOWN  # the town visit, her stop in it (macros/visit.py)


def test_a_vendors_grids_give_each_item_its_tab_and_first_cell():
    from inventory_tracking.game.decode import stock_of

    misc = [0] * 100
    misc[5 * 10 + 9] = 0xA  # the key
    misc[3 * 10 + 9] = misc[4 * 10 + 9] = 0xB  # a two-cell item down the last column
    grids = {5: {'width': 10, 'height': 10, 'cells': misc}, 2: {'width': 10, 'height': 10, 'cells': [0] * 100}}
    units = {0xA: {'txt_id': KEY}, 0xB: {'txt_id': SCROLL}}

    assert stock_of(grids, units) == (Stocked(SCROLL, 3, 9, 3), Stocked(KEY, 3, 9, 5))


def test_the_tome_of_identify_under_its_reserve_is_a_visit_with_the_field_identify_on(monkeypatch):
    # M4 (the player, 2026-10-20: "identify with scroll, and drop if it is bad"; loot/design.md §5): the field identify
    # spends the tome, so under IDENTIFY_RESERVE (5) charges it is short. With the switch off, as before: Cain
    # identifies (macros/cain.py) and the tome is filled on a visit made anyway ("keep bare refills at minimum",
    # 2026-10-17)
    from inventory_tracking.loot import api

    assert short(Pack(keys=12, portals=20, identifies=0))
    assert short(Pack(keys=12, portals=20, identifies=4))
    assert not short(Pack(keys=12, portals=20, identifies=5))
    assert not short(Pack(keys=12, portals=20, identifies=None))  # unread, or no tome
    monkeypatch.setattr(api, 'FIELD_IDENTIFY', False)
    assert not short(Pack(keys=12, portals=20, identifies=0))


def test_an_empty_tome_of_identify_is_filled_and_the_buy_checked_by_its_count(caplog):
    # 15:12-20:05 on 2026-10-20: the empty Tome read None (no quantity stat), "identifies: None carried, no room for
    # more" at every visit, and the field identified nothing; it reads 0 now (game/decode.py `carried_items`)
    from inventory_tracking.game.layout import IDENTIFY_TOME
    from inventory_tracking.macros.shop import IDENTIFY_SCROLL

    play = fortress(keys=24, portals=20)
    assert play.pack is not None
    tome = Carried(2, IDENTIFY_TOME, 8, 0, (1, 2), identified=True)
    play.pack = replace(play.pack, items=(*play.pack.items, tome), key_room=False, identifies=0)
    play.stock = (*STOCK, Stocked(IDENTIFY_SCROLL, 3, 8, 4))
    caplog.set_level('INFO')

    restock(play.run())

    assert play.pack.identifies == 20
    assert 'identifies 0 -> 20' in caplog.text
    scroll = play.stock_cell
    buys = [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]
    assert [scroll(*e[2]) for e in buys] == [(8, 4)]  # one Shift + right click on her Identify scrolls


def test_an_unread_tome_of_identify_gets_no_buy():
    from inventory_tracking.macros.shop import IDENTIFY_SCROLL

    play = fortress(keys=24, portals=20)
    assert play.pack is not None
    play.pack = replace(play.pack, key_room=False, identifies=None)  # unread, or no tome: a scroll would take a cell
    play.stock = (*STOCK, Stocked(IDENTIFY_SCROLL, 3, 8, 4))

    restock(play.run())

    assert play.pack.identifies is None
    assert not [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' in e[3]]


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
    from inventory_tracking.game.records import Loot

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


def test_no_rune_is_sold_whoever_asks():
    # The player, 17:50 on 2026-10-18: the full rune stacks are "cubed, aim to 80 or lower", no longer sold (a full
    # stack's Tal Runes were sold here since 2026-10-17); the junk beside it is sold as before
    from inventory_tracking.loot.runes import RUNES

    play, junk = selling(gold=500_000)
    assert play.pack is not None
    [tal] = [int(cid) for cid, row in RUNES.items() if row['name'] == 'Tal Rune']
    rune = Carried(10, tal, 6, 0, (1, 1), 2)
    play.pack = replace(play.pack, items=(*play.pack.items, rune))

    restock(play.run(), sell=(rune, junk))

    assert rune in play.pack.items
    assert junk not in play.pack.items


def test_an_item_kept_by_its_stats_is_never_sold():
    # 03:48 on 2026-10-19: two rare amulets with +41 and +59 life appraised vendor and sold (macros/keepers.py)
    play, junk = selling(gold=500_000)
    run = play.run()
    run.kept_item = lambda item: '+59 life' if item.unit_id == junk.unit_id else None

    restock(run, sell=(junk,))

    assert play.pack is not None
    assert junk in play.pack.items
    assert dict(play.loot.stats)[14] == 500_000


def test_an_item_the_players_by_its_stats_is_never_sold():
    # The player's charm moved into the cube by hand and sold at 23:17 on 2026-10-18 (rca/2026-10-18): the stats guard
    # (macros/volatile.py prints) holds the sale whatever the list handed to her says
    play, junk = selling(gold=500_000)
    run = play.run()
    run.players_item = lambda item: item.unit_id == junk.unit_id

    restock(run, sell=(junk,))

    assert play.pack is not None
    assert junk in play.pack.items
    assert dict(play.loot.stats)[14] == 500_000


# Healing potions bought into the belt (shop.py BUY_POTIONS; the player, 2026-10-21 ~13:38: "can we also add into town
# routine ability to buy hp potions"). Columns 1-2 rejuvenation, 3-4 healing (config BELT); cell = row x 4 + column


SUPER, GREATER, FULL_REJUVENATION = 606, 605, 531  # d2data misc.json classid of hp5, hp4, rvl


def belt(healing: int) -> tuple[int | None, ...]:
    """Both rejuvenation columns full, `healing` Super Healing Potions in the healing columns (column 3 first)."""
    cells: list[int | None] = [None] * 16
    for row in range(4):
        cells[4 * row], cells[4 * row + 1] = FULL_REJUVENATION, FULL_REJUVENATION
    for n in range(healing):
        cells[4 * (n % 4) + 2 + n // 4] = SUPER
    return tuple(cells)


POTION_STOCK = (Stocked(GREATER, 3, 0, 0), Stocked(SUPER, 3, 1, 0))  # Hell's Jamella: hp4 upgraded to hp5 (HellUpgrade)


def potion_shop(healing: int = 5, gold: int = 500_000, stock: tuple[Stocked, ...] = POTION_STOCK):
    from inventory_tracking.game.records import Loot

    play = fortress(keys=24, portals=20)
    assert play.pack is not None
    play.pack = replace(play.pack, key_room=False)  # nothing else to buy
    play.stock = (*STOCK, *stock)
    play.loot = Loot(belt=belt(healing), life=2907, max_life=2907, stats=((12, 95), (14, gold)), game=('g', 7))
    return play


def potion_buys(play) -> list:
    return [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' not in e[3]]


def test_a_short_belt_is_topped_up_with_the_best_healing_potion_she_sells(caplog):
    play = potion_shop(healing=5)

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.loot.belt == belt(8)  # three Super Healing Potions into the healing columns
    assert play.potions_bought == 3
    assert all(play.stock_cell(*e[2]) == (1, 0) for e in potion_buys(play))  # the Super's cell, not the Greater's
    assert dict(play.loot.stats)[14] == 500_000 - 3 * 450
    assert 'Macro: shop: potions: belt short 3 -> 0, bought 3 Super Healing Potion for 1350 gold' in caplog.text


def test_a_full_belt_buys_no_potion():
    play = potion_shop(healing=8)

    restock(play.run())

    assert not potion_buys(play)
    assert play.potions_bought == 0


def test_gold_under_the_reserve_buys_no_potion(caplog):
    # A vendor takes what the carried gold does not cover from the stash's (repair.py GOLDBANK): never come near it
    play = potion_shop(healing=2, gold=101_000)

    with caplog.at_level('INFO'):
        restock(play.run())

    assert not potion_buys(play)
    assert 'Macro: shop: potions: belt short 6, none bought: carried gold 101000, 100000 kept' in caplog.text


def test_unread_gold_or_an_unread_belt_buys_no_potion():
    play = potion_shop(healing=2)
    play.loot = replace(play.loot, stats=((12, 95),))
    restock(play.run())
    assert not potion_buys(play)

    play = potion_shop(healing=2)
    play.loot = replace(play.loot, belt_read=False)
    restock(play.run())
    assert not potion_buys(play)


def test_a_vendor_without_healing_potions_sells_none(caplog):
    play = potion_shop(healing=2, stock=())

    with caplog.at_level('INFO'):
        restock(play.run())

    assert not potion_buys(play)
    assert 'Macro: shop: potions: belt short 6, none bought: no healing potion in her stock' in caplog.text


def test_the_switch_off_buys_no_potion_as_before(monkeypatch):
    monkeypatch.setattr('inventory_tracking.macros.shop.BUY_POTIONS', False)
    play = potion_shop(healing=2)

    restock(play.run())

    assert not potion_buys(play)
    assert play.loot.belt == belt(2)


def test_a_potion_that_lands_in_the_inventory_ends_the_buying(caplog):
    # A belt with fewer rows than read, or the game's own choice: one potion at most past what the belt takes
    play = potion_shop(healing=2)
    play.potion_lands = lambda cells, txt: None  # never into the belt

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.potions_bought == 1
    assert play.pack is not None
    assert [i.txt for i in play.pack.items].count(SUPER) == 1
    assert 'bought 1 Super Healing Potion for 450 gold: one landed in the inventory' in caplog.text


def test_a_potion_that_lands_in_a_rejuvenation_column_ends_the_buying(caplog):
    play = potion_shop(healing=2)
    cells = list(belt(2))
    cells[0::4] = [None] * 4  # column 1 empty: the game may put a healing potion there
    play.loot = replace(play.loot, belt=tuple(cells))
    play.potion_lands = lambda cells, txt: 0

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.potions_bought == 1
    assert 'bought 1 Super Healing Potion for 450 gold: one landed in belt column 1, not a healing' in caplog.text


# The refill that left the belt short (rca/2026-10-22/belt-refill-findings.md): 23:01:10 "belt short 5 -> 1, bought 4"
# and 23:02:57 "belt short 6 -> 2, bought 4" in the shard game cyberg65; every click after one that bought bought
# nothing, and the clicks were capped at the shortage + 2 (shop.py POTIONS_FILL)
EVERY_OTHER = [True, False] * 10


@pytest.mark.parametrize(('healing', 'short'), [(3, 5), (2, 6), (0, 8)])
def test_a_click_that_buys_nothing_after_each_potion_still_fills_the_belt(caplog, healing, short):
    play = potion_shop(healing=healing)
    play.potion_takes = list(EVERY_OTHER)

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.loot.belt == belt(8)
    assert play.potions_bought == short
    assert dict(play.loot.stats)[14] == 500_000 - short * 450
    assert f'Macro: shop: potions: belt short {short} -> 0, bought {short} Super Healing Potion' in caplog.text


@pytest.mark.parametrize(('healing', 'line'), [(3, 'belt short 5 -> 1, bought 4'), (2, 'belt short 6 -> 2, bought 4')])
def test_the_switch_off_buys_four_of_a_belt_short_five_or_six_as_on_2026_10_22(monkeypatch, caplog, healing, line):
    monkeypatch.setattr('inventory_tracking.macros.shop.POTIONS_FILL', False)
    play = potion_shop(healing=healing)
    play.potion_takes = list(EVERY_OTHER)

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.potions_bought == 4
    assert f'Macro: shop: potions: {line} Super Healing Potion' in caplog.text


def test_the_next_click_waits_for_the_potions_cost_to_land_and_buys(monkeypatch):
    # The game's purchase under way until its cost leaves the carried gold: a click before that buys nothing. With
    # the wait no click is wasted; without it each second click is (the 2026-10-22 pattern)
    play = potion_shop(healing=2)
    play.potion_cost_lag = 0.3

    restock(play.run())

    assert play.loot.belt == belt(8)
    assert len(potion_buys(play)) == 6  # one click a potion

    monkeypatch.setattr('inventory_tracking.macros.shop.POTIONS_FILL', False)
    play = potion_shop(healing=2)
    play.potion_cost_lag = 0.3

    restock(play.run())

    assert play.potions_bought == 4  # the old top-up reproduces the log's 6 -> 2


def test_the_fill_keeps_the_carried_gold_reserve(caplog):
    # Carried gold only, POTIONS_RESERVE kept: never the stash's (repair.py GOLDBANK)
    play = potion_shop(healing=2, gold=103_000)
    play.potion_takes = list(EVERY_OTHER)

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.potions_bought == 3
    assert dict(play.loot.stats)[14] == 103_000 - 3 * 450
    assert ': carried gold 101650, 100000 kept' in caplog.text


def test_two_clicks_in_a_row_that_buy_nothing_still_end_the_fill(caplog):
    play = potion_shop(healing=2)
    play.potion_takes = [True, False, False, True]

    with caplog.at_level('INFO'):
        restock(play.run())

    assert play.potions_bought == 1
    assert 'bought 1 Super Healing Potion for 450 gold: 2 clicks bought nothing (3 clicks, 2 bought nothing)' in (
        caplog.text
    )


def test_the_clicks_a_top_up_makes_at_most():
    from inventory_tracking.macros.shop import potion_clicks

    assert [potion_clicks(short) for short in (1, 5, 6, 8)] == [4, 12, 14, 18]


# A town walk's click with a way out of town under it (shop.py WALK_OFF_WAYS; rca/2026-10-23/visit-portal-findings.md)


def test_a_walk_click_with_a_way_out_under_every_turn_is_refused_unclicked():
    from inventory_tracking.levels.model import TOWN_PORTAL
    from inventory_tracking.macros.shop import walk_until

    play = fortress()
    portal = Thing(2264798530, TOWN_PORTAL, 2, START[0] + 1.0, START[1])  # at the character's feet
    play.thing = portal
    run = play.run()
    run.hovered = lambda: (2, portal.unit_id)  # named under the pointer wherever it is

    with pytest.raises(Abort, match=r'the Town Portal \(2264798530\) under every walk click tried'):
        walk_until(run, lambda world: (START[0] - 6.0, START[1]), (0.0, 0.0, 0.0, 0.0), 'a place 6 away')

    assert not [e for e in play.keys.events if e[0] == 'click']
    assert play.character.area == FORTRESS


def test_the_walks_own_way_out_is_clicked_as_its_goal():
    # The walk to the portal (portal.py) or to the waypoint: the object at the walk's place is not turned off
    from inventory_tracking.macros.shop import ways_out

    play = fortress()
    run = play.run()
    assert ways_out(run, (WAYPOINT.x, WAYPOINT.y)) == ()
    assert ways_out(run, (WAYPOINT.x + 20.0, WAYPOINT.y)) == (WAYPOINT,)
    assert ways_out(run) == (WAYPOINT,)


# A town walk's click with a ground item's label under it (shop.py WALK_OFF_ITEMS; rca/2026-10-24/stash-amulet-
# findings.md): at 18:54:22.7 on 2026-10-24 the walk to the stash took up the Eagle Necklace the loop had put down there

JUNK = (START[0] - 12.0, START[1])  # where the walk's first straight click toward PLACE goes
PLACE = (START[0] - 20.0, START[1])


def _junk_by_the_walk(play: Game) -> Drop:
    """The loop's junk put down on the walk's line; its label is under the pointer within 2.5 units of its ground (a
    label is wider than the fake's half unit), for the record and the click alike."""
    junk = Drop(2388730699, *JUNK, 'Eagle Necklace', VALUABLE)
    play.loot = replace(play.loot, drops=(junk,))

    def under() -> Drop | None:
        gx, gy = play.ground_under_pointer()
        return junk if junk in play.loot.drops and math.dist((gx, gy), JUNK) < 2.5 else None

    play.drop_under_pointer = under  # type: ignore[method-assign]
    return junk


def _there(world) -> bool:
    return world.player is not None and math.dist((world.player.x, world.player.y), PLACE) < 1.0


def test_a_walk_click_on_a_ground_items_label_takes_it_up_as_before(monkeypatch):
    from inventory_tracking.macros import shop

    monkeypatch.setattr(shop, 'WALK_OFF_ITEMS', False)
    play = fortress()
    _junk_by_the_walk(play)

    shop.walk_until(play.run(), lambda world: PLACE, None, 'the stash', until=_there)

    assert play.picked == ['Eagle Necklace']  # the incident: the walk took the junk up


def test_a_walk_click_with_a_ground_item_under_it_is_turned_aside(monkeypatch, caplog):
    from inventory_tracking.macros import shop

    monkeypatch.setattr(shop, 'WALK_OFF_ITEMS', True)
    caplog.set_level('INFO')
    play = fortress()
    _junk_by_the_walk(play)

    shop.walk_until(play.run(), lambda world: PLACE, None, 'the stash', until=_there)

    assert play.picked == []
    assert _there(play.world)
    assert 'Macro: walk: the stash: the ground item (2388730699) under the click at' in caplog.text
    assert 'turned +30 degrees' in caplog.text


def test_a_ground_item_under_every_turn_is_clicked_where_first_aimed(monkeypatch, caplog):
    from inventory_tracking.macros import shop

    monkeypatch.setattr(shop, 'WALK_OFF_ITEMS', True)
    caplog.set_level('INFO')
    play = fortress()
    run = play.run()
    run.hovered = lambda: (4, 77)  # labels everywhere: the walk is not stopped for them

    shop.walk_until(run, lambda world: PLACE, None, 'the stash', until=_there)

    assert _there(play.world)
    assert 'under every turn: clicked where first aimed' in caplog.text


def test_a_way_out_under_every_turn_still_refuses_the_click_with_items_looked_for(monkeypatch):
    from inventory_tracking.levels.model import TOWN_PORTAL
    from inventory_tracking.macros import shop

    monkeypatch.setattr(shop, 'WALK_OFF_ITEMS', True)
    play = fortress()
    portal = Thing(2264798530, TOWN_PORTAL, 2, START[0] + 1.0, START[1])
    play.thing = portal
    run = play.run()
    run.hovered = lambda: (2, portal.unit_id)

    with pytest.raises(Abort, match=r'the Town Portal \(2264798530\) under every walk click tried'):
        shop.walk_until(run, lambda world: (START[0] - 6.0, START[1]), (0.0, 0.0, 0.0, 0.0), 'a place 6 away')
    assert not [e for e in play.keys.events if e[0] == 'click']
