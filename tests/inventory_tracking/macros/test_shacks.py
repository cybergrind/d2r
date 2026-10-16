"""The shacks' other containers on the KP_6 loop's chest run (macros/shacks.py; routes/lower-kurast-loop-plan.md phase
6c). The camp of game 1, 2026-10-16 19:55 (take 20261016T165556Z-79): its corner at (4400, 2960), its chests at
(4427, 3012), (4412, 3017), (4460, 2972), the weapon rack at (4448, 2972), the armor stand at (4412, 2983)."""

from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.levels.model import UNIQUE_CHEST, Level, Room
from inventory_tracking.levels.presets import PRESET_NAMES
from inventory_tracking.macros.goals import USE
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.shacks import REACH, camps, shack_thing
from inventory_tracking.macros.world import Thing
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


def seen(_at) -> bool:
    return True


def test_only_the_bonfire_camps_layout_is_a_camp():
    assert camps(ROOMS + NEXT_DOOR) == (CAMP,)


def test_the_rack_by_the_chest_is_opened_and_the_chest_is_left_to_the_route():
    assert shack_thing((CHEST, RACK, STAND), ROOMS, BY_THE_CHEST, seen) == (RACK, 'Weapon rack')


def test_nothing_out_of_sight_out_of_reach_open_or_tried_is_opened():
    assert shack_thing((RACK,), ROOMS, BY_THE_CHEST, lambda at: False) is None
    assert shack_thing((STAND,), ROOMS, (STAND.x + REACH + 1.0, STAND.y), seen) is None  # just out of reach
    assert shack_thing((STAND,), ROOMS, (STAND.x + REACH - 1.0, STAND.y), seen) == (STAND, 'Armor stand')
    assert shack_thing((Thing(1, 107, 2, 4448.0, 2972.0, selectable=False),), ROOMS, BY_THE_CHEST, seen) is None
    assert shack_thing((RACK,), ROOMS, BY_THE_CHEST, seen, skip=frozenset({RACK.unit_id})) is None
    assert shack_thing((Thing(4, 7, 0, 4450.0, 2972.0),), ROOMS, BY_THE_CHEST, seen) is None  # a barrel: not asked for


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

    goal = hunt.shack_goal(run, world_now, world_now.player)

    assert goal is not None
    assert goal.do == USE
    assert goal.label == 'Weapon rack, in the shack'
    assert goal.unit == RACK.unit_id
    assert goal.stage is None  # no route stage: the route's progress is not told of it
    assert goal.mark is not None
    assert goal.mark.use == UNIQUE_CHEST  # opened as a camp's mark is: any container at the spot
    hunt.shack_tries[RACK.unit_id] = 2
    assert hunt.shack_goal(run, world_now, world_now.player) is None  # tried twice: left
