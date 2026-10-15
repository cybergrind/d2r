"""The town's waypoint, clicked from where a game or a portal puts the character (routes/lower-kurast-loop-plan.md
phase 1): the game walks there and opens the panel."""

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.waypoint import open_panel
from inventory_tracking.macros.world import Thing
from tests.inventory_tracking.macros.fakes import Game, player, world


KURAST_DOCKS, LOWER_KURAST = 75, 79
WAYPOINT_ACT3 = 237  # objects.txt WaypointAct3


def docks(**at) -> Game:
    """Kurast Docks as the portal from Lower Kurast leaves the character: (5158, 5068), 20 units south of the
    waypoint (the player's nine trips of 2026-10-15)."""
    play = Game(world(KURAST_DOCKS, player=player(KURAST_DOCKS, x=5158.0, y=5068.0, **at)))
    play.thing = Thing(5, WAYPOINT_ACT3, 2, 5159.0, 5049.0)
    play.thing_above = 0.0  # a waypoint's picture lies on its ground point
    return play


def test_the_waypoint_in_view_is_clicked_and_done_with_its_panel_open():
    play = docks()

    open_panel(play.run())

    assert play.world.open_panels == ('waypoint',)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.said[-2:] == ['Opening the waypoint, 19 away', 'the waypoint: opened']


def test_a_waypoint_used_before_is_clicked_all_the_same():
    play = docks()
    assert play.thing is not None
    assert play.thing.mode  # activated: its mode is not 0, unlike a chest's that says "opened already"

    open_panel(play.run())

    assert play.world.open_panels == ('waypoint',)


def test_out_of_town_it_is_refused():
    play = Game(world(LOWER_KURAST))

    with pytest.raises(Abort, match='not in town'):
        open_panel(play.run())
    assert play.keys.events == []


def test_with_no_waypoint_shown_it_says_so():
    play = docks()
    play.thing = None

    with pytest.raises(Abort, match='no waypoint in sight'):
        open_panel(play.run())
    assert play.keys.events == []

