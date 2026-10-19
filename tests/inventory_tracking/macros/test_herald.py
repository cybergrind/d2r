"""A Herald's coming in a full clear (macros/hunt.py HERALD_OMEN, rca/2026-10-17/herald-findings.md): the missile the
client holds 5 s where the Herald appears keeps the run there, and a live Herald is its first goal."""

import math

import pytest

from inventory_tracking.macros.hunt import HERALD_OMEN, OMEN_SECONDS
from inventory_tracking.macros.hunting.base import OMEN_STAND, omen_stand
from tests.inventory_tracking.macros.fakes import patch_hunt
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter, me


UNIQUE, MINION = 0x08, 0x10


def setup():
    play = game(area=4)  # Stony Field, a Terror Zone of 2026-10-17
    hunt, run = hunter(play), play.run()
    run.flights = lambda kinds: ()
    return play, hunt, run, (me(play.world).x, me(play.world).y)


def goal(hunt, run, play, foes, here):
    found = hunt.rest_of(run, play.world, foes, here)
    assert found is not None
    return found


def test_a_herald_coming_keeps_the_run_by_its_spot_and_a_monster_far_from_it_is_not_gone_for():
    # Take 20261017T201752Z-5: the second Herald's 5 s went to a monster 65 units off (the player: "we just teleporting
    # out of heralds vicinity hunting for another enemies")
    play, hunt, run, here = setup()
    spot = (here[0] + 100.0, here[1])
    run.flights = lambda kinds: ((0, HERALD_OMEN, *spot),) if HERALD_OMEN in kinds else ()
    away = foe(1, here[0] - 10.0, here[1])  # the nearest, on the other side
    place, what, unit = goal(hunt, run, play, [away], here)
    assert (what, unit) == ('the stand for the Herald coming', None)
    assert math.isclose(math.dist(place, spot), OMEN_STAND)
    by_it = foe(2, spot[0] + 10.0, spot[1] + 5.0)  # within OMEN_NEAR of the spot: fought while it is pending
    assert goal(hunt, run, play, [away, by_it], here)[2] == 2
    # Its time over and no Herald seen: the run goes on as before
    run.flights = lambda kinds: ()
    play.clock.now += OMEN_SECONDS + 0.5
    assert goal(hunt, run, play, [away], here)[2] == 1


def test_a_live_herald_is_the_first_goal_and_a_boss_never_left_alone():
    play, hunt, run, here = setup()
    near = foe(1, here[0] + 5.0, here[1])
    minion = foe(2, here[0] + 8.0, here[1], flags=MINION, tier=5)
    herald = foe(3, here[0] + 40.0, here[1], flags=UNIQUE, tier=5)
    assert goal(hunt, run, play, [near, minion, herald], here)[2] == 3
    assert hunt.boss(herald)
    assert not hunt.boss(minion)
    assert not hunt.boss(foe(4, 0.0, 0.0, flags=UNIQUE))  # a unique of no Herald's


def test_the_stand_is_on_the_characters_side_and_kept_when_near_enough():
    spot = (100.0, 0.0)
    assert omen_stand(spot, (0.0, 0.0)) == (100.0 - OMEN_STAND, 0.0)
    assert omen_stand(spot, (100.0 - OMEN_STAND - 3.0, 0.0)) == (100.0 - OMEN_STAND - 3.0, 0.0)  # no move for 3
    assert math.isclose(math.dist(omen_stand(spot, (101.0, 1.0)), spot), OMEN_STAND)  # on the spot: steps out


# -- a full inventory with room in the cube (the player, 23:55 on 2026-10-17: "if we have cube space - we should move
# items there") --


def test_a_valuable_with_no_room_has_the_macros_pickups_moved_into_the_cube_in_the_quiet_once():
    from inventory_tracking.macros.game.records import VALUABLE, Drop, Loot

    _, hunt, run, here = setup()
    amulet = Drop(9, here[0] + 3.0, here[1], 'Amulet', VALUABLE, size=(1, 1))
    full, roomy = ('#' * 10,) * 4, ('...',) * 4
    run.loot = lambda: Loot(drops=(amulet,), room=full, cube=roomy)
    moved = []
    hunt.room_maker = lambda run: moved.append(run) or 2
    near = foe(1, here[0] + 10.0, here[1])
    assert hunt.stay_by(run, here, foes=[near]) == amulet  # a hostile within reach: not now, the run stands by it
    assert not moved
    assert hunt.stay_by(run, here, foes=[]) is None  # the quiet: room made, the next look takes it
    assert len(moved) == 1
    hunt.room_maker = lambda run: 0  # nothing of the macro's to move: the run stands by it for the player
    hunt.room_tried = None
    assert hunt.stay_by(run, here) == amulet
    run.loot = lambda: Loot(drops=(amulet,), room=full, cube=('###',) * 4)  # no room in the cube either
    hunt.room_tried, hunt.room_maker = None, lambda run: moved.append(run) or 2
    assert hunt.stay_by(run, here) == amulet
    assert len(moved) == 1


def test_an_unread_cube_gets_one_room_making_attempt_before_standing_by_a_valuable():
    from inventory_tracking.macros.game.records import VALUABLE, Drop, Loot

    _, hunt, run, here = setup()
    tal = Drop(9, here[0] + 1.0, here[1], 'Tal Rune', VALUABLE)
    run.loot = lambda: Loot(drops=(tal,), room=('#' * 10,) * 4, cube=None)
    moved = []
    hunt.room_maker = lambda playing: moved.append(playing) or 1
    assert hunt.stay_by(run, here) is None
    assert moved == [run]
    assert hunt.room_tried == tal.unit_id


# -- a full clear's super chests (the player, 00:19 on 2026-10-18: "in auto mode - we should open at least glowing
# superchests") --


def test_a_closed_super_chest_near_is_the_full_clears_goal_before_the_rest_and_a_herald_before_it():
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.game.records import Thing
    from inventory_tracking.macros.goals import USE
    from inventory_tracking.macros.hunting.base import SUPER_NEAR, SUPER_TRIES
    from inventory_tracking.macros.runmode import SWITCHED, Mode

    play, hunt, run, here = setup()
    hunt.mode = Mode(True, SWITCHED)
    chest = Thing(70, 397, 0, here[0] + 30.0, here[1])
    run.things = lambda: (chest, Thing(71, 397, 1, here[0] + 5.0, here[1]))  # the open one is no goal
    far = foe(1, here[0] - 40.0, here[1])  # off the way: the chest first
    goal = hunt.cleared(run, play.world, [far], Ground(()), None)
    assert goal is not None
    assert (goal.do, goal.unit, goal.place) == (USE, 70, (chest.x, chest.y))
    run.things = lambda: (Thing(70, 397, 0, here[0] + SUPER_NEAR + 5.0, here[1]),)  # too far: the rest of the level
    assert getattr(hunt.cleared(run, play.world, [far], Ground(()), None), 'unit', None) == 1
    run.things = lambda: (chest,)
    herald = foe(2, here[0] - 40.0, here[1], flags=UNIQUE, tier=5)
    assert getattr(hunt.cleared(run, play.world, [herald], Ground(()), None), 'unit', None) == 2  # a Herald first
    hunt.shack_tries[70] = SUPER_TRIES  # tried enough: left
    assert getattr(hunt.cleared(run, play.world, [far], Ground(()), None), 'unit', None) == 1


def test_a_route_chest_no_try_opens_is_left_as_gone_after_route_use_tries(monkeypatch):
    # 01:37:56-01:38:42 on 2026-10-18: another object under the pointer at every aim at Lower Kurast's chest, 46 tries
    # in 47 s, until the loop's watchdog left the game
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros import route
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.game.records import Thing
    from inventory_tracking.macros.goals import USE, Goal
    from inventory_tracking.macros.hunting.base import ROUTE_USE_TRIES
    from inventory_tracking.macros.travel import LOOPED
    from inventory_tracking.routes.model import Stage

    play, hunt, run, here = setup()
    chest = Thing(70, 183, 0, here[0] + 3.0, here[1])
    mark = Target(79, (), (chest.x / 5, chest.y / 5), 'Super chests', 'target', use=183)
    goal = Goal(
        'Super chests', (chest.x, chest.y), USE, 3.0, LOOPED, unit=70, mark=mark, stage=Stage(USE, 'Super chests')
    )
    tried, left = [], []
    patch_hunt(monkeypatch, 'marked_thing', lambda run, target: chest)

    def refused(*_args):
        tried.append(True)
        raise Abort('Super chests is not under the pointer at any aim')

    patch_hunt(monkeypatch, 'use_thing', refused)
    monkeypatch.setattr(route, 'note_empty', lambda *args: left.append(args[-1]) or True)
    for _ in range(ROUTE_USE_TRIES):
        with pytest.raises(Abort):
            hunt.operate(run, play.world, goal, None)
    assert len(tried) == ROUTE_USE_TRIES
    hunt.operate(run, play.world, goal, None)  # one more: left as gone, no click
    assert len(tried) == ROUTE_USE_TRIES
    assert left == [f'not opened in {ROUTE_USE_TRIES} tries']
