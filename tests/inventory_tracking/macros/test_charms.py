"""Gheed's Fortune is carry-one: the player's onto a shared stash page for another, the better kept (macros/charms.py).

The player, 2026-10-18 13:39: "go to town; put our own gheed into SHARED tab; go back and pick new one; go to town,
identify; check what is better (magic find roll); keep in own inventory better one"."""

import pytest

from inventory_tracking.game.layout import BANK
from inventory_tracking.game.records import Carried, Pack, Thing
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.charms import (
    GHEEDS_FORTUNE,
    MAGIC_FIND,
    UNIQUE,
    Parked,
    candidates,
    choose,
    gheeds,
    grand_charm,
    park,
)
from inventory_tracking.macros.cube import CUBE_CLASS, own_of
from inventory_tracking.macros.visit import Remembered
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103
EMPTY = ('.' * 10,) * 10
FULL = ('#' * 10,) * 10


def stash_game(pack: Pack, pages: list[tuple[str, ...]]) -> Game:
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    play.pack = pack
    play.stash_pages = pages
    return play


def theirs_at(x: int = 0, y: int = 0) -> Carried:
    return Carried(1, grand_charm(), x, y, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)


def test_the_players_gheeds_goes_onto_a_shared_page_with_room_never_the_personal_one():
    # "you cannot pickup another gheed if you have another in inventory/private tab": the personal page has room and is
    # not used; shared page 1 is full, and priority sends it to page 3
    cube, theirs = Carried(2, CUBE_CLASS, 1, 0, (2, 2)), theirs_at()
    play = stash_game(Pack((theirs, cube), ('...',) * 4), [EMPTY, FULL, EMPTY, EMPTY, EMPTY, EMPTY])

    parked = park(play.run(), theirs, {1: {MAGIC_FIND: 31}}.get, Remembered())

    assert parked == Parked(1, 3, (theirs.txt, 0, 0), 31)
    assert carried(play).items == (cube,)
    assert play.page_items == {3: [1]}
    assert play.world.open_panels == ()


def test_with_no_room_on_any_shared_page_the_players_gheeds_stays_carried():
    theirs = theirs_at()
    play = stash_game(Pack((theirs,), ('...',) * 4), [EMPTY, FULL, FULL, FULL, FULL, FULL])

    with pytest.raises(Abort, match='no shared stash page has room'):
        park(play.run(), theirs, None)
    assert carried(play).items == (theirs,)
    assert play.page_items == {}


def test_a_better_new_gheeds_stays_carried_at_the_players_cell_and_theirs_stays_on_the_shared_page():
    cube, theirs = Carried(2, CUBE_CLASS, 1, 0, (2, 2)), theirs_at()
    play = stash_game(Pack((theirs, cube), ('...',) * 4), [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY])
    stats = {1: {MAGIC_FIND: 25}, 7: {MAGIC_FIND: 38}}
    parked = park(play.run(), theirs, stats.get)
    new = Carried(7, grand_charm(), 9, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)  # picked up elsewhere
    play.pack = Pack((cube, new), ('...',) * 4)

    kept = choose(play.run(), parked, new, stats.get)

    assert (kept.unit_id, kept.x, kept.y) == (7, 0, 0)  # at the player's cell
    assert play.page_items == {3: [1]}
    assert play.world.open_panels == ()


@pytest.mark.parametrize('rolls', [(38, 25), (30, 30)], ids=['theirs better', 'a tie'])
def test_the_players_better_or_equal_gheeds_comes_back_to_its_cell_and_the_new_one_onto_a_shared_page(rolls):
    mine, newer = rolls
    cube, theirs = Carried(2, CUBE_CLASS, 1, 0, (2, 2)), theirs_at()
    play = stash_game(Pack((theirs, cube), ('...',) * 4), [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY])
    stats = {1: {MAGIC_FIND: mine}, 7: {MAGIC_FIND: newer}}
    parked = park(play.run(), theirs, stats.get)
    new = Carried(7, grand_charm(), 9, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play.pack = Pack((cube, new), ('...',) * 4)

    kept = choose(play.run(), parked, new, stats.get)

    assert (kept.unit_id, kept.x, kept.y) == (1, 0, 0)
    assert sorted(i.unit_id for i in carried(play).items) == [1, 2]
    assert play.page_items == {3: [7]}
    assert play.world.open_panels == ()


def test_with_no_new_gheeds_the_players_comes_back():
    theirs = theirs_at(3, 1)
    play = stash_game(Pack((theirs,), ('...',) * 4), [EMPTY, FULL, EMPTY, EMPTY, EMPTY, EMPTY])
    parked = park(play.run(), theirs, None)

    kept = choose(play.run(), parked, None, None)

    assert (kept.unit_id, kept.x, kept.y) == (1, 3, 1)
    assert play.page_items == {3: []}


def test_a_new_charm_not_gheeds_in_the_players_cell_goes_onto_a_shared_page_for_the_players_to_come_back():
    # The player, 2026-10-18 16:50: "refused grand charm - should cause a trip": the swap is made with no 1 x 3 free
    # but the player's own cell, which the new charm takes; a Latent Sunder charm (no Gheed's Fortune to compare)
    # must not keep the player's in the stash for want of a block to come back to
    from inventory_tracking.macros.charms import newcomers

    theirs = theirs_at()
    filler = tuple(Carried(10 + x, 999, x, 0, (1, 4)) for x in range(1, 10))  # columns 1-9 taken
    play = stash_game(Pack((theirs, *filler), ('...',) * 4), [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY])
    parked = park(play.run(), theirs, None)
    sunder = Carried(8, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=426)  # picked up into the player's cell
    play.pack = Pack((sunder, *filler), ('...',) * 4)
    assert newcomers(carried(play), parked, frozenset({1, *(i.unit_id for i in filler)})) == [sunder]

    kept = choose(play.run(), parked, None, None, others=(sunder,))

    assert (kept.unit_id, kept.x, kept.y) == (1, 0, 0)
    assert play.page_items == {3: [8]}  # the player's left page 3, the Sunder charm onto it
    assert play.world.open_panels == ()


def test_the_new_one_is_a_unique_grand_charm_not_carried_before_unidentified_or_of_gheeds_row():
    parked = Parked(1, 1, (grand_charm(), 0, 0), 30)
    old = Carried(3, grand_charm(), 2, 0, (1, 3), quality=UNIQUE, identified=False)
    new = Carried(7, grand_charm(), 4, 0, (1, 3), quality=UNIQUE, identified=False)
    sunder = Carried(8, grand_charm(), 5, 0, (1, 3), quality=UNIQUE, unique=426)
    pack = Pack((old, new, sunder))
    assert candidates(pack, parked, frozenset({3})) == [new]
    assert Parked.restore(parked.state()) == parked
    assert Parked.restore({'bad': 1}) is None


def test_only_an_identified_unique_grand_charm_of_gheeds_row_is_the_players_gheeds():
    sunder = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=426)  # Latent Cold Rupture
    unread = Carried(2, grand_charm(), 1, 0, (1, 3), quality=UNIQUE, identified=False)
    pack = Pack((sunder, unread))
    assert gheeds(pack, own_of((sunder, unread))) is None


def carried(play: Game) -> Pack:
    assert play.pack is not None
    return play.pack


# The player, 2026-10-21 ~09:00: "I have dropped low roll gheed's charms, it looks like we don't need that many of
# them. low rolls doesn't sell"; keep only "MF38, or MF35 + very good gold roll"; "also - do not sell our current gheed
# charm" (charms.py GHEEDS_LOW_DOWN, loot/keep.py GHEEDS_MF, GHEEDS_MF_WITH_GOLD, GHEEDS_GOLD)
GOLD_FIND = 79


def swap(mine: dict[int, int], newer: dict[int, int] | None) -> tuple[Game, Parked, Carried, dict]:
    """The player's Gheed's (unit 1) parked on page 3, the new one (unit 7) carried, both with `stats`."""
    cube, theirs = Carried(2, CUBE_CLASS, 1, 0, (2, 2)), theirs_at()
    play = stash_game(Pack((theirs, cube), ('...',) * 4), [EMPTY, FULL, EMPTY, EMPTY, EMPTY, EMPTY])
    stats = {1: mine} if newer is None else {1: mine, 7: newer}
    parked = park(play.run(), theirs, stats.get)
    new = Carried(7, grand_charm(), 9, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play.pack = Pack((cube, new), ('...',) * 4)
    return play, parked, new, stats


def test_a_low_new_gheeds_that_loses_is_put_down_in_town_not_stashed_and_the_players_comes_back(caplog):
    from inventory_tracking.macros import visit

    play, parked, new, stats = swap({MAGIC_FIND: 36}, {MAGIC_FIND: 30, GOLD_FIND: 150})

    with caplog.at_level('INFO'):
        kept = choose(play.run(), parked, new, stats.get)

    assert (kept.unit_id, kept.x, kept.y) == (1, 0, 0)
    assert [i.unit_id for i in play.fallen] == [7]
    assert play.page_items == {3: []}  # the player's left page 3, nothing put on a shared page
    assert sorted(i.unit_id for i in carried(play).items) == [1, 2]
    assert play.world.open_panels == ()
    assert "the new Gheed's Fortune is low (magic find 30%, gold find 150%): put down in town, not stashed" in (
        caplog.text
    )
    assert visit._down['items'] == 1  # it lies by the stash: counted with the town's (visit.py DOWN_A_GAME)


@pytest.mark.parametrize(
    'newer', [{MAGIC_FIND: 38, GOLD_FIND: 80}, {MAGIC_FIND: 35, GOLD_FIND: 140}], ids=['MF 38', 'MF 35 gold 140']
)
def test_a_good_new_gheeds_that_loses_is_stashed_as_before(newer):
    play, parked, new, stats = swap({MAGIC_FIND: 40}, newer)

    kept = choose(play.run(), parked, new, stats.get)

    assert kept.unit_id == 1
    assert play.fallen == []
    assert play.page_items == {3: [7]}


@pytest.mark.parametrize('newer', [None, {MAGIC_FIND: 25}, {GOLD_FIND: 90}], ids=['none read', 'gold', 'magic find'])
def test_a_new_gheeds_whose_rolls_are_unread_is_stashed_as_before(newer):
    play, parked, new, stats = swap({MAGIC_FIND: 36}, newer)

    kept = choose(play.run(), parked, new, stats.get)

    assert kept.unit_id == 1
    assert play.fallen == []
    assert play.page_items == {3: [7]}


def test_a_low_new_gheeds_that_wins_is_carried_and_the_players_stays_on_the_shared_page():
    play, parked, new, stats = swap({MAGIC_FIND: 20, GOLD_FIND: 80}, {MAGIC_FIND: 30, GOLD_FIND: 90})

    kept = choose(play.run(), parked, new, stats.get)

    assert (kept.unit_id, kept.x, kept.y) == (7, 0, 0)
    assert play.fallen == []
    assert play.page_items == {3: [1]}


@pytest.mark.parametrize('rival', [True, False], ids=['a low tie', 'no new one'])
def test_the_players_low_gheeds_is_never_put_down(rival):
    low = {MAGIC_FIND: 22, GOLD_FIND: 85}
    play, parked, new, stats = swap(low, dict(low) if rival else None)

    kept = choose(play.run(), parked, new if rival else None, stats.get)

    assert (kept.unit_id, kept.x, kept.y) == (1, 0, 0)
    assert [i.unit_id for i in play.fallen] == ([7] if rival else [])
    assert all(i.unit_id != 1 for i in play.fallen)


def test_with_the_switch_off_a_low_loser_is_stashed_as_before(monkeypatch):
    from inventory_tracking.macros import charms

    monkeypatch.setattr(charms, 'GHEEDS_LOW_DOWN', False)
    play, parked, new, stats = swap({MAGIC_FIND: 36}, {MAGIC_FIND: 30, GOLD_FIND: 90})

    kept = choose(play.run(), parked, new, stats.get)

    assert kept.unit_id == 1
    assert play.fallen == []
    assert play.page_items == {3: [7]}
