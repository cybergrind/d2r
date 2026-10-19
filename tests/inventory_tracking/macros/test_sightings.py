import pytest

from inventory_tracking.game.records import GOLD, VALUABLE, Drop, Loot
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.sightings import FETCH_SECONDS, FETCH_TRIES, Sightings


LK = 79
GAME = ('game-1', 7)


def loot(*drops: Drop, game=GAME) -> Loot:
    return Loot(drops=drops, game=game)


def emerald(x=5798.0, y=2870.0) -> Drop:
    return Drop(41, x, y, 'Flawless Emerald', VALUABLE)


def test_a_valuable_seen_in_flight_is_remembered_once_out_of_the_read():
    # The Flawless Emerald of 08:58:34 on 2026-10-17: seen in a Blade Warp's flight, then 104 units off and unread
    seen = Sightings()
    seen.update(loot(emerald()), (5790.0, 2860.0), LK, 0.0)
    seen.update(loot(), (5695.0, 2857.0), LK, 25.0)
    assert seen.left() == 'Flawless Emerald at (5798, 2870)'
    assert not seen.outstanding()[0].read


def test_a_valuable_not_read_near_its_place_is_off_the_ground():
    seen = Sightings()
    seen.update(loot(emerald()), (5700.0, 2860.0), LK, 0.0)
    seen.update(loot(), (5795.0, 2868.0), LK, 3.0)  # picked up (or gone): the character by it, the unit unread
    assert seen.left() is None


def test_gold_and_potions_are_not_remembered_and_a_new_game_forgets_the_last():
    seen = Sightings()
    seen.update(loot(Drop(9, 0.0, 0.0, '900 gold', GOLD), emerald()), (0.0, 0.0), LK, 0.0)
    assert [found.label for found in seen.outstanding()] == ['Flawless Emerald']
    seen.update(loot(game=('game-2', 7)), (0.0, 0.0), LK, 60.0)
    assert seen.left() is None


def test_an_unread_ground_or_another_area_resolves_nothing():
    seen = Sightings()
    seen.update(loot(emerald()), (5700.0, 2860.0), LK, 0.0)
    seen.update(Loot(), (5798.0, 2870.0), LK, 1.0)  # an empty Loot: the character unread
    seen.update(loot(), (5798.0, 2870.0), 75, 2.0)  # the same place, in another level
    assert seen.left() is not None


def test_fetch_goes_back_to_the_nearest_then_stops_the_loop_after_its_tries():
    seen = Sightings()
    seen.update(loot(emerald(), Drop(42, 5000.0, 3000.0, 'Small Charm', VALUABLE)), (5100.0, 3000.0), LK, 0.0)
    gone_to = []
    for _ in range(FETCH_TRIES):
        assert seen.fetch((5100.0, 3000.0), LK, 10.0, lambda found: gone_to.append(found.label))
    assert gone_to == ['Small Charm'] * FETCH_TRIES
    with pytest.raises(Abort, match='Small Charm at \\(5000, 3000\\) was not picked up after 2 trips back'):
        seen.fetch((5100.0, 3000.0), LK, 11.0, lambda found: None)


def test_fetch_has_nothing_to_do_elsewhere_and_a_game_has_its_seconds():
    seen = Sightings()
    seen.update(loot(emerald()), (5700.0, 2860.0), LK, 0.0)
    assert not seen.fetch((0.0, 0.0), 75, 1.0, lambda found: None)  # in Kurast Docks: not this level's
    assert seen.fetch((5700.0, 2860.0), LK, 1.0, lambda found: None)
    with pytest.raises(Abort):
        seen.fetch((5700.0, 2860.0), LK, 2.0 + FETCH_SECONDS, lambda found: None)


def test_again_after_a_trip_for_room_gives_the_trips_back_and_the_seconds_again():
    # 13:16:00 on 2026-10-18: "not picked up after 2 trips back" 2 s after the return through the portal
    seen = Sightings()
    seen.update(loot(emerald()), (5700.0, 2860.0), LK, 0.0)
    for _ in range(FETCH_TRIES):
        assert seen.fetch((5700.0, 2860.0), LK, 1.0, lambda found: None)
    seen.again()
    assert seen.fetch((5700.0, 2860.0), LK, 3.0 + FETCH_SECONDS, lambda found: None)  # the trip's seconds forgiven
    assert seen.outstanding()[0].tries == 1


def test_a_candidate_for_an_identify_is_not_remembered():
    # A magic Kriss is taken to be identified and maybe sold (macros/pickmode.py `candidate`): no game is kept for it
    kriss = Drop(43, 5798.0, 2870.0, 'Magic Kriss', VALUABLE, (1, 3), prized=False, source='shown', txt=41, quality=4)
    seen = Sightings()
    seen.update(loot(kriss), (5790.0, 2860.0), LK, 0.0)
    assert seen.left() is None


def test_a_valuable_read_at_its_inventory_cell_while_picked_up_is_still_where_it_lay():
    # 19:02:23 on 2026-10-17: a read in the moment of the pickup had a Chipped Sapphire at (3, 3), its inventory cell;
    # remembered there, 5372 units off, it was gone back for twice and the loop stopped for the player
    seen = Sightings()
    seen.update(loot(emerald()), (5790.0, 2870.0), LK, 0.0)
    seen.update(loot(emerald(3.0, 3.0)), (5795.0, 2870.0), LK, 0.1)
    seen.update(loot(), (5796.0, 2870.0), LK, 0.2)
    assert seen.outstanding() == []
