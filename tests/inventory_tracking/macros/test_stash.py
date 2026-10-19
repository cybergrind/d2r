"""The loop's resources into the stash's resource tabs (macros/stash.py)."""

from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.cube import CUBE_CLASS, overflow, own_of
from inventory_tracking.macros.stash import GEMS_TAB, RESOURCES, STASH_CUBE, Pages, open_stash, resources, unload
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.macros.world import BANK, Carried, Pack, Thing
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103
WINDOW = (1920, 0, 2560, 1418)


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


THE_CUBE = Carried(2, CUBE_CLASS, 1, 0, (2, 2))
GRAND = Carried(1, class_of('Grand Charm'), 0, 0, (1, 3))  # the player's
OWN = own_of((THE_CUBE, GRAND))
RUNE = Carried(11, class_of('Hel Rune'), 4, 2, (1, 1))  # the loop's
GEM = Carried(12, class_of('Flawless Sapphire'), 5, 2, (1, 1))
CHARM = Carried(13, class_of('Small Charm'), 6, 2, (1, 1))  # the loop's, no resource: the cube's
CUBED_RUNE = Carried(21, class_of('Ort Rune'), 0, 0, (1, 1))
CUBED_RING = Carried(22, class_of('Ring'), 1, 0, (1, 1))
AMULET = Carried(14, class_of('Amulet'), 7, 2, (1, 1))  # the loop's


def test_the_resources_are_the_stash_tabs_own_kinds():
    for name in (
        'El Rune',
        'Zod Rune',
        'Chipped Diamond',
        'Perfect Skull',
        'Western Worldstone Shard',
        'Key of Terror',
    ):
        assert class_of(name) in RESOURCES, name
    for name in ('Small Charm', 'Grand Charm', 'Jewel', 'Ring', 'Horadric Cube', 'Key'):
        assert class_of(name) not in RESOURCES, name
    assert len(RESOURCES) == 35 + 23 + 33  # the gems, materials and runes tabs' slots


def test_the_loops_resources_and_every_one_in_the_cube_go_and_nothing_else():
    cube = ('##.', '...', '...', '...')
    pack = Pack((GRAND, THE_CUBE, RUNE, GEM, CHARM), cube, frozenset({21, 22}), (CUBED_RUNE, CUBED_RING))

    assert resources(pack, OWN) == ([RUNE, GEM], [CUBED_RUNE])
    assert not overflow(pack, OWN)  # 10 cells free for 3 items
    assert overflow(Pack((GRAND, THE_CUBE, RUNE, GEM, CHARM), ('###', '###', '###', '##.')), OWN)


def test_the_tab_and_the_cubes_grid_are_where_the_players_screenshot_shows_them():
    # 23:59 on 2026-10-16 (2000 x 1125 of the 2560 x 1440 output, its top 22 pixels the desktop's bar): the Gems tab's
    # label at (413, 214), the cube's first cell in the stash centred about (367, 550)
    def shown(point):
        return point[0] * 2000, (point[1] * 1418 + 22) / 1.28

    from inventory_tracking.macros.cube import cell_point

    assert shown(panel_point(WINDOW, *GEMS_TAB)) == pytest.approx((413, 214), abs=6)
    assert shown(cell_point(WINDOW, STASH_CUBE, (0, 0))) == pytest.approx((367, 550), abs=8)


def fortress(pack: Pack) -> Game:
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.pack = pack
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    return play


def test_the_stash_takes_the_cube_and_every_one_of_the_loops_items_and_none_of_the_players():
    # The player, 2026-10-17: "opened stash + ctrl+ click on item - move it to stash"; "if we open any item where cube
    # contents is visible (eg. gems tab) - we can press ctrl + shift + item click - to move it from cube inventory
    # directly into the stash"; "to effectively farm - we need to unload inventory into our stash"
    cube = ('##.', '...', '...', '...')
    play = fortress(Pack((GRAND, THE_CUBE, RUNE, GEM, CHARM), cube, frozenset({21, 22}), (CUBED_RUNE, CUBED_RING)))

    assert unload(play.run(), OWN, 'i') == 5

    # Everything out of the cube into the inventory first (the player, 2026-10-17: only stacks leave the cube on a
    # Ctrl + Shift + click; the rest goes "to inventory (ctrl+click) and then ... back to stash tab (ctrl-click)"),
    # then the resources onto their tabs, then the rest onto the pages
    sent = [item.unit_id for item in play.stashed]
    assert sorted(sent[:3]) == sorted([RUNE.unit_id, GEM.unit_id, CUBED_RUNE.unit_id])
    assert sorted(sent[3:]) == sorted([CHARM.unit_id, CUBED_RING.unit_id])
    assert play.pack is not None
    assert play.pack.items == (GRAND, THE_CUBE)
    assert play.pack.in_cube == ()
    assert play.world.open_panels == ()
    assert play.said[-1] == 'Stash: 5 items put in'


def test_a_cube_item_no_resource_tab_holds_comes_out_through_the_inventory():
    # 01:28:34 on 2026-10-17: a Large Charm, Small Charms, a Ring and Jewels "did not leave" the cube on a Ctrl + Shift
    # + click from the Gems tab
    play = fortress(Pack((GRAND, THE_CUBE), ('#..', '...', '...', '...'), frozenset({22}), (CUBED_RING,)))

    assert unload(play.run(), OWN, 'i') == 1

    assert [item.unit_id for item in play.stashed] == [22]
    assert play.pack is not None
    assert play.pack.items == (GRAND, THE_CUBE)
    assert play.pack.in_cube == ()


def test_scan_uses_the_page_priority_even_after_a_previous_page_took_an_item():
    play = fortress(Pack((GRAND, THE_CUBE, CHARM), ('...',) * 4))
    play.stash_room = [1] * 6
    play.shared_page = 4  # the Shared tab shows page 5 from an earlier visit
    pages = Pages()
    for unit, wanted in enumerate((3, 4, 5, 2, 1, 0), start=13):
        play.pack = Pack((GRAND, THE_CUBE, replace(CHARM, unit_id=unit)), ('...',) * 4)
        assert unload(play.run(), OWN, pages=pages) == 1
        assert pages.first == wanted
        assert play.stash_room[wanted] == 0


def test_a_full_page_sends_the_rest_to_the_shared_pages_and_with_all_full_they_stay():
    play = fortress(Pack((GRAND, THE_CUBE, RUNE, CHARM, AMULET), ('...',) * 4))
    play.stash_room = [0, 0, 1, 0, 0, 0]  # the personal page and the first shared one full, the second takes one
    play.shared_page = 3  # the Shared tab shows the page last looked at

    assert unload(play.run(), OWN) == 2

    assert play.stashed == [RUNE, CHARM]  # the rune onto its tab, the charm onto the second shared page
    assert play.pack is not None
    assert play.pack.items == (GRAND, THE_CUBE, AMULET)
    assert play.said[-1] == 'Stash: 2 items put in, 1 left'


def test_with_nothing_of_the_loops_the_stash_is_not_gone_to():
    play = fortress(Pack((GRAND, THE_CUBE), ('...',) * 4))

    assert unload(play.run(), OWN) == 0
    assert play.pressed() == []
    assert play.keys.events == []


def test_a_stash_out_of_view_is_walked_to_before_it_is_clicked():
    # 01:07:41 on 2026-10-17: the character by the waypoint at (5046.5, 5021.5), the stash at (5019, 5040), 33 units
    # off and out of view: "the stash is not under the pointer at any aim", nothing put in
    play = fortress(Pack((GRAND, THE_CUBE, RUNE), ('...',) * 4))
    play.world = world(FORTRESS, player=player(FORTRESS, x=5046.5, y=5021.5))
    play.thing = Thing(9, BANK, 0, 5019.0, 5040.0)

    assert unload(play.run(), OWN) == 1

    assert play.stashed == [RUNE]


def test_a_resource_its_tab_refuses_is_marked_full_and_a_full_kind_stays_for_jamella():
    # The player, 2026-10-17: "we have 99 tal runes and cannot add more. probably we better just sell them (and other
    # runes that will have 99)"
    play = fortress(Pack((GRAND, THE_CUBE, RUNE, GEM), ('...',) * 4))
    play.stash_refuses = {RUNE.txt}
    full: set[int] = set()

    assert unload(play.run(), OWN, 'i', full) == 1

    assert full == {RUNE.txt}
    assert play.stashed == [GEM]
    play.stash_refuses = set()
    assert unload(play.run(), OWN, 'i', full) == 0  # the rune stays in the inventory for Jamella
    assert play.pack is not None
    assert RUNE in play.pack.items


def test_the_stash_is_gone_to_only_with_the_loops_items_over_half_the_room_left():
    # The player, 2026-10-17: "proabably we don't need to visit stash every game, maybe only when we have more than 50%
    # occupied": of the room the player's own items leave (they take over half the inventory)
    from inventory_tracking.macros.stash import crowded, occupied

    mine = tuple(Carried(30 + i, class_of('Grand Charm'), i, 0, (1, 3)) for i in range(6))  # the player's, 18 cells
    own = own_of((*mine, THE_CUBE))
    loose = tuple(Carried(50 + i, class_of('Ring'), 6 + i % 4, 3, (1, 1)) for i in range(4))
    assert occupied(Pack((*mine, THE_CUBE, *loose[:2])), own) == 2 / 18  # 40 cells, 22 the player's (the cube 2 x 2)
    assert not crowded(Pack((*mine, THE_CUBE, *loose)), own)
    big = tuple(Carried(70 + i, class_of('Grand Charm'), 6 + i, 0, (1, 3)) for i in range(4))  # 12 of 18
    assert crowded(Pack((*mine, THE_CUBE, *big)), own)


def test_a_refused_potion_is_never_a_full_stack():
    # 03:35:18 on 2026-10-17: a Full Rejuvenation Potion its tab refused was marked full, and one was sold at Jamella;
    # the potions are the belt's supply, never a kind left on the ground or sold
    potion = Carried(15, class_of('Full Rejuvenation Potion'), 8, 2, (1, 1))
    play = fortress(Pack((GRAND, THE_CUBE, potion), ('...',) * 4))
    play.stash_refuses = {potion.txt}
    full: set[int] = set()

    unload(play.run(), OWN, 'i', full)

    assert full == set()


def deposit_game(dialog: bool):
    from inventory_tracking.macros.world import Loot

    play = Game(world(103, open_panels=('inventory', 'stash')))
    play.loot = Loot(stats=((12, 94), (14, 924_000), (15, 9_000_000)))
    play.pack = Pack(())  # the inventory read: the clicks on it reach the game
    play.gold_dialog = dialog
    return play


def test_the_gold_over_the_room_kept_is_deposited_with_the_stash_open(monkeypatch):
    # The player, 2026-10-17: "probably we need to move extra gold to our cube [stash]"; the dialog opens with all the
    # carried gold typed in
    from inventory_tracking.macros.stash import deposit
    from tests.inventory_tracking.macros.fakes import WINDOW

    monkeypatch.setattr('inventory_tracking.macros.stash._picture', lambda what: None)
    play = deposit_game(dialog=True)
    assert deposit(play.run(), WINDOW, 690_000) == 234_000
    assert dict(play.loot.stats)[14] == 690_000
    assert dict(play.loot.stats)[15] == 9_234_000


def test_with_no_dialog_nothing_is_deposited_and_escape_closes_what_opened(monkeypatch):
    # the deposit is checked by the carried gold: with no dialog it does not fall, and Escape closes the chat a
    # Return would have opened
    from inventory_tracking.macros.stash import deposit
    from tests.inventory_tracking.macros.fakes import WINDOW

    monkeypatch.setattr('inventory_tracking.macros.stash._picture', lambda what: None)
    play = deposit_game(dialog=False)
    assert deposit(play.run(), WINDOW, 690_000) == 0
    assert dict(play.loot.stats)[14] == 924_000
    assert play.pressed()[-1] == 'Escape'


def test_the_deposit_shows_the_personal_tab_and_one_refused_ends_the_deposits(monkeypatch):
    # 07:38 on 2026-10-19: the Shared tab shown, its gold at 12500000, refused 181494 twice a visit, ~3 s each
    from inventory_tracking.macros.stash import deposit
    from tests.inventory_tracking.macros.fakes import WINDOW

    monkeypatch.setattr('inventory_tracking.macros.stash._picture', lambda what: None)
    play = deposit_game(dialog=True)
    play.stash_tab = 2  # the Gems tab shown, as the rune transmutes leave it
    assert deposit(play.run(), WINDOW, 690_000) == 234_000
    assert play.stash_tab == 0  # the Personal tab
    refused = deposit_game(dialog=False)
    assert deposit(refused.run(), WINDOW, 690_000) == 0
    again = deposit_game(dialog=True)
    assert deposit(again.run(), WINDOW, 690_000) == 0
    assert not [e for e in again.keys.events if e[0] == 'click']


def test_with_the_stash_shut_the_gold_button_is_never_clicked():
    # the same button drops the gold on the ground with the stash shut
    from inventory_tracking.macros.stash import deposit
    from tests.inventory_tracking.macros.fakes import WINDOW

    play = deposit_game(dialog=True)
    play.world = replace(play.world, open_panels=('inventory',))
    assert deposit(play.run(), WINDOW, 690_000) == 0
    assert not [e for e in play.keys.events if e[0] == 'click']


def test_the_inventorys_resources_go_onto_their_tabs_with_no_tab_clicked():
    # The player, 2026-10-18: "when you move runes/gems/dusts/worldstone shards from inventory to stash - you don't need
    # to open appropriate tab. these items automatically gets to corrrect tab in stash"
    play = fortress(Pack((GRAND, THE_CUBE, RUNE, GEM), ('...',) * 4))
    play.stash_tab = 0  # the Personal tab, as the stash opens

    assert unload(play.run(), OWN) == 2

    assert play.stashed == [RUNE, GEM]
    assert play.stash_tab == 0  # no tab was clicked


def test_once_a_kind_is_refused_the_rest_of_it_is_not_tried_in_that_visit():
    # 06:08:50-55 on 2026-10-18: seven flawless gems of four full stacks, each tried (~1.3 s each)
    def clicks(*gems: Carried) -> int:
        play = fortress(Pack((GRAND, THE_CUBE, *gems), ('...',) * 4))
        play.stash_refuses = {GEM.txt}
        unload(play.run(), OWN, 'i', set())
        return sum(event[0] == 'click' for event in play.keys.events)

    assert clicks(GEM, replace(GEM, unit_id=77, x=GEM.x + 1)) == clicks(GEM)


def test_a_stash_the_walks_click_opened_is_done_with_no_aim():
    """The stash version of 14:42:09 on 2026-10-18 (the waypoint's: rca/2026-10-18/arch-actions.md §2 A): the walk's
    last click lands on the stash's picture, which opens 0.12 s after the character stops; the aims then read nothing
    under the pointer (the panel is drawn over it), and the stash was said not under the pointer at any aim."""
    play = fortress(Pack((GRAND, THE_CUBE, RUNE), ('...',) * 4))
    play.world = world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5050.0))  # drawn above the window's fifth
    play.walk_reach, play.opens_after, play.panel_covers = 3.0, 0.12, True

    open_stash(play.run())

    clicks = [e for e in play.keys.events if e[0] == 'click']
    assert len(clicks) == 1  # the walk's, and no aim's
    assert play.stash_opened == 1
    assert set(play.world.open_panels) == {'inventory', 'stash'}
