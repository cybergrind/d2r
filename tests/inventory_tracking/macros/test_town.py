"""The town visit's plan, its stash stop (macros/town.py; macros/town-plan.md step 1)."""

from collections.abc import Sequence
from dataclasses import replace

from inventory_tracking.items.grid import Grid
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.cube import CUBE_CLASS, KEY_CLASS, keys_move, own_of
from inventory_tracking.macros.game.decode import item_size
from inventory_tracking.macros.game.records import Carried, Pack, Page, StashView
from inventory_tracking.macros.town import (
    DEPOSIT_ROOM,
    RUNE_TRANSMUTES,
    RUNES_AIM,
    Holdings,
    Needs,
    Put,
    RuneCube,
    after,
    contract,
    deposit_to,
    named,
    out_now,
    place,
    rune_transmutes,
    stash_stop,
    surplus,
    uncubed,
)


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def thing(unit: int, name: str, x: int, y: int) -> Carried:
    txt = class_of(name)
    return Carried(unit, txt, x, y, item_size(txt))


FULL_PAGE: tuple[str, ...] = ('#' * 10,) * 10
OPEN_PAGE: tuple[str, ...] = ('.' * 10,) * 10


def pages(*rows: tuple[str, ...]) -> tuple[Page, ...]:
    return tuple(Page(index, page) for index, page in enumerate(rows))


def view(room_on: dict[int, tuple[str, ...]] | None = None, **stacks: int) -> StashView:
    """Every page full but those of `room_on`; the stacks by item name ('Tal_Rune' for 'Tal Rune')."""
    rows: list[tuple[str, ...]] = [FULL_PAGE] * 6
    for index, page in (room_on or {}).items():
        rows[index] = page
    counts = tuple(sorted((class_of(name.replace('_', ' ')), count) for name, count in stacks.items()))
    return StashView(pages(*rows), counts)


THE_CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
OWN_CHARMS = tuple(thing(2 + i, 'Grand Charm', 2 + i, 0) for i in range(4))  # the player's, columns 2-5
OWN = own_of((THE_CUBE, *OWN_CHARMS))


def test_place_puts_the_largest_first_onto_the_first_page_with_a_block_for_it():
    small = ('#' * 10,) * 9 + ('.' * 10,)  # one row free: no 1 x 3 fits
    tall = ('#' * 10,) * 7 + ('#########.',) * 3  # one column of three cells
    charm, ring = thing(10, 'Grand Charm', 6, 0), thing(11, 'Ring', 7, 0)

    assert place(pages(FULL_PAGE, small, tall), [ring, charm]) == {charm.unit_id: 2, ring.unit_id: 1}
    assert place(pages(FULL_PAGE, FULL_PAGE), [ring]) == {}  # no room anywhere: it stays


def test_stash_keepers_fill_shared_pages_3_4_5_2_1_before_personal():
    ring = thing(10, 'Ring', 6, 0)
    pack = Pack((THE_CUBE, *OWN_CHARMS, ring))
    priority = (3, 4, 5, 2, 1, 0)
    for offset, wanted in enumerate(priority):
        available = dict.fromkeys(priority[offset:], OPEN_PAGE)
        assert place(view(available).pages, [ring]) == {ring.unit_id: wanted}
        stop = stash_stop(Holdings(pack, OWN), view(available))
        assert stop.puts == (Put(ring, 'inventory', wanted),)


def test_the_keepers_go_to_the_one_page_with_room_and_no_other_is_clicked():
    # 12:42 on 2026-10-18: every page full but shared page 5; the scan opened pages 0 to 5, 13 s, for its items
    ring, charm = thing(10, 'Ring', 6, 0), thing(11, 'Grand Charm', 7, 0)
    pack = Pack((THE_CUBE, *OWN_CHARMS, ring, charm))

    stop = stash_stop(Holdings(pack, OWN), view({5: OPEN_PAGE}))

    assert {(put.item.unit_id, put.source, put.to) for put in stop.puts} == {(10, 'inventory', 5), (11, 'inventory', 5)}
    assert stop.pages() == (5,)
    assert stop.drops == ()
    assert stop.out_for_sale == ()


def test_no_put_goes_to_a_full_stack_and_each_stacks_room_is_counted():
    tals = [thing(20 + i, 'Tal Rune', 6 + i, 3) for i in range(2)]
    gem = thing(22, 'Flawless Sapphire', 8, 3)
    essence = thing(23, 'Twisted Essence of Suffering', 9, 3)
    potion = thing(24, 'Full Rejuvenation Potion', 9, 2)
    pack = Pack((THE_CUBE, *OWN_CHARMS, *tals, gem, essence, potion))

    stop = stash_stop(
        Holdings(pack, OWN),
        view(Tal_Rune=98, Flawless_Sapphire=99, Twisted_Essence_of_Suffering=99, Full_Rejuvenation_Potion=99),
    )

    # one Tal Rune onto its stack of 98 (the Runes tab), the other stays carried; the full gem stays for the cube;
    # the full material is put down (no vendor buys it); a potion is never full: it stays for the belt
    assert stop.puts == (Put(tals[0], 'inventory', -4),)
    assert stop.drops == (essence,)


def test_the_cubes_resources_go_onto_their_tabs_and_its_full_runes_come_out_of_it():
    hel = Carried(30, class_of('Hel Rune'), 0, 0, (1, 1))
    tal = Carried(31, class_of('Tal Rune'), 1, 0, (1, 1))
    gem = Carried(32, class_of('Flawless Sapphire'), 2, 0, (1, 1))
    pack = Pack((THE_CUBE, *OWN_CHARMS), ('###', '...', '...', '...'), frozenset({30, 31, 32}), (hel, tal, gem))

    stop = stash_stop(Holdings(pack, OWN), view(Tal_Rune=99, Flawless_Sapphire=99))

    assert stop.puts == (Put(hel, 'cube', -4),)
    # Out of the cube, no longer for Jamella (the player, 17:50 on 2026-10-18): onto its stack once the rune transmutes
    # make room; the gem stays in the cube for its transmute, so no rune transmute this stop (the cube not empty)
    assert stop.out_for_sale == (tal,)
    assert stop.runes == ()


def test_a_cube_keeper_goes_through_the_room_the_inventory_keepers_leave_onto_the_page_with_room():
    # 12:48 on 2026-10-18: a Linked Mail in the cube found no room in the inventory before the stash; the inventory's
    # keepers went, the stash closed, and a second STASH leg after Jamella tried pages 0 to 5 for it (15.4 s)
    keepers = (thing(10, 'Grand Charm', 6, 0), thing(11, 'Grand Charm', 7, 0))
    junk = tuple(thing(100 + i, 'Ring', x, y) for i, (x, y) in enumerate(
        [(8, 0), (9, 0), (8, 1), (9, 1), (8, 2), (9, 2), (0, 2), (1, 2)] + [(x, 3) for x in range(10)]
    ))  # fmt: skip
    mail = Carried(50, class_of('Linked Mail'), 0, 0, (2, 3))
    pack = Pack((THE_CUBE, *OWN_CHARMS, *keepers, *junk), ('##.', '##.', '##.', '...'), frozenset({50}), (mail,))
    assert not pack.inventory.has_room(mail.size)
    room = ('#' * 10,) * 6 + ('.' * 10,) * 4

    stop = stash_stop(Holdings(pack, OWN, junk=frozenset(i.unit_id for i in junk)), view({5: room}))

    assert [(put.item.unit_id, put.source, put.to) for put in stop.puts] == [
        (10, 'inventory', 5),
        (11, 'inventory', 5),
        (50, 'cube', 5),
    ]
    assert out_now(pack.inventory, [mail]) == ()  # not before the stash: through the room the keepers leave
    left = after(pack, stop)
    assert left.in_cube == ()
    assert all(i.unit_id not in (10, 11, 50) for i in left.items)


def test_the_cubes_junk_comes_out_as_the_room_left_after_the_keepers_allows_and_the_block_is_free_once_sold():
    keeper = thing(10, 'Grand Charm', 6, 0)
    fill = tuple(thing(40 + i, 'Ring', x, 3) for i, x in enumerate(range(10)))  # the loop's junk, the bottom row
    cubed_junk = (
        Carried(60, class_of('Grand Charm'), 0, 0, (1, 3)),
        Carried(61, class_of('Grand Charm'), 1, 0, (1, 3)),
        Carried(62, class_of('Grand Charm'), 2, 0, (1, 3)),
        Carried(63, class_of('Ring'), 0, 3, (1, 1)),
    )
    others = (thing(70, 'Grand Charm', 7, 0), thing(71, 'Grand Charm', 8, 0))  # the loop's unidentified
    cube = ('###', '###', '###', '#..')
    pack = Pack((THE_CUBE, *OWN_CHARMS, keeper, *others, *fill), cube, frozenset(range(60, 64)), cubed_junk)
    junk = frozenset({*(i.unit_id for i in fill), *(i.unit_id for i in cubed_junk)})

    stop = stash_stop(Holdings(pack, OWN, junk=junk, unknown=frozenset({70, 71})), view({1: OPEN_PAGE}))

    assert stop.puts == (Put(keeper, 'inventory', 1),)
    # Room after the keeper: column 6 rows 0-2, column 9 rows 0-2, (0, 2) and (1, 2): two Grand Charms and the ring
    assert {i.unit_id for i in stop.out_for_sale} == {60, 61, 63}
    sold = after(pack, stop)
    sold = Pack(tuple(i for i in sold.items if i.unit_id not in junk))
    assert sold.inventory.has_room(Needs().block) is False  # the unidentified still hold columns 7 and 8
    sold = Pack(tuple(i for i in sold.items if i.unit_id not in (70, 71)))
    assert sold.inventory.has_room(Needs().block)


def test_the_players_own_items_are_never_put():
    pack = Pack((THE_CUBE, *OWN_CHARMS))

    stop = stash_stop(Holdings(pack, OWN), view({0: OPEN_PAGE}))

    assert stop.puts == ()
    assert stop.idle


def test_a_key_stack_in_the_block_is_moved_out_of_it():
    keys = Carried(80, KEY_CLASS, 8, 1, (1, 1))
    pack = Pack((THE_CUBE, *OWN_CHARMS, keys))

    move = keys_move(pack, (2, 4))

    assert move is not None
    moved, cell = move
    assert moved == keys
    rows = Pack((THE_CUBE, *OWN_CHARMS, Carried(80, KEY_CLASS, *cell, (1, 1)))).inventory
    assert Grid(rows).has_room((2, 4))


def test_a_kind_whose_perfect_stack_is_full_has_its_surplus_sold():
    flawless = class_of('Flawless Sapphire')
    full = view(Flawless_Sapphire=99, Perfect_Sapphire=99)
    half = view(Flawless_Sapphire=99, Perfect_Sapphire=40)
    gems = [Carried(90 + i, flawless, i, 3, (1, 1)) for i in range(5)]
    assert surplus(gems, full) == tuple(gems[3:])  # one transmute's worth kept
    assert surplus(gems, half) == ()  # cubed into perfect ones first


def test_the_deposit_leaves_the_sales_room_and_the_repair_carried():
    cap = 990_000
    assert deposit_to(500_000, cap) is None  # far from the cap: no deposit
    assert deposit_to(950_000, cap) == cap - DEPOSIT_ROOM
    assert deposit_to(950_000, cap, repair=800_000) == 960_000  # never below 1.2 x the expected repair


# A cube keeper whose block the inventory's junk holds (rca/2026-10-18/town-remaining-findings.md §1)


def free_page(index: int, free: int) -> Page:
    """A page with `free` cells free, the first rows first."""
    rows = [('.' * min(10, max(0, free - 10 * row))).ljust(10, '#') for row in range(10)]
    return Page(index, tuple(rows))


def pack_1428() -> tuple[Pack, frozenset[tuple[int, int, int]], frozenset[int]]:
    """The 14:28:12 stash stop on 2026-10-18 (probe.log 20261018T112640Z-e7593b62, the session's repro1428.py): the
    pack, the player's own items and the junk (the set Amulet at (4, 2), the magic Small Charm at (4, 3)). The cube
    holds a unique Embossed Plate (2 x 3) whose one block in the inventory, columns 3-4 rows 0-2, the Amulet is in."""
    own_items = [
        thing(201, 'Grand Charm', 0, 0),
        thing(202, 'Horadric Cube', 1, 0),
        thing(203, 'Small Charm', 5, 0),
        thing(204, 'Small Charm', 6, 0),
        thing(205, 'Key', 7, 0),
        thing(206, 'Tome of Town Portal', 8, 0),
        thing(207, 'Small Charm', 9, 0),
        thing(208, 'Grand Charm', 5, 1),
        *(thing(209 + n, 'Small Charm', x, 1) for n, x in enumerate((6, 7, 9))),
        thing(212, 'Large Charm', 1, 2),
        thing(213, 'Large Charm', 6, 2),
        thing(214, 'Small Charm', 7, 2),
        thing(215, 'Large Charm', 8, 2),
        thing(216, 'Small Charm', 9, 2),
        *(thing(217 + n, 'Small Charm', x, 3) for n, x in enumerate((0, 7, 9))),
    ]
    loop = [
        thing(13, 'Key', 2, 2),
        thing(21, 'Flawless Skull', 2, 3),
        replace(thing(22, 'Small Charm', 4, 3), quality=4),  # vendor
        thing(23, 'Flawed Topaz', 3, 0),
        replace(thing(24, 'Amulet', 4, 2), quality=5),  # vendor
    ]
    cubed = (
        replace(thing(31, 'Embossed Plate', 0, 0), quality=7),  # slow: a keeper
        thing(32, 'Flawless Amethyst', 2, 0),
        replace(thing(33, 'Amulet', 2, 1), quality=7),  # slow: a keeper
        thing(34, 'Ort Rune', 2, 2),
    )
    pack = Pack(tuple(own_items + loop), ('###', '###', '###', '...'), frozenset(i.unit_id for i in cubed), cubed)
    return pack, own_of(own_items), frozenset({22, 24})


def view_1428() -> StashView:
    free = {0: 4, 1: 2, 2: 13, 3: 2, 4: 16, 5: 54}  # the pages' free cells as the stop's view read them
    stacks = ('Flawless_Amethyst', 'Flawed_Topaz', 'Flawless_Skull', 'Ort_Rune')
    return StashView(
        tuple(free_page(i, n) for i, n in free.items()),
        tuple(sorted((class_of(name.replace('_', ' ')), 10) for name in stacks)),
    )


def test_a_cube_keeper_blocked_by_inventory_junk_gets_a_shuffle_that_frees_its_block():
    # 14:28 on 2026-10-18: the plate had no put, stayed in the cube, "short of the contract: cube 1 items, 1 keepers
    # carried"; the Amulet moved aside frees columns 3-4, rows 0-2 inside the stop's close and reopen
    pack, own, junk = pack_1428()
    assert out_now(pack.inventory, [pack.in_cube[0]]) == ()

    stop = stash_stop(Holdings(pack, own, junk), view_1428())

    assert [(item.unit_id, cell) for item, cell in stop.shuffles] == [(24, (2, 3))]
    assert stop.into_cube == ()
    assert (31, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    left = after(pack, stop)
    assert left.in_cube == ()
    sold = Pack(tuple(i for i in left.items if i.unit_id not in junk))
    assert contract(sold, own, Needs(keys=12), junk=junk).misses == ()


def grid(free: set[tuple[int, int]], loop: Sequence[Carried] = ()) -> tuple[Pack, frozenset[tuple[int, int, int]]]:
    """An inventory with THE_CUBE at (0, 0), the loop's `loop` items, `free` cells free and every other cell the
    player's own Small Charm; the cube holding a unique Embossed Plate (2 x 3) at (0, 0) and room in column 2."""
    held = {(i.x + dx, i.y + dy) for i in (THE_CUBE, *loop) for dx in range(i.size[0]) for dy in range(i.size[1])}
    charms = [
        thing(300 + 10 * y + x, 'Small Charm', x, y) for y in range(4) for x in range(10) if (x, y) not in held | free
    ]
    plate = replace(Carried(50, class_of('Embossed Plate'), 0, 0, (2, 3)), quality=7)
    pack = Pack((THE_CUBE, *charms, *loop), ('##.', '##.', '##.', '...'), frozenset({50}), (plate,))
    return pack, own_of((THE_CUBE, *charms))


BLOCK_BUT_ONE = {(x, y) for x in (3, 4) for y in range(3)} - {(4, 2)}  # columns 3-4, rows 0-2 but (4, 2)


def test_a_shuffle_never_moves_the_players_own_items_and_moves_the_unidentified_within_the_inventory():
    # The player, 2026-10-17: "we shouldn't sell our own equipment"; 16:50 on 2026-10-18: "shuffle can move unid items"
    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)})  # the player's own Small Charm at (4, 2)

    stop = stash_stop(Holdings(pack, own), view({5: OPEN_PAGE}))

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert all(put.item.unit_id != 50 for put in stop.puts)  # it stays in the cube: a miss, never the player's moved

    ring = replace(thing(60, 'Ring', 4, 2), quality=4, identified=False)
    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)}, [ring])

    stop = stash_stop(Holdings(pack, own, unknown=frozenset({60})), view({5: OPEN_PAGE}))

    assert [(item.unit_id, cell) for item, cell in stop.shuffles] == [(60, (9, 3))]  # carried on, for Cain
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert [(i.unit_id, i.x, i.y) for i in after(pack, stop).items if i.unit_id == 60] == [(60, 9, 3)]

    # With no cell for it outside the block the unidentified never goes into the cube (nor onto a page): the plate stays
    pack, own = grid(BLOCK_BUT_ONE, [ring])

    stop = stash_stop(Holdings(pack, own, unknown=frozenset({60})), view({5: OPEN_PAGE}))

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert stop.parks == ()
    assert all(put.item.unit_id != 50 for put in stop.puts)

    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)}, [replace(ring, identified=True)])  # judged junk: it moves

    stop = stash_stop(Holdings(pack, own, frozenset({60})), view({5: OPEN_PAGE}))

    assert [(item.unit_id, cell) for item, cell in stop.shuffles] == [(60, (9, 3))]
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]


def test_no_shuffle_when_the_block_is_free_already():
    ring = replace(thing(60, 'Ring', 4, 3), quality=4)
    pack, own = grid(BLOCK_BUT_ONE | {(4, 2)}, [ring])

    stop = stash_stop(Holdings(pack, own, frozenset({60})), view({5: OPEN_PAGE}))

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]


def test_a_cube_keeper_with_no_page_room_moves_nothing():
    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)}, [ring])

    stop = stash_stop(Holdings(pack, own, frozenset({60})), view())

    assert stop.shuffles == ()
    assert stop.into_cube == ()


def test_with_no_free_cell_outside_the_block_the_junk_goes_into_the_cube_for_jamella():
    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    pack, own = grid(BLOCK_BUT_ONE, [ring])  # no cell free but the block's

    stop = stash_stop(Holdings(pack, own, frozenset({60})), view({5: OPEN_PAGE}))

    assert stop.shuffles == ()
    assert stop.into_cube == (ring,)
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    left = after(pack, stop)
    assert [(i.unit_id, i.x, i.y) for i in left.in_cube] == [(60, 2, 0)]  # beside the plate, before it came out
    assert all(i.unit_id != 60 for i in left.items)


def test_a_shuffle_never_takes_the_2x4_block_at_the_end():
    # The 2 x 4 a session leaves (the player, 2026-10-18; 12:36 Brandistock): the loop's key moved out of the plate's
    # block goes where the block stays free once the junk is sold, not into the first free cell
    key = thing(70, 'Key', 3, 0)
    rings = [replace(thing(71 + n, 'Ring', x, y), quality=4) for n, (x, y) in enumerate(
        [(6, 1), (6, 2), (6, 3), (7, 0), (7, 1), (7, 2), (7, 3)]
    )]  # fmt: skip
    pack, own = grid(BLOCK_BUT_ONE - {(3, 0)} | {(4, 2), (6, 0), (9, 3)}, [key, *rings])
    junk = frozenset(i.unit_id for i in rings)

    stop = stash_stop(Holdings(pack, own, junk), view({5: OPEN_PAGE}), Needs(block=(2, 4)))

    assert [(item.unit_id, cell) for item, cell in stop.shuffles] == [(70, (9, 3))]  # not (6, 0)
    left = after(pack, stop)
    sold = Pack(tuple(i for i in left.items if i.unit_id not in junk))
    assert sold.inventory.has_room((2, 4))


def pack_1455() -> tuple[Pack, frozenset[tuple[int, int, int]], frozenset[int]]:
    """The 14:55:56 visit on 2026-10-18 (probe.log 20261018T114835Z-2dc9cf24, lines 3116-3178; the inventory and cube
    from the collection 20261018T115605Z-dff7a422 after its stop), the same character's inventory as at 14:28. The
    cube held a unique Spiked Club (1 x 3, `slow`) and three junk; the inventory's junk unique Ring (3, 2) and rare
    Jewel (4, 2) held both columns the club could come out into. The resources' classes and cells (the 4 put onto
    their tabs) are inferred from the cells free before and after the stop."""
    pack, own, _junk = pack_1428()
    own_items = [i for i in pack.items if (i.txt, i.x, i.y) in own]
    loop = [
        thing(13, 'Key', 2, 2),
        replace(thing(40, 'Ring', 3, 2), quality=7),  # vendor
        replace(thing(41, 'Jewel', 4, 2), quality=6),  # vendor
        replace(thing(42, 'Small Charm', 2, 3), quality=4),  # vendor
        thing(43, 'Flawed Topaz', 3, 0),
        thing(44, 'Hel Rune', 4, 3),
    ]
    cubed = (
        replace(thing(50, 'Spiked Club', 0, 0), quality=7),  # slow: a keeper
        thing(51, 'Flawless Amethyst', 1, 0),
        thing(52, 'Flawed Topaz', 1, 1),
        replace(thing(53, 'Jewel', 2, 0), quality=4),  # vendor
        replace(thing(54, 'Amulet', 2, 1), quality=5),  # vendor
        thing(55, 'Ort Rune', 0, 3),
        replace(thing(56, 'Ring', 2, 3), quality=5),  # vendor
    )
    pack = Pack(
        tuple(own_items + loop), ('###', '###', '#..', '#.#'), frozenset(i.unit_id for i in cubed), cubed, keys=24
    )
    return pack, own, frozenset({40, 41, 42, 53, 54, 56})


def view_1455() -> StashView:
    free = {0: 0, 1: 2, 2: 9, 3: 2, 4: 12, 5: 40}  # "stash view: pages free 0:0 1:2 2:9 3:2 4:12 5:40"
    stacks = ('Flawless_Amethyst', 'Flawed_Topaz', 'Hel_Rune', 'Ort_Rune')
    return StashView(
        tuple(free_page(i, n) for i, n in free.items()),
        tuple(sorted((class_of(name.replace('_', ' ')), 10) for name in stacks)),
    )


def test_the_1455_spiked_club_gets_a_column_by_a_shuffle_and_the_cubes_junk_still_comes_out():
    # 14:56:16 on 2026-10-18: "short of the contract: cube 1 items (unique Spiked Club at (0, 0)), 1 keepers carried";
    # the cube's three junk came out first, into the cells left, and the club had no column of three
    pack, own, junk = pack_1455()

    stop = stash_stop(Holdings(pack, own, junk), view_1455())

    assert [(item.unit_id, cell) for item, cell in stop.shuffles] == [(40, (4, 0))]
    assert stop.into_cube == ()
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert {i.unit_id for i in stop.out_for_sale} == {53, 54, 56}  # the room the club leaves
    left = after(pack, stop)
    assert left.in_cube == ()
    sold = Pack(tuple(i for i in left.items if i.unit_id not in junk), keys=24)
    assert contract(sold, own, Needs(keys=12), junk=junk).misses == ()


def pack_1505() -> tuple[Pack, frozenset[tuple[int, int, int]], frozenset[int]]:
    """The 15:05:53 visit on 2026-10-18 (probe.log 20261018T120214Z-72a31d3f; the collections 20261018T120058Z-bf8cda44
    and 120600Z-c5e2212a around it), the same character's inventory as at 14:28: the loop's one item there a unique
    Fuscina (2 x 4, junk) in columns 3-4, one cell free (2, 3), the cube full: a set Boots (2 x 2, a keeper) at (1, 0),
    a set Amulet (a keeper), three junk and four resources (their classes inferred: "5 items put in (pages 1)")."""
    pack, own, _junk = pack_1428()
    own_items = [i for i in pack.items if (i.txt, i.x, i.y) in own]
    loop = [thing(13, 'Key', 2, 2), replace(thing(40, 'Fuscina', 3, 0), quality=7)]  # vendor
    cubed = (
        replace(thing(50, 'Small Charm', 0, 0), quality=4),  # vendor
        replace(thing(51, 'Boots', 1, 0), quality=5),  # slow at 15:01: a keeper
        thing(52, 'Flawless Amethyst', 0, 1),
        replace(thing(53, 'Amulet', 0, 2), quality=5),  # check: a keeper
        replace(thing(54, 'Jewel', 1, 2), quality=4),  # vendor
        thing(55, 'Flawed Topaz', 2, 2),
        thing(56, 'Ort Rune', 0, 3),
        replace(thing(57, 'Jewel', 1, 3), quality=6),  # vendor
        thing(58, 'Hel Rune', 2, 3),
    )
    pack = Pack(tuple(own_items + loop), ('###',) * 4, frozenset(i.unit_id for i in cubed), cubed, keys=24)
    return pack, own, frozenset({40, 50, 54, 57})


def view_1505() -> StashView:
    free = {0: 0, 1: 2, 2: 9, 3: 2, 4: 12, 5: 34}  # "stash view: pages free 0:0 1:2 2:9 3:2 4:12 5:34"
    stacks = ('Flawless_Amethyst', 'Flawed_Topaz', 'Hel_Rune', 'Ort_Rune')
    return StashView(
        tuple(free_page(i, n) for i, n in free.items()),
        tuple(sorted((class_of(name.replace('_', ' ')), 10) for name in stacks)),
    )


def test_a_cube_keeper_only_the_junks_sale_lets_out_is_told_stranded():
    # 15:06:15 on 2026-10-18: "short of the contract: cube 1 items (set Boots at (1, 0))": the Fuscina moves nowhere in
    # the inventory and no cube room takes it while the Boots and the cube's junk are in it; only her sale frees it
    pack, own, junk = pack_1505()

    stop = stash_stop(Holdings(pack, own, junk), view_1505(), park=False)

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert [i.unit_id for i in stop.stranded] == [51]
    assert all(put.item.unit_id != 51 for put in stop.puts)
    # Once she has bought the junk, the same stop takes the Boots out first and onto a page
    sold = Pack(
        tuple(i for i in pack.items if i.unit_id not in junk),
        pack.cube,
        pack.cube_items - junk,
        tuple(i for i in pack.in_cube if i.unit_id not in junk),
    )
    stop = stash_stop(Holdings(sold, own), view_1505())

    assert stop.stranded == ()
    assert (51, 'cube', 4) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert after(sold, stop).in_cube == ()


def test_a_cube_keeper_the_shuffle_frees_is_not_stranded():
    pack, own, junk = pack_1428()

    stop = stash_stop(Holdings(pack, own, junk), view_1428())

    assert stop.stranded == ()
    assert stop.parks == ()  # a move aside does it: nothing parked


def test_the_1505_fuscina_is_parked_on_a_shared_page_and_comes_back_once_the_boots_are_in():
    # The player, 16:50 on 2026-10-18: "junk can be temporarily stored in stash, but sold after". The Fuscina (2 x 4)
    # onto page 5 for the stop, the Boots out through its cells onto page 4, the Fuscina back where it was; the cube's
    # junk waits in it for Jamella's passes (the room kept for the Fuscina to come back)
    pack, own, junk = pack_1505()

    stop = stash_stop(Holdings(pack, own, junk), view_1505())

    assert [(put.item.unit_id, put.to) for put in stop.parks] == [(40, 5)]
    assert stop.stranded == ()
    assert stop.full == ()
    assert (51, 'cube', 4) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert stop.out_for_sale == ()
    left = after(pack, stop)
    assert [(i.unit_id, i.x, i.y) for i in left.items if i.unit_id == 40] == [(40, 3, 0)]  # back, for her
    assert {i.unit_id for i in left.in_cube} == {50, 54, 57}  # the cube's junk only
    sold = Pack(tuple(i for i in left.items if i.unit_id not in junk), keys=24)
    assert contract(sold, own, Needs(keys=12), junk=junk).misses == ()


def test_no_park_without_a_shared_page_for_the_junk_nor_onto_the_personal_page():
    # A park whose junk no shared page takes is not made (it would stay in the stash): the keeper stays stranded
    pack, own, junk = pack_1505()
    roomy = StashView((Page(0, OPEN_PAGE), *view_1505().pages[1:]), view_1505().stacks)
    tight = StashView(
        (Page(0, OPEN_PAGE), *(replace(p, rows=('.' * 2 + '#' * 8,) * 2 + ('#' * 10,) * 8) for p in roomy.pages[1:])),
        roomy.stacks,
    )  # a 2 x 2 on each shared page, no 2 x 4

    stop = stash_stop(Holdings(pack, own, junk), tight)

    assert stop.parks == ()
    assert [i.unit_id for i in stop.stranded] == [51]


def test_a_park_never_takes_the_block_a_later_keeper_needs_on_its_page():
    # Page 5's one 2 x 4 and one 2 x 2: the Fuscina parked first (the Boots come out after it) must not take the
    # 2 x 2's cells; no other page has room, so nothing is parked
    pack, own, junk = pack_1505()
    rows = ('..########', '..########', '..##..####', '..##..####') + ('#' * 10,) * 6
    only = StashView(tuple(Page(i, rows if i == 5 else FULL_PAGE) for i in range(6)), view_1505().stacks)
    amulet_room = replace(only.pages[3], rows=('.' + '#' * 9,) + ('#' * 10,) * 9)
    only = StashView((*only.pages[:3], amulet_room, *only.pages[4:]), only.stacks)

    stop = stash_stop(Holdings(pack, own, junk), only)

    assert [(put.item.unit_id, put.to) for put in stop.parks] == [(40, 5)]  # the 2 x 4 at (0, 0), first fit
    assert (51, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]  # the 2 x 2 at (4, 2)


def pack_1514() -> tuple[Pack, frozenset[tuple[int, int, int]], frozenset[int]]:
    """The 15:14:23 visit on 2026-10-18 (probe.log 20261018T120214Z-72a31d3f; the collection 20261018T121436Z-308e3155
    after its stop): a junk set Bramble Mitts (2 x 2) at (3, 0) held the top of the only 2 x 3 a unique Serpentskin
    Armor in the cube needed, and no other 2 x 2 took the Mitts, in the inventory or the cube. The resources' classes
    and the rune's cell are inferred ("4 items put in (pages 1,2)")."""
    pack, own, _junk = pack_1428()
    own_items = [i for i in pack.items if (i.txt, i.x, i.y) in own]
    loop = [
        thing(13, 'Key', 2, 2),
        replace(thing(40, 'Bramble Mitts', 3, 0), quality=5),  # vendor
        replace(thing(41, 'Ring', 2, 3), quality=7),  # check: a keeper
        thing(42, 'Ort Rune', 4, 3),
    ]
    cubed = (
        replace(thing(50, 'Serpentskin Armor', 0, 0), quality=7),  # slow: a keeper
        thing(51, 'Flawless Amethyst', 2, 0),
        replace(thing(52, 'Small Charm', 2, 1), quality=4),  # vendor
        replace(thing(53, 'Ring', 2, 2), quality=7),  # slow: a keeper
    )
    pack = Pack(tuple(own_items + loop), ('###',) * 3 + ('...',), frozenset(i.unit_id for i in cubed), cubed, keys=24)
    return pack, own, frozenset({40, 52})


def view_1514() -> StashView:
    free = {0: 0, 1: 1, 2: 9, 3: 2, 4: 8, 5: 34}  # "stash view: pages free 0:0 1:1 2:9 3:2 4:8 5:34"
    return StashView(
        tuple(free_page(i, n) for i, n in free.items()),
        tuple(sorted((class_of(name), 10) for name in ('Flawless Amethyst', 'Ort Rune'))),
    )


def test_the_1514_serpentskin_armor_is_told_stranded_behind_the_bramble_mitts():
    # 15:14:44 on 2026-10-18: "short of the contract: cube 1 items (unique Serpentskin Armor at (0, 0))"
    pack, own, junk = pack_1514()

    stop = stash_stop(Holdings(pack, own, junk), view_1514(), park=False)

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert [i.unit_id for i in stop.stranded] == [50]

    stop = stash_stop(Holdings(pack, own, junk), view_1514())  # the Mitts parked on page 5 (PARK_JUNK)

    assert [(put.item.unit_id, put.to) for put in stop.parks] == [(40, 5)]
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert stop.stranded == ()
    assert after(pack, stop).in_cube == tuple(i for i in pack.in_cube if i.unit_id in junk)


def pack_1520() -> tuple[Pack, frozenset[tuple[int, int, int]], frozenset[int]]:
    """The 15:20:18 visit on 2026-10-18 (probe.log 20261018T120214Z-72a31d3f, lines 7425-7484): "room low: 6 cells free
    (inventory 6, cube 0, loop items 1 in the inventory and 7 in the cube; cube rows ###/###/###/###)", the same
    character's inventory as at 14:28. The inventory's one loop item a magic Grand Charm (1 x 3, vendor) at (3, 0), in
    the only 2 x 3; the cube the unique Serpentskin Armor of 15:14 at (0, 0), two set Rings and a magic Jewel judged
    vendor at Cain ("appraised ... at (2, 0) / (2, 1) / (1, 3)") and three resources in the cells left, onto their tabs
    ("3 items put in (pages -)": their classes inferred)."""
    pack, own, _junk = pack_1428()
    own_items = [i for i in pack.items if (i.txt, i.x, i.y) in own]
    loop = [thing(13, 'Key', 2, 2), replace(thing(40, 'Grand Charm', 3, 0), quality=4)]  # vendor
    cubed = (
        replace(thing(50, 'Serpentskin Armor', 0, 0), quality=7),  # slow: a keeper
        replace(thing(51, 'Ring', 2, 0), quality=5),  # vendor
        replace(thing(52, 'Jewel', 2, 1), quality=4),  # vendor
        thing(53, 'Flawless Amethyst', 2, 2),
        thing(54, 'Ort Rune', 0, 3),
        replace(thing(55, 'Ring', 1, 3), quality=5),  # vendor
        thing(56, 'Flawed Topaz', 2, 3),
    )
    pack = Pack(tuple(own_items + loop), ('###',) * 4, frozenset(i.unit_id for i in cubed), cubed, keys=18)
    return pack, own, frozenset({40, 51, 52, 55})


def view_1520() -> StashView:
    free = {0: 0, 1: 0, 2: 8, 3: 2, 4: 8, 5: 34}  # "stash view: pages free 0:0 1:0 2:8 3:2 4:8 5:34"
    full = ('Full Rejuvenation Potion', 'Tal Rune', 'Twisted Essence of Suffering')  # "full stacks ..."
    stacks = [(class_of(name), 10) for name in ('Flawless Amethyst', 'Ort Rune', 'Flawed Topaz')]
    return StashView(
        tuple(free_page(i, n) for i, n in free.items()), tuple(sorted(stacks + [(class_of(n), 99) for n in full]))
    )


def test_the_1520_serpentskin_armor_is_told_stranded_behind_the_grand_charm():
    # 15:20:31 on 2026-10-18: "short of the contract: cube 1 items (unique Serpentskin Armor at (0, 0))": a junk Grand
    # Charm (1 x 3) at (3, 0) in the only 2 x 3, no cell for it elsewhere, the cube full
    pack, own, junk = pack_1520()

    stop = stash_stop(Holdings(pack, own, junk), view_1520(), park=False)

    assert stop.shuffles == ()
    assert stop.into_cube == ()
    assert [i.unit_id for i in stop.stranded] == [50]

    stop = stash_stop(Holdings(pack, own, junk), view_1520())  # the Grand Charm parked on page 5 (PARK_JUNK)

    assert [(put.item.unit_id, put.to) for put in stop.parks] == [(40, 5)]
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]
    assert stop.stranded == ()


# The stash full (the player, 16:50 on 2026-10-18: "if stash is full - we need to stop loop")


def test_a_keeper_no_page_has_room_for_is_the_stash_full_and_named():
    # The cube's plate (2 x 3) and the inventory's Ring with every page full: both named, nothing moved for them
    ring = replace(thing(60, 'Ring', 9, 3), quality=7)
    pack, own = grid(BLOCK_BUT_ONE | {(4, 2)}, [ring])

    stop = stash_stop(Holdings(pack, own), view())

    assert {i.unit_id for i in stop.full} == {50, 60}
    assert stop.puts == ()
    assert stop.shuffles == ()
    assert stop.parks == ()
    done = contract(after(pack, stop), own, Needs(), stash_full=named(stop.full))
    assert set(done.stash_full) == {'unique Embossed Plate at (0, 0)', 'unique Ring at (9, 3)'}


def test_a_stranded_keeper_is_not_the_stash_full():
    # 16:35 on 2026-10-18 (fixtures/visits/2026-10-18-163522.json): the Boots have room on page 5; the inventory has
    # none for them to come out through, and no shared page a 2 x 4 for the Fuscina to park: stranded, not full
    from tests.inventory_tracking.macros.test_townplan import fixture

    start = fixture('1635')
    assert start.view is not None

    stop = stash_stop(Holdings(start.pack, start.own, start.junk, start.unknown), start.view)

    assert stop.full == ()
    assert [i.unit_id for i in stop.stranded] == [704388917]
    assert stop.parks == ()


def test_no_park_into_the_room_the_keepers_take():
    # Every page full but a 2 x 4 on page 3: the keepers (the Boots, the Amulet) have room there, the Fuscina parked
    # too would leave them none. Nothing parked, the Boots stranded, and no stash full
    pack, own, junk = pack_1505()
    rows = ('..' + '#' * 8,) * 4 + ('#' * 10,) * 6
    one = StashView(tuple(Page(i, rows if i == 3 else FULL_PAGE) for i in range(6)), view_1505().stacks)

    stop = stash_stop(Holdings(pack, own, junk), one)

    assert stop.parks == ()
    assert [i.unit_id for i in stop.stranded] == [51]
    assert stop.full == ()


# A keeper waiting in the cube (the player, 17:50 on 2026-10-18: "keeper can wait in cube")


def test_a_cube_keeper_with_no_way_out_waits_in_the_cube_named_on_the_contract_not_a_miss():
    # The cube's plate has room on page 5; the inventory has no 2 x 3 for it to come out through and no junk to move or
    # park: it waits for the next visit. The contract names it as deferred; no cube miss, no keeper carried, no stash
    # full; the cube's count still says it is there (its cells the loop's room counts)
    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)})

    stop = stash_stop(Holdings(pack, own), view({5: OPEN_PAGE}))

    assert [i.unit_id for i in stop.waits] == [50]
    assert stop.full == ()
    left = after(pack, stop)
    done = contract(left, own, Needs(), deferred=stop.waits)
    assert done.deferred == ('unique Embossed Plate at (0, 0)',)
    assert done.misses == ('block 2x4 taken',)  # the player's charms fill the inventory: no cube nor keeper miss
    assert done.cube == 1
    assert done.stash_full == ()
    # Without the ruling's deferral it is the miss it was
    assert contract(left, own, Needs()).misses == (
        'cube 1 items (unique Embossed Plate at (0, 0))',
        'block 2x4 taken',
        '1 keepers carried (unique Embossed Plate at (0, 0))',
    )


def test_a_full_stacks_flawless_gem_kept_in_the_cube_waits_there_not_a_miss():
    # 06:18 on 2026-10-19: "short of the contract: cube 1 items (normal Flawless Amethyst at (1, 1))", its stash stack
    # full and the gem kept for the transmute of three into a perfect one
    amethyst = Carried(51, class_of('Flawless Amethyst'), 2, 0, (1, 1), quality=2)
    pack = Pack((THE_CUBE,), ('..#', '...', '...', '...'), frozenset({51}), (amethyst,))
    own = own_of((THE_CUBE,))
    full = frozenset({class_of('Flawless Amethyst')})

    done = contract(pack, own, Needs(), full=full)

    assert done.misses == ()
    assert done.deferred == ('normal Flawless Amethyst at (2, 0)',)
    assert 'cube 1 items (normal Flawless Amethyst at (2, 0))' in contract(pack, own, Needs()).misses


def test_a_keeper_no_page_takes_is_the_stash_full_never_waiting():
    pack, own = grid(BLOCK_BUT_ONE | {(9, 3)})

    stop = stash_stop(Holdings(pack, own), view())

    assert stop.waits == ()
    assert [i.unit_id for i in stop.full] == [50]
    done = contract(after(pack, stop), own, Needs(), stash_full=named(stop.full), deferred=stop.waits)
    assert done.deferred == ()
    assert done.stash_full == ('unique Embossed Plate at (0, 0)',)
    assert 'cube 1 items (unique Embossed Plate at (0, 0))' in done.misses


def test_a_cube_keeper_that_comes_out_does_not_wait():
    pack, own = grid(BLOCK_BUT_ONE | {(4, 2)})  # a 2 x 3 free: it comes out

    stop = stash_stop(Holdings(pack, own), view({5: OPEN_PAGE}))

    assert stop.waits == ()
    assert (50, 'cube', 5) in [(put.item.unit_id, put.source, put.to) for put in stop.puts]


# The 99 rune stacks (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower")


def stacks(**counts: int) -> dict[int, int]:
    return {class_of(name.replace('_', ' ')): count for name, count in counts.items()}


def test_the_recipes_come_from_the_games_data_and_need_no_gem_up_to_ort():
    from inventory_tracking.macros.cube import rune_recipe

    tal = rune_recipe(class_of('Tal Rune'))
    assert tal is not None
    assert (tal.into, tal.runes, tal.gems) == (class_of('Ral Rune'), 3, ())
    assert tal.description == '3 Tal Runes -> Ral Rune'  # cubemain.txt's own row
    thul = rune_recipe(class_of('Thul Rune'))
    assert thul is not None
    assert (thul.into, thul.gems) == (class_of('Amn Rune'), (class_of('Chipped Topaz'),))
    pul = rune_recipe(class_of('Pul Rune'))
    assert pul is not None
    assert (pul.runes, pul.gems) == (2, (class_of('Flawed Diamond'),))
    assert rune_recipe(class_of('Zod Rune')) is None  # nothing makes more of it
    assert rune_recipe(class_of('Flawless Sapphire')) is None
    names = ('El', 'Eld', 'Tir', 'Nef', 'Eth', 'Ith', 'Tal', 'Ral', 'Ort', 'Thul', 'Amn')
    gem_free = [n for n in names if (r := rune_recipe(class_of(f'{n} Rune'))) is not None and not r.gems]
    assert gem_free == ['El', 'Eld', 'Tir', 'Nef', 'Eth', 'Ith', 'Tal', 'Ral', 'Ort']


def test_a_99_stack_is_transmuted_three_a_visit_until_it_is_at_80_or_lower():
    tal, ral = class_of('Tal Rune'), class_of('Ral Rune')
    counts = stacks(Tal_Rune=99, Ral_Rune=10)

    assert rune_transmutes(counts) == (RuneCube(tal, ral),) * RUNE_TRANSMUTES  # 99 -> 90, Ral 13
    visits = 0
    while plan := rune_transmutes(counts):
        visits += 1
        counts[tal] -= 3 * len(plan)
        counts[ral] += len(plan)
    assert counts[tal] == 78  # seven transmutes: at RUNES_AIM or lower, never further
    assert counts[tal] <= RUNES_AIM < counts[tal] + 3
    assert visits == 3
    assert rune_transmutes(counts, most=10) == ()


def test_the_fullest_stack_goes_first_and_a_rune_whose_gem_is_missing_is_skipped():
    tal, ral, eth, ith = (class_of(f'{n} Rune') for n in ('Tal', 'Ral', 'Eth', 'Ith'))
    counts = stacks(Thul_Rune=99, Amn_Rune=95, Tal_Rune=99, Eth_Rune=89, Ral_Rune=50, Ith_Rune=40)

    plan = rune_transmutes(counts, most=6)

    # Tal 99, 96, 93, 90 before Eth 89; then Eth 89 before Tal 87; then Tal 87 before Eth 86
    assert plan == (RuneCube(tal, ral),) * 4 + (RuneCube(eth, ith), RuneCube(tal, ral))
    assert all(step.txt not in (class_of('Thul Rune'), class_of('Amn Rune')) for step in plan)
    said = dict(uncubed(counts))  # no chipped gem in the stash
    assert said[class_of('Thul Rune')] == (
        'no Chipped Topaz in the stash for its recipe (3 Thul Runes + 1 Chipped Topaz -> Amn Rune)'
    )
    assert class_of('Tal Rune') not in said


def test_a_rune_whose_made_stack_is_full_is_not_transmuted():
    counts = stacks(Ort_Rune=93, Thul_Rune=98)

    assert rune_transmutes(counts) == (RuneCube(class_of('Ort Rune'), class_of('Thul Rune')),)  # one, Thul then 99
    counts = stacks(Ort_Rune=93, Thul_Rune=99)
    assert rune_transmutes(counts) == ()
    assert dict(uncubed(counts))[class_of('Ort Rune')] == 'the stack it makes is full'


def test_the_stash_stop_plans_the_rune_transmutes_with_the_cube_empty_and_the_carried_tal_after_them():
    tal = thing(20, 'Tal Rune', 6, 3)
    pack = Pack((THE_CUBE, *OWN_CHARMS, tal), ('...',) * 4)

    stop = stash_stop(Holdings(pack, OWN), view(Tal_Rune=99, Ral_Rune=10))

    assert stop.puts == ()  # the full stack refuses it now
    assert stop.runes == (RuneCube(tal.txt, class_of('Ral Rune')),) * 3
    assert stop.rune_puts == (Put(tal, 'inventory', -4),)  # onto the room the transmutes make
    assert not stop.idle
    assert all(i.unit_id != tal.unit_id for i in after(pack, stop).items)


def test_no_rune_transmute_while_the_cube_keeps_something():
    plate = replace(Carried(50, class_of('Embossed Plate'), 0, 0, (2, 3)), quality=7)
    pack = Pack((THE_CUBE, *OWN_CHARMS), ('##.', '##.', '##.', '...'), frozenset({50}), (plate,))

    stop = stash_stop(Holdings(pack, OWN), view(Tal_Rune=99))  # every page full: the plate stays

    assert stop.runes == ()
    assert stop.rune_puts == ()


def test_a_stack_at_80_is_left_and_the_stop_with_nothing_else_is_idle():
    stop = stash_stop(Holdings(Pack((THE_CUBE, *OWN_CHARMS), ('...',) * 4), OWN), view(Tal_Rune=80))

    assert stop.runes == ()
    assert stop.idle


# Gem recipes (the player, 18:31 on 2026-10-18: "yes, loop should use required gems + runes")


def test_thul_and_amn_over_80_are_cubed_with_the_gems_their_recipes_take():
    thul, amn, sol = (class_of(f'{n} Rune') for n in ('Thul', 'Amn', 'Sol'))
    topaz, amethyst = class_of('Chipped Topaz'), class_of('Chipped Amethyst')
    counts = stacks(Thul_Rune=95, Amn_Rune=94, Sol_Rune=73, Chipped_Topaz=24, Chipped_Amethyst=26)

    plan = rune_transmutes(counts, most=4)

    # Thul 95, then Amn 95 (94 and the one made), then Thul 92 against Amn 92 (the smaller rune), then Amn 92
    assert plan == (
        RuneCube(thul, amn, topaz),
        RuneCube(amn, sol, amethyst),
        RuneCube(thul, amn, topaz),
        RuneCube(amn, sol, amethyst),
    )


def test_a_gem_recipe_takes_only_the_gems_the_stash_has():
    thul, amn, topaz = class_of('Thul Rune'), class_of('Amn Rune'), class_of('Chipped Topaz')

    assert rune_transmutes(stacks(Thul_Rune=99, Amn_Rune=10, Chipped_Topaz=1)) == (RuneCube(thul, amn, topaz),)
    assert rune_transmutes(stacks(Thul_Rune=99, Amn_Rune=10)) == ()


def test_the_stash_stop_plans_a_gem_recipe_with_the_carried_gem_put_on_its_stack_first():
    # The carried Chipped Topaz goes onto its stack in the stop's tab puts; the transmute takes it from there
    topaz = thing(21, 'Chipped Topaz', 6, 3)
    pack = Pack((THE_CUBE, *OWN_CHARMS, topaz), ('...',) * 4)

    stop = stash_stop(Holdings(pack, OWN), view(Thul_Rune=95, Amn_Rune=10))

    assert Put(topaz, 'inventory', -2) in stop.puts
    assert stop.runes == (RuneCube(class_of('Thul Rune'), class_of('Amn Rune'), topaz.txt),)


def test_a_ber_rune_is_never_cubed_whatever_the_recipe(monkeypatch):
    # Ber is kept for Enigma (the player, 2026-10-09): not by its own recipe (two Ber and a Flawless Sapphire), nor by
    # one of three runes and no gem the data might give
    from inventory_tracking.macros import town
    from inventory_tracking.macros.cube import RuneRecipe

    ber, jah = class_of('Ber Rune'), class_of('Jah Rune')
    assert ber == town.BER
    counts = stacks(Ber_Rune=99, Jah_Rune=0, Flawless_Sapphire=50)
    assert rune_transmutes(counts) == ()
    assert dict(uncubed(counts))[ber] == 'Ber Runes are kept for Enigma'
    monkeypatch.setattr(town, 'rune_recipe', lambda txt: RuneRecipe(jah, 3) if txt == ber else None)
    assert rune_transmutes(counts) == ()
    # Nor as a recipe's other input
    sur = class_of('Sur Rune')
    monkeypatch.setattr(town, 'rune_recipe', lambda txt: RuneRecipe(ber, 3, (ber,)) if txt == sur else None)
    assert rune_transmutes(stacks(Sur_Rune=99, Ber_Rune=5)) == ()
