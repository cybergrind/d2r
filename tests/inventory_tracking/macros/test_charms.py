"""Gheed's Fortune is carry-one: the player's onto the stash page for another one, and back (macros/charms.py)."""

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, gheeds, grand_charm, put_away, take_back
from inventory_tracking.macros.cube import CUBE_CLASS, own_of
from inventory_tracking.macros.world import BANK, Carried, Pack, Thing
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103
EMPTY_PAGE = ('.' * 10,) * 10


def test_the_players_gheeds_goes_onto_the_stash_page_and_comes_back_for_the_new_one_to_stay():
    # The player, 2026-10-18: "go to the shared stash tab and put our current charm there, then go back and pickup
    # another gheed charm. go to shared stash tab, put new there and bring our's back"
    cube = Carried(2, CUBE_CLASS, 1, 0, (2, 2))
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    own = own_of((cube, theirs))
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    play.pack = Pack((theirs, cube), ('...',) * 4, stash=EMPTY_PAGE)

    assert gheeds(play.pack, own) == theirs
    placed = put_away(play.run(), theirs)
    assert play.pack.items == (cube,)
    assert [i.unit_id for i in play.pack.stashed] == [theirs.unit_id]
    assert play.world.open_panels == ()

    new = Carried(7, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, identified=False)  # where theirs was
    play.pack = Pack((cube, new), ('...',) * 4, stashed=play.pack.stashed, stash=play.pack.stash)
    back = take_back(play.run(), placed, new.unit_id)

    assert back.unit_id == theirs.unit_id
    assert [i.unit_id for i in play.pack.items] == [cube.unit_id, theirs.unit_id]
    assert [i.unit_id for i in play.pack.stashed] == [new.unit_id]
    assert play.world.open_panels == ()


def test_with_no_room_on_the_stash_page_the_players_gheeds_stays_carried():
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    play.pack = Pack((theirs,), ('...',) * 4, stash=('#' * 10,) * 10)

    with pytest.raises(Abort, match='no room on the personal stash page'):
        put_away(play.run(), theirs)
    assert play.pack.items == (theirs,)


def test_only_an_identified_unique_grand_charm_of_gheeds_row_is_the_players_gheeds():
    sunder = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=426)  # Latent Cold Rupture
    unread = Carried(2, grand_charm(), 1, 0, (1, 3), quality=UNIQUE, identified=False)
    pack = Pack((sunder, unread))
    assert gheeds(pack, own_of((sunder, unread))) is None
