import pytest

from inventory_tracking.game.records import GOLD, VALUABLE, Drop, Loot
from inventory_tracking.macros import sightings as sightings_module
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.sightings import ARRIVAL_SECONDS, FETCH_SECONDS, FETCH_TRIES, Sightings


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


def test_fetch_goes_to_another_level_only_with_none_left_here_and_only_one_it_can_cross_to():
    # 00:05:52 on 2026-10-20: the Grand Charm in the Outer Steppes (104), the character in the Plains of Despair (105)
    seen = Sightings()
    seen.update(loot(Drop(7, 5477.0, 5092.0, 'Grand Charm', VALUABLE)), (5470.0, 5090.0), 104, 0.0)
    gone_to = []
    assert not seen.fetch((5248.0, 5223.0), 105, 5.0, lambda found: gone_to.append(found.label))  # as before
    assert not seen.fetch((5248.0, 5223.0), 105, 5.0, gone_to.append, across=lambda area: False)
    assert seen.fetch((5248.0, 5223.0), 105, 5.0, lambda found: gone_to.append(found.area), across=lambda a: a == 104)
    assert gone_to == [104]
    seen.update(loot(emerald(5250.0, 5230.0)), (5248.0, 5223.0), 105, 6.0)
    assert seen.fetch((5248.0, 5223.0), 105, 7.0, lambda found: gone_to.append(found.label), across=lambda a: True)
    assert gone_to[-1] == 'Flawless Emerald'  # one on this level first


CITY = 106


def bow(x=5628.0, y=4499.0) -> Drop:
    return Drop(43, x, y, 'Unique Double Bow', VALUABLE)


def test_back_through_the_portal_a_valuable_unread_at_the_arrival_is_not_taken_for_gone():
    # 2026-10-21 00:55:22: back from the trip for room, the first read held no ground units, the Double Bow 2 units
    # off was forgotten as taken and the game was left with it ("that is VERY BAD")
    seen = Sightings()
    seen.update(loot(bow()), (5640.0, 4492.0), CITY, 0.0)
    seen.update(loot(), (5048.0, 5049.0), 103, 1.0)  # the town
    seen.update(loot(), (5626.5, 4497.5), CITY, 20.0)  # back: the level's units not read yet
    assert seen.left() == 'Unique Double Bow at (5628, 4499)'
    seen.update(loot(), (5626.5, 4497.5), CITY, 20.0 + ARRIVAL_SECONDS + 0.1)  # settled, still unread: taken
    assert seen.left() is None


def test_with_no_arrival_grace_the_first_read_judges_as_before(monkeypatch):
    monkeypatch.setattr(sightings_module, 'ARRIVAL_SECONDS', 0.0)
    seen = Sightings()
    seen.update(loot(bow()), (5640.0, 4492.0), CITY, 0.0)
    seen.update(loot(), (5048.0, 5049.0), 103, 1.0)
    seen.update(loot(), (5626.5, 4497.5), CITY, 20.0)
    assert seen.left() is None


# -- a read that still holds the level just left (16:28:26 on 2026-10-21, session 20261021T131533Z-b2235979) --------

TRAVINCAL, DURANCE_1 = 83, 100
DURANCE_HERE = (17634.0, 5216.0)


def charm() -> Drop:
    return Drop(77, 5153.0, 1496.0, 'Large Charm', VALUABLE)


def test_a_drop_read_far_off_after_a_level_change_is_remembered_on_the_level_left_and_never_planned_here():
    seen = Sightings()
    seen.update(loot(), (5158.0, 1487.0), TRAVINCAL, 0.0)
    seen.update(loot(charm()), DURANCE_HERE, DURANCE_1, 1.0)  # 13 ms into Durance of Hate 1: Travincal's charm
    (found,) = seen.outstanding()
    assert found.area == TRAVINCAL
    went: list = []
    assert not seen.fetch(DURANCE_HERE, DURANCE_1, 2.0, went.append)  # never across Durance's rooms
    assert went == []
    assert seen.left() == 'Large Charm at (5153, 1496)'  # still on the ground: the guard keeps the game
    seen.update(loot(), (5150.0, 1490.0), TRAVINCAL, 30.0)  # back on Travincal, by its place
    seen.update(loot(), (5150.0, 1490.0), TRAVINCAL, 30.0 + ARRIVAL_SECONDS)  # settled, unread: off the ground
    assert seen.left() is None


def test_a_sighting_noted_on_the_wrong_level_is_not_planned_and_one_carried_now_is_dropped(caplog):
    # The kept state of the live service: the charm noted on Durance 1, 12949 away; the player took it by hand
    seen = Sightings()
    seen.update(loot(), DURANCE_HERE, DURANCE_1, 0.0)
    seen.items[77] = sightings_module.Sighting(77, 'Large Charm', 5153.0, 1496.0, DURANCE_1, 0.0)
    went: list = []
    assert not seen.fetch(DURANCE_HERE, DURANCE_1, 1.0, went.append)
    assert went == []
    with caplog.at_level('INFO'):
        seen.update(loot(), DURANCE_HERE, DURANCE_1, 2.0)
    assert seen.outstanding()[0].area != DURANCE_1  # not on this level
    with caplog.at_level('INFO'):
        seen.update(Loot(game=GAME, carried=frozenset({77})), DURANCE_HERE, DURANCE_1, 3.0)
    assert seen.left() is None
    assert 'Macro: remembered Large Charm at (5153, 1496): carried now' in caplog.text
