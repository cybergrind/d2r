"""The shacks' other containers on the KP_6 loop's chest run (macros/shacks.py; routes/lower-kurast-loop-plan.md phase
6c). The camp of game 1, 2026-10-16 19:55 (take 20261016T165556Z-79): its corner at (4400, 2960), its chests at
(4427, 3012), (4412, 3017), (4460, 2972), the weapon rack at (4448, 2972), the armor stand at (4412, 2983)."""

import math
from dataclasses import replace

from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.levels.model import UNIQUE_CHEST, Level, Room
from inventory_tracking.levels.presets import PRESET_NAMES
from inventory_tracking.macros.game.records import Thing
from inventory_tracking.macros.goals import USE
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.shacks import BY_CHEST, REACH, camps, shack_thing
from tests.inventory_tracking.macros.fakes import Game, player, world


LOWER_KURAST = 79
[CAMP_PRESET] = [preset for preset, name in PRESET_NAMES.items() if name == 'Act 3 - Slums 16x16']
CAMP = (880, 592, 16, 16)  # tiles: the camp's corner at (4400, 2960) units
ROOMS = tuple(
    Room(CAMP_PRESET, x, y, 8, 8, variant=1, block=CAMP) for x, y in ((880, 592), (888, 592), (880, 600), (888, 600))
)
NEXT_DOOR = (Room(CAMP_PRESET, 896, 592, 8, 8, variant=2, block=(896, 592, 8, 8)),)  # another Slums layout
BY_THE_CHEST = (4460.0, 2975.0)  # beside the camp's chest at (60, 12)
RACK = Thing(1, 107, 0, 4448.0, 2972.0)
STAND = Thing(2, 104, 0, 4412.0, 2983.0)
CHEST = Thing(3, 183, 0, 4460.0, 2972.0)  # the card's mark: the route's own


def seen(_from, _at) -> bool:
    return True


def test_only_the_bonfire_camps_layout_is_a_camp():
    assert camps(ROOMS + NEXT_DOOR) == (CAMP,)


def test_the_rack_by_the_chest_is_opened_and_the_chest_is_left_to_the_route():
    assert shack_thing((CHEST, RACK, STAND), ROOMS, BY_THE_CHEST, seen) == (RACK, 'Weapon rack')


def test_nothing_out_of_sight_out_of_reach_open_or_tried_is_opened():
    assert shack_thing((RACK,), ROOMS, BY_THE_CHEST, lambda origin, at: False) is None
    basket = Thing(6, 208, 0, 4427.0, 3000.0)  # 12 units from the chest at (27, 52)
    assert shack_thing((basket,), ROOMS, (basket.x + REACH + 1.0, basket.y), seen) is None  # just out of reach
    assert shack_thing((basket,), ROOMS, (basket.x + REACH - 1.0, basket.y), seen) == (basket, 'Basket')
    assert shack_thing((Thing(1, 107, 2, 4448.0, 2972.0, selectable=False),), ROOMS, BY_THE_CHEST, seen) is None
    assert shack_thing((RACK,), ROOMS, BY_THE_CHEST, seen, skip=frozenset({RACK.unit_id})) is None
    assert shack_thing((Thing(4, 7, 0, 4450.0, 2972.0),), ROOMS, BY_THE_CHEST, seen) is None  # a barrel: not asked for


def test_only_one_beside_a_chest_in_sight_of_it_is_opened():
    # The player, 2026-10-17: "interact only with interactables directly visible from superchests within small radius"
    assert shack_thing((STAND,), ROOMS, (STAND.x + 5.0, STAND.y), seen) is None  # 32 units from the nearest chest
    near = Thing(7, 209, 0, 4460.0, 2972.0 + BY_CHEST - 1.0)
    far = Thing(8, 209, 0, 4460.0, 2972.0 + BY_CHEST + 1.0)
    assert shack_thing((far,), ROOMS, BY_THE_CHEST, seen) is None
    assert shack_thing((near,), ROOMS, BY_THE_CHEST, seen) == (near, 'Basket')

    def behind_a_wall(origin, _at) -> bool:  # in sight of the character, not of the chest
        return origin != (CHEST.x, CHEST.y)

    assert shack_thing((near,), ROOMS, BY_THE_CHEST, behind_a_wall) is None


def test_none_is_hunted_from_outside_the_camp_nor_outside_it_from_within():
    # The player: "do not hunt them, only if we encounter them in shacks"
    outside = (4398.0, 2983.0)  # 14 units from the armor stand, out of the camp
    assert shack_thing((STAND,), ROOMS, outside, seen) is None
    beyond = Thing(5, 181, 0, 4482.0, 2972.0)  # 22 units from the chest, in the next preset
    assert shack_thing((beyond,), ROOMS + NEXT_DOOR, BY_THE_CHEST, seen) is None


def test_the_loops_run_goes_for_the_rack_in_sight_as_a_mark_of_its_own():
    play = Game(world(LOWER_KURAST, player=player(LOWER_KURAST, x=BY_THE_CHEST[0], y=BY_THE_CHEST[1])))
    play.thing = RACK
    hunt = Hunter(lambda: Level(LOWER_KURAST, ROOMS, ()), None, None, build=GENERIC)
    run = play.run()
    world_now = run.world()
    assert world_now.player is not None

    goal = hunt.shack_goal(run, world_now, world_now.player, 'Lower Kurast')

    assert goal is not None
    assert goal.do == USE
    assert goal.label == 'Weapon rack, in the shack'
    assert goal.unit == RACK.unit_id
    assert goal.stage is None  # no stage of its own: the route's progress is not told of it
    assert goal.route == 'Lower Kurast'  # a side goal of the level's route, as a drop on the way is
    assert goal.mark is not None
    assert goal.mark.use == UNIQUE_CHEST  # opened as a camp's mark is: any container at the spot
    hunt.shack_tries[RACK.unit_id] = 2
    assert hunt.shack_goal(run, world_now, world_now.player, 'Lower Kurast') is None  # tried twice: left


def test_the_loops_run_hops_beside_what_it_opens_and_opens_it_from_there():
    # Phase 6d (rca/2026-10-16/loop-chests-findings.md §3): from 18-23 units the game walked the character to the
    # chest (1.4 s, twice past the act's 1.5 s), and a hop aimed onto a chest's own spot was not cast.
    from inventory_tracking.builds import pursuing
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.hunt import Bearings
    from inventory_tracking.macros.hunting.base import OPEN_NEAR
    from inventory_tracking.macros.pursuit import FULL, Move, Operate, Pursuit
    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.macros.travel import LOOP_SHORT
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress
    from tests.inventory_tracking.macros.test_hunt import game

    play = game(area=LOWER_KURAST, player=player(LOWER_KURAST, x=BY_THE_CHEST[0], y=BY_THE_CHEST[1] + 6.0))
    play.thing = RACK  # 14.2 units off
    hunt = Hunter(lambda: Level(LOWER_KURAST, ROOMS, ()), None, None, build=pursuing(GENERIC))
    progress = Progress(ROUTES, PERFORMED)
    progress.note(play.world.game_name, LOWER_KURAST)
    progress.looted(LOWER_KURAST)  # past the chests: the rack in sight is still opened before the run ends
    hunt.bearings = Bearings(progress, lambda: None)
    run = play.run()
    hunt.post(Pursuit('pickup', play.clock.now, advance=False, leash=FULL, rush=True))
    play.clock.now += 5.0  # the run's own look, its press long past (pursuit.py FRESH)

    far = hunt.judge(run, play.world, [], Ground(()), in_reach=False)

    assert far.goal is not None
    assert far.goal.label == 'Weapon rack, in the shack'
    assert isinstance(far.act, Move)
    here = (BY_THE_CHEST[0], BY_THE_CHEST[1] + 6.0)
    # The way goes to the object's own place, which stays put as the character moves (a place beside it on the
    # character's side moved with it, and the walked way was grown afresh at every look: 22:50 on 2026-10-16); the
    # move ends LOOP_SHORT of it
    assert far.place == (RACK.x, RACK.y)
    assert far.goal.spend.short == LOOP_SHORT
    assert math.dist(far.act.step.spot, (RACK.x, RACK.y)) >= LOOP_SHORT - 0.5
    play.world = world(LOWER_KURAST, player=player(LOWER_KURAST, x=here[0] - 2.0, y=here[1] + 1.0))
    moved = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert moved.place == far.place

    play.world = world(LOWER_KURAST, player=player(LOWER_KURAST, x=RACK.x + OPEN_NEAR - 1.0, y=RACK.y))
    near = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert isinstance(near.act, Operate)

    # KP_1's own run: no shack goal (the loop's alone); the route's loot is what is left, which takes a press
    hunt.pursuit = None  # a run of its own, not a press during the loop's (`Hunter.post` keeps `rush` for that)
    hunt.post(Pursuit('pickup', play.clock.now, advance=False, leash=FULL))
    play.clock.now += 5.0
    play.world = world(LOWER_KURAST, player=player(LOWER_KURAST, x=here[0], y=here[1]))
    own = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert own.goal is None or own.goal.label != 'Weapon rack, in the shack'


def test_the_routes_chest_in_reach_comes_before_the_shacks_rack():
    # 19:45-20:08 on 2026-10-17: 9 of 27 stays landed within 4 of the chest and went to the rack first, then hopped
    # back (2.9 s from there to the chest opened; rca/2026-10-17/slow-legs-findings.md)
    from inventory_tracking.macros.goals import FIGHT, Goal
    from inventory_tracking.macros.travel import PRESSED

    play = Game(world(LOWER_KURAST, player=player(LOWER_KURAST, x=BY_THE_CHEST[0], y=BY_THE_CHEST[1])))
    hunt = Hunter(lambda: Level(LOWER_KURAST, ROOMS, ()), None, None, build=GENERIC)
    run = play.run()
    me = run.world().player
    assert me is not None
    chest = Goal('Super chests', (CHEST.x, CHEST.y), USE, 5.0, PRESSED, route='Lower Kurast')

    assert hunt.at_hand(chest, me, run.world())  # 3 units off on open ground: opened before the rack
    away = replace(me, x=CHEST.x + 20.0)
    assert not hunt.at_hand(chest, away, run.world())  # further than OPEN_NEAR: the rack in sight first, as before
    assert not hunt.at_hand(replace(chest, do=FIGHT), me, run.world())
    assert not hunt.at_hand(None, me, run.world())


def test_the_shacks_other_container_is_clicked_from_beside_the_one_opened():
    # The player, 21:50 on 2026-10-17: "we teleport into center of it and then go to weapon stand and travel back to
    # chest". From beside one, the other was 13-17 away and hopped to: 1.75 s first open to second (81 times), against
    # 0.72 s clicked and walked to (160)
    from inventory_tracking.macros.hunting.base import PAIR_NEAR, paired

    opened = replace(CHEST, mode=1)
    by_the_chest = (CHEST.x + 2.0, CHEST.y + 2.0)  # 14.1 from the rack
    assert paired((opened, RACK), RACK, by_the_chest)
    assert math.dist(by_the_chest, (RACK.x, RACK.y)) <= PAIR_NEAR
    assert not paired((CHEST, RACK), RACK, by_the_chest)  # the chest not opened yet: as before
    assert not paired((opened, RACK), RACK, (CHEST.x + 10.0, CHEST.y))  # not standing by it
    assert not paired((opened, STAND), STAND, by_the_chest)  # 48 units off: no shack's pair
