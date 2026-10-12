"""Chests opened by the pickup step (macros/opening.py): the containers by the character, else a super chest."""

import pytest

from inventory_tracking.loot.ground import SPARKLY_CHEST
from inventory_tracking.macros import opening
from inventory_tracking.macros.opening import NEAR_UNITS, choose, open_near
from inventory_tracking.macros.world import Teleport, Thing, containers
from tests.inventory_tracking.macros.fakes import KEYS, SLOTS, Game, world


ORIGIN = (5000.0, 5000.0)
URN, CHEST, EXPLODING_BARREL, SHRINE = 4, 5, 11, 2  # objects.txt ids: Urn1, LargeChestR, BarrelExploding, Shrine


@pytest.fixture(autouse=True)
def nothing_shunned():
    opening.SHUNNED.clear()


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def game(thing, above=10.0):
    play = Game(world(area=101, slots=SLOTS))
    play.staff = Teleport(10, 20, True)
    play.thing, play.thing_above = thing, above
    return play


def test_containers_are_what_is_opened_for_what_it_holds_and_nothing_that_blows_up():
    assert {URN, CHEST, SPARKLY_CHEST} <= containers()
    assert not {EXPLODING_BARREL, SHRINE} & containers()


def test_the_nearest_unopened_container_by_the_character_comes_first_then_a_super_chest_further_off():
    urn = Thing(1, URN, 0, 5008.0, 5000.0)
    chest = Thing(2, CHEST, 0, 5004.0, 5000.0)
    far = Thing(3, CHEST, 0, 5000.0 + NEAR_UNITS + 1, 5000.0)
    sparkly = Thing(4, SPARKLY_CHEST, 0, 5040.0, 5000.0)
    assert choose((urn, chest, far, sparkly), ORIGIN, 0.0).thing == chest
    assert choose((Thing(2, CHEST, 2, 5004.0, 5000.0), urn, sparkly), ORIGIN, 0.0).thing == urn  # opened already
    found = choose((far, sparkly), ORIGIN, 0.0)
    assert (found.thing, found.label) == (sparkly, 'the super chest')
    assert choose((far, Thing(4, SPARKLY_CHEST, 2, 5040.0, 5000.0)), ORIGIN, 0.0) is None  # opened: not usable
    opening.SHUNNED[4] = 10.0
    assert choose((sparkly,), ORIGIN, 5.0) is None  # no click opened it a moment ago
    assert choose((sparkly,), ORIGIN, 11.0).thing == sparkly


def test_a_press_opens_the_chest_by_the_character_with_the_chest_under_the_pointer(caplog):
    play = game(Thing(7, CHEST, 0, 5006.0, 5002.0))
    with caplog.at_level('INFO'):
        assert open_near(play.run(), None, keys)
    assert play.thing.mode != 0
    assert play.said == ['Opening LargeChestR, 6 away', 'LargeChestR: opened']
    assert 'opened' in caplog.text


def test_a_chest_no_aim_finds_is_left_alone_for_a_while_and_the_press_is_spent_on_it():
    play = game(Thing(7, CHEST, 0, 5006.0, 5002.0), above=200.0)  # its picture is nowhere the aims look
    run = play.run()
    assert open_near(run, None, keys)
    assert play.thing.mode == 0
    assert play.said[-1] == 'LargeChestR: not opened'
    assert not [event for event in play.keys.events if event[0] == 'button']  # nothing was clicked unseen
    assert not open_near(run, None, keys)  # the next press goes on to the seek step


def test_with_nothing_to_open_the_press_is_not_spent():
    assert not open_near(game(None).run(), None, keys)
    assert not open_near(game(Thing(7, CHEST, 2, 5006.0, 5002.0)).run(), None, keys)


def test_the_games_own_flag_says_whether_a_container_can_be_used_before_the_table_does():
    # Mode 0 and the flag clear: not to be clicked; an unknown mode and the flag set: it is.
    assert choose((Thing(7, CHEST, 0, 5004.0, 5000.0, selectable=False),), ORIGIN, 0.0) is None
    assert choose((Thing(7, CHEST, 3, 5004.0, 5000.0, selectable=True),), ORIGIN, 0.0) is not None
    assert choose((Thing(7, SHRINE, 0, 5004.0, 5000.0, selectable=True),), ORIGIN, 0.0) is None  # no container
