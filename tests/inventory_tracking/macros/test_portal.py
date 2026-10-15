"""Town Portal out of a level (routes/lower-kurast-loop-plan.md phase 3): the tome's key, the portal beside the
character once it is open, the click, the town."""

import pytest

from inventory_tracking.levels.model import TOWN_PORTAL
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.portal import TOME, to_town
from inventory_tracking.macros.world import Thing
from tests.inventory_tracking.macros.fakes import KEYS, Game, world


LOWER_KURAST, KURAST_DOCKS = 79, 75


def keys(_world, skills):
    return {skill: {**KEYS, TOME: 'x'}[skill] for skill in skills}


def lower_kurast() -> Game:
    play = Game(world(LOWER_KURAST))
    play.next_area = KURAST_DOCKS
    return play


def test_the_tome_is_cast_and_its_portal_taken_once_open():
    play = lower_kurast()
    play.portal_opens = 0.6

    to_town(play.run(), keys)

    assert play.pressed() == ['x']
    assert play.character.area == KURAST_DOCKS
    clicks = [event for event in play.keys.events if event[0] == 'click']
    assert len(clicks) == 1  # not at the portal while it opened
    assert play.clock.now >= 0.6
    assert play.said[-2:] == ['Through the portal to town, 4 away', 'town: there']


def test_a_portal_that_was_open_before_the_cast_is_not_the_new_one():
    play = lower_kurast()
    play.thing = Thing(9, TOWN_PORTAL, 2, 5030.0, 5000.0)  # the portal of an earlier trip, open
    play.portal_opens = None  # the tome casts nothing

    with pytest.raises(Abort, match='no Town Portal opened'):
        to_town(play.run(), keys)
    assert play.character.area == LOWER_KURAST
    assert [event for event in play.keys.events if event[0] == 'click'] == []


def test_with_no_portal_after_the_cast_it_stops_saying_so():
    play = lower_kurast()
    play.portal_opens = None

    with pytest.raises(Abort, match=r'no Town Portal opened .* is the tome empty\?'):
        to_town(play.run(), keys)
    assert play.pressed() == ['x']


def test_in_town_nothing_is_cast():
    play = Game(world(KURAST_DOCKS))

    with pytest.raises(Abort, match='in town already'):
        to_town(play.run(), keys)
    assert play.keys.events == []
