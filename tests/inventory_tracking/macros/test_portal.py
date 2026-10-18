"""Town Portal out of a level (routes/lower-kurast-loop-plan.md phase 3): the tome's key, the portal beside the
character once it is open, the click, the town."""

import pytest

from inventory_tracking.levels.model import TOWN_PORTAL
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.portal import TOME, to_town
from inventory_tracking.macros.world import Thing
from tests.inventory_tracking.macros.fakes import KEYS, PREBUFF_SET, Game, world


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

    assert play.pressed() == ['x', 'c', 'c']  # the tome; the arrival's check: a swap that takes, and back
    assert play.sets[0] == PREBUFF_SET  # the set held before (a game left with the staff in hand loses its key)
    assert play.character.area == KURAST_DOCKS
    clicks = [event for event in play.keys.events if event[0] == 'click']
    assert len(clicks) == 1  # not at the portal while it opened
    assert play.clock.now >= 0.6
    assert play.said[-4:] == ['Through the portal to town, 4 away', 'town: there', 'Swap Weapons', 'Swap Weapons']


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


def test_after_the_portal_the_leg_waits_for_the_town_to_come_up():
    # rca/2026-10-16/loop-first-game-findings.md §2: the waypoint's aims were tried 0.002 s after the portal's arrival
    play = lower_kurast()
    play.arrival_load = 1.2

    to_town(play.run(), keys)

    assert play.arrived_at is not None
    assert play.clock.now >= play.arrived_at + 1.2


def test_with_no_load_shown_the_leg_is_over_once_a_swap_takes_and_waits_the_settle_at_most():
    # The eight trips of 2026-10-16 19:55-20:04 showed no load by the view byte; game 1 took no input for 4.5 s
    from inventory_tracking.macros.routines import ARRIVAL_SETTLE

    play = lower_kurast()  # the view byte never shows a load
    play.arrival_deaf = 2.0

    to_town(play.run(), keys)

    assert play.arrived_at is not None
    assert play.arrived_at + 2.0 <= play.clock.now < play.arrived_at + ARRIVAL_SETTLE
    assert play.sets[0] == PREBUFF_SET

    deaf = lower_kurast()
    deaf.arrival_deaf = 60.0  # no input taken at all: the settle, and nothing more

    to_town(deaf.run(), keys)

    assert deaf.arrived_at is not None
    assert deaf.clock.now >= deaf.arrived_at + ARRIVAL_SETTLE


def test_what_lands_while_the_portal_opens_is_picked_up_before_it_is_gone_through():
    # 03:04:16-17 on 2026-10-18: a chest's Chipped Ruby landed 0.8 s after its click, while the portal opened, and the
    # character went through without it
    play = lower_kurast()
    play.portal_opens = 0.6
    asked: list[tuple[float, int]] = []

    def first() -> bool:
        clicks = sum(event[0] == 'click' for event in play.keys.events)
        asked.append((play.clock.now, clicks))
        return len(asked) < 2  # one drop picked up, then nothing more

    to_town(play.run(), keys, first)

    assert len(asked) == 2
    assert all(now >= 0.6 and clicks == 0 for now, clicks in asked)  # the portal open, not yet clicked
    assert play.character.area == KURAST_DOCKS


def test_a_portal_whose_middle_is_covered_is_taken_by_its_top():
    # 05:25:08 on 2026-10-18: a Doom Ape killed on the portal lay under the three aims down its middle, and the game was
    # left for it (teleport.py PORTAL_AIMS)
    play = lower_kurast()
    play.portal_opens = 0.6
    play.thing_above = 110  # only the portal's top is under the pointer: its middle shows the body

    to_town(play.run(), keys)

    assert play.character.area == KURAST_DOCKS
