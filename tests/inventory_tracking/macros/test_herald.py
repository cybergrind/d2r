"""A Herald's coming in a full clear (macros/hunt.py HERALD_OMEN, rca/2026-10-17/herald-findings.md): the missile the
client holds 5 s where the Herald appears keeps the run there, and a live Herald is its first goal."""

import math

from inventory_tracking.macros.hunt import HERALD_OMEN, OMEN_SECONDS, OMEN_STAND, omen_stand
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
    from inventory_tracking.macros.world import VALUABLE, Drop, Loot

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
