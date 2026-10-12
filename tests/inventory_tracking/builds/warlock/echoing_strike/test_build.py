"""The Echoing Strike Warlock as a build (builds/warlock/echoing_strike/build.py): whose it is, what it holds so far."""

from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.casters import CASTERS
from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.movement import MOVEMENT
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.skills import ATTACK, TELEPORT
from tests.inventory_tracking.builds.dummy import DUMMY
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, world


def test_it_is_for_a_character_with_the_strike_on_a_key_or_a_mouse_button():
    applies = ECHOING_STRIKE_BUILD.applies
    assert applies(world(slots=HUNT_SLOTS))
    off_keys = world(slots=(TELEPORT, None))
    assert not applies(off_keys)
    assert off_keys.player is not None
    assert applies(replace(off_keys, player=replace(off_keys.player, right_skill=ECHOING_STRIKE)))
    assert applies(replace(off_keys, player=replace(off_keys.player, left_skill=ECHOING_STRIKE)))
    assert not applies(replace(off_keys, player=replace(off_keys.player, left_skill=ATTACK, name='CybergrindAA')))
    assert not applies(replace(world(slots=HUNT_SLOTS), player=None))  # a loading screen: nobody's


def test_it_moves_by_the_warlocks_sets_and_fights_by_echoing_strike():
    assert ECHOING_STRIKE_BUILD.movement == MOVEMENT
    assert ECHOING_STRIKE_BUILD.attack is ECHOING_STRIKE_ATTACK


def test_it_holds_the_warlocks_buff_plan_and_casters():
    assert ECHOING_STRIKE_BUILD.buffs == BUFFS
    assert ECHOING_STRIKE_BUILD.casters == CASTERS


def test_the_hunt_plays_the_build_it_is_made_with():
    hunter = Hunter(build=ECHOING_STRIKE_BUILD)
    assert hunter.build is ECHOING_STRIKE_BUILD
    assert hunter.travel.sets == MOVEMENT
    other = Hunter(build=DUMMY)
    assert other.build is DUMMY
    assert other.travel.sets == DUMMY.movement
