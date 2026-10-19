"""The pursuit's pure parts (rca/2026-10-13/pursuit-v1.md): the goal a key means (macros/goals.py), the one
decision per look (macros/pursuit.py), and the movement sets answering for a goal at any distance by their
own means (macros/movement.py `Ways.routed`, macros/travel.py `Walked`, `way_leg`, `Travel.toward`).

The ground of the navigation tests is a walled pocket, the shape of 13:05 on 2026-10-13: the character in a
pocket open to the east, the goal behind its west wall. The way of hops crosses the wall; the walked way
leads out of the mouth and round.
"""

import ast
import inspect
import math
import re
import textwrap
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pytest

from inventory_tracking.combat.stance import Jump, no_footing
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import VALUABLE, Drop, Monster, Teleport
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground, Room, Target, Walkable, pack_cells
from inventory_tracking.macros import goals, movement, pickup, route, teleport, travel
from inventory_tracking.macros.build import BuildSettings, Intent, JumpSource, MoveFacts, NoWay, Step
from inventory_tracking.macros.goals import PICK_UP, PURSUED, REACH, Goal, goal_of
from inventory_tracking.macros.hunting import base as hunt_base
from inventory_tracking.macros.pursuit import FRESH, Defer, Facts, Hold, Move, Operate, Pursuit, Told, decide
from inventory_tracking.macros.runner import EXPIRES, TELEPORT as TELEPORT_KEY
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED, STANDING, Travel, Walked, navigator, way_leg
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, enter, fight, leave, loot, stand, use
from inventory_tracking.terror.bosses import SUPER_UNIQUE_FLAG


ROOT = Path(__file__).resolve().parents[3]
REACH_UNITS = 22.0  # a build's strike reach, for the goals
AREA = 108


# -- goals ----------------------------------------------------------------------------------------------


def card(label: str, tile: Point, *, use_: int = 0, warp: bool = False, kind: str = 'target') -> Target:
    return Target(AREA, (), tile, label, kind, warp, (), use_)


def monster(unit: int, at: Point, flags: int = 0, txt: int = 306) -> Monster:
    return Monster(unit, txt, 1, at[0], at[1], NO_OWNER, flags)


def named(here: Point = (0.0, 0.0), **given) -> Goal | None:
    return goal_of(here, spend=PRESSED, reach=REACH_UNITS, **given)


def goal_named(here: Point = (0.0, 0.0), **given) -> Goal:
    """The goal named where the test expects one."""
    found = named(here, **given)
    assert found is not None
    return found


def test_the_goals_distances_are_the_hands_own() -> None:
    assert goals.USE_NEAR == teleport.THING_REACH
    assert goals.STAND_NEAR == route.STAND_NEAR
    assert goals.PLACE_NEAR == teleport.SPOT_NEAR
    assert goals.PICK_NEAR == pickup.STOP_UNITS
    assert goals.PICK_REACH == pickup.PICK_UNITS  # a level run's drop is clicked from within the pickup's own reach
    assert goals.GUARD_NEAR == hunt_base.GATHER_CLEAR  # a potion's guards are the pickup key's own measure
    assert goals.BOSS_MARK_UNITS == hunt_base.BOSS_MARK_UNITS


def test_a_use_stage_is_the_object_on_the_stages_mark_within_a_clicks_reach() -> None:
    seal = card('Vizier seal 1', (10.0, 20.0), use_=396)
    found = named(stage=use('Vizier seal 1'), route='Diablo', card=seal)
    assert found is not None
    assert (found.do, found.place, found.near, found.label) == (USE, (50.0, 100.0), goals.USE_NEAR, 'Vizier seal 1')
    assert found.mark is seal
    assert found.spend is PRESSED


def test_a_stand_and_a_way_on_are_their_marks() -> None:
    assert goal_named(stage=stand('the altar'), card=card('the altar', (2.0, 2.0))).do == STAND
    door = goal_named(stage=enter('River of Flame', 107), card=card('River of Flame', (2.0, 2.0), warp=True))
    assert door.do == ENTER
    assert door.do not in PURSUED


def test_a_fight_with_no_mark_is_the_boss_where_it_stands() -> None:
    boss = monster(7, (60.0, 0.0), SUPER_UNIQUE_FLAG | 0x08)
    pack = [monster(8, (20.0, 0.0), 0x10), monster(9, (25.0, 0.0), 0x08)]  # a minion, a plain unique
    found = goal_named(stage=fight('Grand Vizier of Chaos'), foes=[*pack, boss])
    assert (found.do, found.place, found.unit, found.near) == (FIGHT, (60.0, 0.0), 7, REACH_UNITS)
    assert found.known
    assert found.label == 'Grand Vizier of Chaos'


def test_a_boss_out_of_sight_is_where_one_was_last_seen_alive() -> None:
    # The tracker holds every super unique's last place, the dead ones too; alive are the remembered ones.
    remembered = [(7, 300.0, 0.0, True), (8, 100.0, 0.0, True), (9, 50.0, 0.0, False)]
    supers = [(300.0, 0.0), (40.0, 40.0)]  # the boss alive at 300, a boss dead at (40, 40); 8 is a plain unique
    found = goal_named(stage=fight('Lord De Seis'), remembered=remembered, supers=supers)
    assert (found.place, found.unit, found.known) == ((300.0, 0.0), None, True)
    assert 'last seen' in found.label
    assert named(stage=fight('Lord De Seis'), remembered=remembered, supers=supers, gone=frozenset({7})) is None


def test_a_fight_with_a_mark_is_the_boss_by_it_else_the_mark() -> None:
    mark = card('Diablo', (20.0, 20.0))
    stage = fight('Diablo', 'Diablo')
    far = monster(7, (400.0, 400.0), SUPER_UNIQUE_FLAG)  # a super unique that is not this mark's
    near = monster(8, (120.0, 110.0), 0, txt=243)  # the act boss, by its type
    assert goal_named(stage=stage, card=mark, foes=[far]).place == (100.0, 100.0)
    found = goal_named(stage=stage, card=mark, foes=[far, near])
    assert (found.unit, found.place) == (8, (120.0, 110.0))


def test_a_boss_nothing_is_known_of_is_sought_and_the_label_says_so() -> None:
    found = goal_named(stage=fight('Infector of Souls'), elsewhere=lambda: ((70.0, 0.0), 'an unexplored room'))
    assert (found.do, found.place, found.known) == (FIGHT, (70.0, 0.0), False)
    assert found.label == 'seek Infector of Souls: toward an unexplored room'
    assert named(stage=fight('Infector of Souls'), elsewhere=lambda: None) is None
    assert named(stage=fight('Infector of Souls')) is None


def test_elsewhere_is_asked_only_when_nothing_is_known() -> None:
    def never():
        raise AssertionError('asked')

    assert goal_named(stage=fight('x'), foes=[monster(7, (9.0, 9.0), SUPER_UNIQUE_FLAG)], elsewhere=never).unit == 7


def test_a_valuable_beside_the_character_comes_before_the_routes_goal() -> None:
    drop = Drop(55, 4.0, 3.0, 'Ring', VALUABLE)
    found = goal_named(stage=use('Vizier seal 1'), card=card('Vizier seal 1', (10.0, 20.0), use_=396), drop=drop)
    assert (found.do, found.place, found.unit) == (PICK_UP, (4.0, 3.0), 55)
    assert 'Ring' in found.label


def test_without_a_stage_the_goal_is_the_cards_first_mark() -> None:
    assert goal_named(card=card('a room', (4.0, 4.0), kind='explore')).do == REACH
    assert goal_named(card=card('the chest', (4.0, 4.0), use_=5)).do == USE
    assert goal_named(card=card('the stairs', (4.0, 4.0), warp=True)).do == ENTER
    assert named() is None


def test_a_doors_remembered_entry_is_where_the_way_to_it_ends() -> None:
    # The Catacombs stairs: a run ended at the mark's far side walked round its block of walls, or hopped onto the
    # entry first (rca/2026-10-18/stairs-walks-findings.md §5 B)
    from inventory_tracking.macros.goals import ENTRY_GOAL_NEAR, PLACE_NEAR

    stairs = card('the stairs', (4.0, 4.0), warp=True)
    plain = goal_named(card=stairs)
    assert (plain.place, plain.near) == ((4.0 * TILE_UNITS, 4.0 * TILE_UNITS), PLACE_NEAR)
    door = goal_named(card=stairs, entry=(18.0, 22.0))
    assert (door.place, door.near, door.do) == ((18.0, 22.0), ENTRY_GOAL_NEAR, ENTER)


def test_the_way_to_a_doors_entry_ends_on_it_not_the_loops_short_of_it() -> None:
    # 13:00-13:10 on 2026-10-18: the loop's goals end LOOP_SHORT 3 short (a chest's own spot); the runs to the Catacombs
    # stairs ended 2.2-3.0 off the entry, east of the block of walls, and the click walked round it
    from inventory_tracking.macros.travel import LOOP_SHORT, LOOPED_TELEPORT

    stairs = card('the stairs', (4.0, 4.0), warp=True)
    door = goal_of((0.0, 0.0), spend=LOOPED_TELEPORT, reach=REACH_UNITS, card=stairs, entry=(18.0, 22.0))
    assert door is not None
    assert door.spend == replace(LOOPED_TELEPORT, short=0.0)
    plain = goal_of((0.0, 0.0), spend=LOOPED_TELEPORT, reach=REACH_UNITS, card=stairs)
    assert plain is not None
    assert plain.spend.short == LOOP_SHORT  # no entry known: the mark, as before


def test_a_stage_whose_mark_the_card_does_not_hold_follows_the_card_and_says_so() -> None:
    found = goal_named(stage=use('Vizier seal 1'), card=card('Diablo', (4.0, 4.0)))
    assert (found.do, found.place) == (REACH, (20.0, 20.0))
    assert 'Vizier seal 1 is not marked yet' in found.label


def test_the_loot_and_the_leaving_are_the_routes_own_step() -> None:
    for stage in (loot(), leave()):
        found = goal_named(stage=stage, card=card('Diablo', (4.0, 4.0)))
        assert found.do in (LOOT, LEAVE)
        assert found.do not in PURSUED


# -- the split, kept by a test ("NO HARDCODE") ------------------------------------------------------------


def identifiers(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for part in ast.walk(node):
        if isinstance(part, ast.Name):
            found.add(part.id)
        elif isinstance(part, ast.Attribute):
            found.add(part.attr)
        elif isinstance(part, ast.arg):
            found.add(part.arg)
        elif isinstance(part, ast.FunctionDef | ast.ClassDef):
            found.add(part.name)
    return found


def imported(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    }


# (`warp` is not among them: on the level card it is a door's tile, `Target.warp`, which a goal reads.)
HOW = re.compile(r'wall|staff|blade|hop|landing|charge|jump|stride|teleport', re.IGNORECASE)
WHAT = re.compile(r'(^|_)(route|stage|mark|seal|boss|progress|card)(s|es)?($|_)', re.IGNORECASE)


@pytest.mark.parametrize('module', ['goals', 'pursuit'])
def test_the_goal_layer_names_no_way_to_move(module) -> None:
    """Goals and the decision say what, never how: no name of theirs is of a wall, the staff, a hop or a
    landing, and they import nothing of the navigation (the contracts of build.py only)."""
    path = ROOT / 'inventory_tracking' / 'macros' / f'{module}.py'
    names = identifiers(ast.parse(path.read_text(encoding='utf-8')))
    assert not sorted(name for name in names if HOW.search(name))
    navigation = ('macros.travel', 'macros.movement', 'macros.teleport', 'macros.sight', 'combat.stance')
    assert not [found for found in imported(path) if found.endswith(navigation)]


def test_the_navigation_names_no_route() -> None:
    """The sets' answer for a far goal and the walked way know of no route, stage, mark, seal or boss."""
    parts = [
        travel.Walked, travel.walked_over, travel.walked_for, travel.way_left, travel.way_leg, travel.Travel.asked,
        travel.Travel.toward, travel.Travel.eta, travel.Travel.pause, movement.hops, movement.hop_way,
        movement.hops_left, movement.hop_leg, movement.Ways.routed, movement.Ways.left, movement.Ways.pace,
        movement.Ways.routed_wait, movement.Ways.spare,
    ]  # fmt: skip
    for part in parts:
        names = identifiers(ast.parse(textwrap.dedent(inspect.getsource(part))))
        assert not sorted(name for name in names if WHAT.search(name)), part
    for module in ('travel', 'movement'):
        found = imported(ROOT / 'inventory_tracking' / 'macros' / f'{module}.py')
        assert not [name for name in found if '.routes' in name or name.endswith(('.goals', '.pursuit', '.route'))]


# -- the decision ---------------------------------------------------------------------------------------


SEAL = Goal('Vizier seal 1', (50.0, 0.0), USE, goals.USE_NEAR, PRESSED)
BOSS = Goal('Grand Vizier of Chaos', (50.0, 0.0), FIGHT, REACH_UNITS, PRESSED, unit=7)
STEP = Step((20.0, 0.0), 5)
PRESS = Pursuit(TELEPORT_KEY, 10.0)


def unasked():
    raise AssertionError('the navigator was asked')


def facts(goal: Goal | None, *, now=10.2, there=False, in_reach=False, attacking=True, way=lambda: STEP) -> Facts:
    return Facts(now, goal, there, in_reach, attacking, way)


def test_a_press_is_fresh_for_the_longest_gap_of_a_travelling_player_and_under_the_requests_limit() -> None:
    assert PRESS.fresh(10.0)
    assert PRESS.fresh(10.0 + FRESH)
    assert not PRESS.fresh(10.0 + FRESH + 0.01)
    assert not PRESS.fresh(9.9)  # a clock that went back keeps nothing alive
    assert 0.6 < FRESH <= EXPIRES[TELEPORT_KEY]  # no move is begun for a press older than a request lives


def test_a_fresh_press_whose_goal_is_not_near_moves_even_with_hostiles_in_reach() -> None:
    for in_reach in (False, True):
        assert decide(facts(SEAL, in_reach=in_reach), PRESS) == Move(STEP, SEAL)


def test_a_fresh_press_at_its_goal_operates_it_or_holds_the_fight() -> None:
    assert decide(facts(SEAL, there=True, way=unasked), PRESS) == Operate(SEAL)
    assert decide(facts(BOSS, there=True, in_reach=True, way=unasked), PRESS) == Hold(BOSS)


def test_a_fight_in_reach_with_attack_mode_off_is_said_and_not_struck() -> None:
    found = decide(facts(BOSS, there=True, in_reach=True, attacking=False, way=unasked), PRESS)
    assert isinstance(found, NoWay)
    assert found.arrived
    assert 'attack mode is off' in found.reason


def test_a_goal_the_routes_step_performs_is_deferred_to_it() -> None:
    door = Goal('River of Flame', (50.0, 0.0), ENTER, 5.0, PRESSED)
    assert decide(facts(door, there=True, way=unasked), PRESS) == Defer(door)
    assert isinstance(decide(facts(door, in_reach=True, now=20.0, way=unasked), PRESS), Hold)  # the press is old
    loot = Goal('the loot', (50.0, 0.0), LOOT, 5.0, PRESSED)
    assert decide(facts(loot, way=unasked), PRESS) == Defer(loot)


def test_a_press_for_a_door_goes_by_the_navigator_and_the_step_takes_it_at_the_door() -> None:
    """rca/2026-10-14/run-1932-findings.md §1.2.2: a press for the Icy Cellar's door 43 units off was handed to the
    old step, which with the staff empty walked toward a Teleport landing into a pocket 276 units from the door by
    the walked way. The press is a goal: the way there is the navigator's (the class in hand); at the door, or where
    the navigator has no move left or none at all, the route's own step takes the press for the click."""
    door = Goal('Icy Cellar', (50.0, 0.0), ENTER, 5.0, PRESSED)
    assert decide(facts(door), PRESS) == Move(STEP, door)
    assert decide(facts(door, there=True, way=unasked), PRESS) == Defer(door)
    assert decide(facts(door, way=lambda: NoWay('there', arrived=True)), PRESS) == Defer(door)
    assert decide(facts(door, way=lambda: NoWay('no walked way')), PRESS) == Defer(door)


def test_a_drop_is_taken_at_once_by_the_hands_that_walk_to_it() -> None:
    drop = Goal('Ring, before leaving', (30.0, 0.0), PICK_UP, goals.PICK_NEAR, PRESSED)
    assert decide(facts(drop, way=unasked), PRESS) == Operate(drop)


def test_a_fresh_press_with_nothing_to_go_to_says_so() -> None:
    assert isinstance(decide(facts(None, way=unasked), PRESS), NoWay)


def test_without_a_fresh_press_what_is_in_reach_is_held() -> None:
    for posted in (None, PRESS):
        assert decide(facts(BOSS, now=20.0, in_reach=True, way=unasked), posted) == Hold(BOSS)
        assert decide(facts(None, now=20.0, in_reach=True, way=unasked), posted) == Hold(None)


def test_attack_mode_alone_goes_to_a_boss_out_of_reach_whose_place_is_known() -> None:
    assert decide(facts(BOSS, now=20.0), None) == Move(STEP, BOSS)
    sought = replace(BOSS, known=False, unit=None)
    assert isinstance(decide(facts(sought, now=20.0, way=unasked), None), NoWay)
    assert isinstance(decide(facts(SEAL, now=20.0, way=unasked), None), NoWay)  # a seal is gone to by the key only
    assert isinstance(decide(facts(BOSS, now=20.0, attacking=False, way=unasked), None), NoWay)


def test_no_way_is_the_navigators_reason_with_the_goals_name() -> None:
    found = decide(facts(SEAL, way=lambda: NoWay('a wall')), PRESS)
    assert isinstance(found, NoWay)
    assert not found.arrived
    assert found.reason == 'no way toward Vizier seal 1: a wall'


def test_the_navigators_arrival_is_what_is_done_at_the_goal() -> None:
    def there() -> NoWay:
        return NoWay('there', arrived=True)

    assert decide(facts(SEAL, way=there), PRESS) == Operate(SEAL)
    assert decide(facts(BOSS, in_reach=True, way=there), PRESS) == Hold(BOSS)
    blind = decide(facts(BOSS, way=there), PRESS)
    assert isinstance(blind, NoWay)
    assert blind.arrived


def test_with_the_switch_off_the_decision_is_the_old_loops() -> None:
    assert BuildSettings().pursuit is False
    assert decide(facts(SEAL, in_reach=True, way=unasked), PRESS, enabled=False) == Hold()
    assert isinstance(decide(facts(BOSS, now=20.0, way=unasked), None, enabled=False), NoWay)


def test_a_reason_is_new_once_per_change() -> None:
    told = Told()
    assert [told.new(reason) for reason in ('a', 'a', 'b', None, None, 'b', 'b')] == [
        True, False, True, False, False, True, False,
    ]  # fmt: skip


# -- navigation: the sets answer for the goal by their own means ----------------------------------------


SIDE = 20  # tiles: the ground is 100 by 100 units from (ORIGIN, ORIGIN)
ORIGIN = 1000 * TILE_UNITS
SPARE = 999  # a jump that costs no charge and needs a clear line (a thrown one), of a made-up skill
SPARE_JUMP = Jump(SPARE, 0.35, 45.0, travel.JUMP_REACH, travel.JUMP_LEAST, line=True)
SPARE_SOURCE = JumpSource(SPARE_JUMP, delay=1.0)
SETS = tuple(shared.led_by(SPARE_SOURCE) for shared in movement.SHARED)
IN_POCKET, BEHIND = (ORIGIN + 50.5, ORIGIN + 50.5), (ORIGIN + 20.5, ORIGIN + 50.5)


def pocket() -> tuple[Ground, tuple[Room, ...]]:
    """Open ground with a pocket in its middle, open to the east: walls 2 units thick on its north, west
    and south (x 40 to 70, y 35 to 65). `IN_POCKET` is inside, `BEHIND` 30 units west, beyond the wall."""
    units = SIDE * TILE_UNITS
    rows = []
    for y in range(units):
        row = ['1'] * units
        for x in range(units):
            north, south = 35 <= y < 37, 63 <= y < 65
            west = 40 <= x < 42 and 35 <= y < 65
            if ((north or south) and 40 <= x < 70) or west:
                row[x] = '0'
        rows.append(''.join(row))
    cells = pack_cells(''.join(rows))
    grids = (Walkable(1000, 1000, SIDE, SIDE, cells, cells),)
    return Ground(grids), (Room(0, 1000, 1000, SIDE, SIDE),)


def standing(
    here: Point, *, charges: int | None, in_hand: bool = False, slots: tuple[int, ...] = (SPARE, TELEPORT), now=100.0
) -> MoveFacts:
    ground, rooms = pocket()
    staff = None if charges is None else Teleport(charges, 69, in_hand)
    return MoveFacts(here, now, slots, staff, ground, (), 16 / 9, area=AREA, rooms=rooms)


def ways(found: MoveFacts) -> movement.Ways:
    """The set the navigator gives for `found`: one of the shared sets, which also measure what is left."""
    movement_ = navigator(SETS, found)
    assert isinstance(movement_, movement.Ways)
    return movement_


def walk_it(found: MoveFacts, goal: Point, intent: Intent, most: int = 40) -> list[tuple[Point, int | None, float]]:
    """The moves the set gives from `found` to the goal, each made as it is given: (from, by, eta before)."""
    made = []
    for _ in range(most):
        movement_ = ways(found)
        leg = movement_.leg(found, goal, intent)
        if isinstance(leg, NoWay):
            assert leg.arrived, leg.reason
            return made
        made.append((found.here, leg.skill, movement_.eta(found, goal, intent)))
        staff = found.staff
        if leg.skill == TELEPORT and staff is not None:
            staff = replace(staff, charges=staff.charges - 1, in_hand=True)
        found = replace(found, here=leg.spot, now=found.now + 2.0, staff=staff)
    raise AssertionError(f'not at the goal after {most} moves')


def test_the_way_of_hops_and_the_walked_way_disagree_in_the_pocket() -> None:
    ground, _ = pocket()
    barred = no_footing(ground, ())
    assert barred is not None
    field = Walked(barred, BEHIND)
    assert math.dist(IN_POCKET, BEHIND) == 30.0
    assert field.left(IN_POCKET) > 80.0  # out of the mouth and round
    assert field.left((ORIGIN + 75.5, ORIGIN + 50.5)) < field.left(IN_POCKET)  # the mouth is nearer on foot
    assert movement.hops_left(standing(IN_POCKET, charges=30), BEHIND) < 40.0


def test_with_charges_the_set_hops_across_the_wall() -> None:
    made = walk_it(standing(IN_POCKET, charges=30), BEHIND, PRESSED)
    assert [by for _, by, _ in made] == [TELEPORT] * len(made)
    assert len(made) <= 2


def test_with_the_staff_empty_the_set_goes_by_the_walked_way_out_of_the_pocket() -> None:
    """The defect of 13:05: the landing was the way of hops', and the walker went back and forth by it."""
    made = walk_it(standing(IN_POCKET, charges=0), BEHIND, PRESSED)
    assert TELEPORT not in [by for _, by, _ in made]
    assert made[0][0] == IN_POCKET
    assert max(here[0] for here, _, _ in made) > ORIGIN + 70  # through the mouth, east of where it began
    etas = [eta for _, _, eta in made]
    assert all(later < earlier for earlier, later in pairwise(etas))  # every move brings the goal nearer


def test_a_walker_goes_the_same_way_and_a_character_that_teleports_by_itself_hops() -> None:
    walked = walk_it(standing(IN_POCKET, charges=None, slots=(SPARE,)), BEHIND, PRESSED)
    assert ways(standing(IN_POCKET, charges=None, slots=(SPARE,))).name == 'walk'
    assert max(here[0] for here, _, _ in walked) > ORIGIN + 70
    own = walk_it(standing(IN_POCKET, charges=None), BEHIND, PRESSED)
    assert {by for _, by, _ in own} == {TELEPORT}


def test_the_modes_own_move_spends_no_charge_under_its_reserve_and_swaps_no_weapons() -> None:
    assert TELEPORT not in [by for _, by, _ in walk_it(standing(IN_POCKET, charges=30), BEHIND, STANDING)]
    assert TELEPORT not in [by for _, by, _ in walk_it(standing(IN_POCKET, charges=5, in_hand=True), BEHIND, STANDING)]
    in_hand = walk_it(standing(IN_POCKET, charges=30, in_hand=True), BEHIND, STANDING)
    assert TELEPORT in [by for _, by, _ in in_hand]


def test_few_charges_are_spared_where_a_free_jump_still_shortens_the_way_of_hops() -> None:
    open_start = (ORIGIN + 10.5, ORIGIN + 10.5)  # open ground between it and the goal's side
    goal = (ORIGIN + 10.5, ORIGIN + 80.5)
    spared = ways(standing(open_start, charges=5)).leg(standing(open_start, charges=5), goal, PRESSED)
    assert isinstance(spared, Step)
    assert spared.skill == SPARE
    walled = ways(standing(IN_POCKET, charges=5)).leg(standing(IN_POCKET, charges=5), BEHIND, PRESSED)
    assert isinstance(walled, Step)
    assert walled.skill == TELEPORT  # a wall in the free jump's line: the charge is still spent


PLACES = [
    (ORIGIN + x + 0.5, ORIGIN + y + 0.5) for x in range(5, 100, 15) for y in range(5, 100, 15)
]  # across the ground, the pocket's inside among them


@pytest.mark.parametrize(
    'given',
    [
        {'charges': 30},
        {'charges': 5},
        {'charges': 0},
        {'charges': None},
        {'charges': None, 'slots': (SPARE,)},
        {'charges': None, 'slots': ()},
    ],
    ids=['staff', 'few charges', 'empty staff', 'own teleport', 'walk and a jump', 'walk'],
)
@pytest.mark.parametrize('intent', [PRESSED, STANDING], ids=['pressed', 'standing'])
def test_eta_is_infinite_exactly_where_the_set_has_no_way_and_a_move_always_shortens_it(given, intent) -> None:
    ground, _ = pocket()
    for here in PLACES:
        if ground.walkable(*here) is not True:
            continue
        found = standing(here, **given)
        movement_ = ways(found)
        leg, eta = movement_.leg(found, BEHIND, intent), movement_.eta(found, BEHIND, intent)
        if isinstance(leg, NoWay):
            assert eta == (0.0 if leg.arrived else math.inf), (here, leg)
            continue
        assert 0.0 < eta < math.inf, (here, leg)
        after = replace(found, here=leg.spot)
        assert movement_.left(after, BEHIND, intent) < movement_.left(found, BEHIND, intent), (here, leg)


def test_a_goal_no_walked_way_leads_to_is_said() -> None:
    inside_wall = (ORIGIN + 150.5, ORIGIN + 50.5)  # off the ground that was read
    found = standing(IN_POCKET, charges=0)
    leg = ways(found).leg(found, inside_wall, PRESSED)
    assert isinstance(leg, NoWay)
    assert not leg.arrived
    assert ways(found).eta(found, inside_wall, PRESSED) == math.inf


def test_on_open_ground_the_way_is_the_straight_stride() -> None:
    found = replace(standing(IN_POCKET, charges=0), ground=None, rooms=())
    leg = way_leg(found, BEHIND, PRESSED, jumps=(SPARE_JUMP,))
    assert isinstance(leg, Step)
    assert leg.skill == SPARE
    assert leg.spot[1] == pytest.approx(IN_POCKET[1])
    assert leg.spot[0] < IN_POCKET[0]


def test_a_casting_delay_is_waited_out_only_for_a_jump_the_way_would_take() -> None:
    mouth = (ORIGIN + 80.5, ORIGIN + 50.5)  # open ground north of it: the next move is a jump
    found = replace(standing(mouth, charges=0), last_used={SPARE: 99.4})
    movement_ = ways(found)
    assert movement_.wait(found, BEHIND, PRESSED) == pytest.approx(0.4)
    assert movement_.wait(replace(found, last_used={SPARE: 90.0}), BEHIND, PRESSED) == 0.0
    assert movement_.wait(found, BEHIND, replace(PRESSED, may_wait=False)) == 0.0


def test_a_free_jump_leg_is_made_only_where_it_gets_on_faster_than_the_walk() -> None:
    """The navigation class WARPS (travel.py `beats_walk`): a jump takes its casting delay at least (1.0 s, key to
    key), a walk leg its loop's 1.6 s. A warp of 26 beats a walk of 16; one of 9 round a corner does not."""
    assert travel.beats_walk(SPARE_JUMP, SPARE_SOURCE.delay, 26.0, 26.0, 16.0, 16.0)
    assert not travel.beats_walk(SPARE_JUMP, SPARE_SOURCE.delay, 9.0, 9.0, 16.0, 16.0)
    assert travel.beats_walk(SPARE_JUMP, SPARE_SOURCE.delay, 9.0, 9.0, 5.0, 5.0)  # the walk is shorter still
    assert travel.beats_walk(SPARE_JUMP, SPARE_SOURCE.delay, 9.0, 9.0, 16.0, 0.0)  # a walk that saves nothing


def test_a_free_jump_lands_where_the_least_of_the_way_is_left_not_on_the_ways_own_line() -> None:
    """travel.py `landing_in_reach`: the cell in reach with the least walked way left (in view, off a wall, over a clear
    line), never more of it left than the furthest cell of the way's descent the jump reaches. Out of the pocket and
    round its wall the way's own line bends at the corner; a landing off it gets further on."""
    ground, _ = pocket()
    view = Viewport(16 / 9)
    better = 0
    for here in PLACES:
        if ground.walkable(*here) is not True:
            continue
        found = replace(standing(here, charges=0), rooms=())
        field = travel.walked_for(found, BEHIND)
        if field is None or field.left(here) == math.inf:
            continue
        leg = travel.way_leg(found, BEHIND, PRESSED, jumps=(SPARE_JUMP,))
        descent = [
            cost
            for spot, cost in field.descent(here, travel.JUMP_REACH)
            if SPARE_JUMP.least <= math.dist(here, spot) <= SPARE_JUMP.reach
            and view.in_view(view.ground(here, *spot))
            and not any(field.barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            and clear_shot(ground, here, spot, ())
        ]
        if not isinstance(leg, Step) or leg.skill != SPARE or not descent:
            continue
        assert field.left(leg.spot) <= min(descent) + 1e-9, here
        better += field.left(leg.spot) < min(descent) - 1.0
    assert better >= 3  # round the pocket's corners the way's own line is short of the reach


def test_a_landing_is_chosen_within_a_looks_time_from_what_the_way_has_settled() -> None:
    """00:13 on 2026-10-17: `landing_in_reach` asked each cell of the reach for its way by `Walked.of`, which grows
    the field on to it; in a look's time (`planning`) that raised `Unplanned`, and every look of the loop's run failed
    ("the chests again and again"). A field that has reached the character answers with no growth at all."""
    here = (ORIGIN + 80.5, ORIGIN + 50.5)  # open ground east of the pocket: the way round its wall to BEHIND
    found = replace(standing(here, charges=0), rooms=())
    field = travel.walked_for(found, BEHIND)  # grown, with no look's time, as far as the character
    assert field is not None
    with travel.planning(lambda: 1.0, 0.0):  # the look's time over already
        leg = way_leg(found, BEHIND, PRESSED, jumps=(SPARE_JUMP,))
    assert isinstance(leg, Step)
    assert leg.skill == SPARE


def test_a_loop_goals_teleport_hop_lands_short_of_it_never_on_its_own_spot() -> None:
    """travel.py LOOPED `short`: a Teleport aimed onto a chest's own spot was not cast (19:56:40.4 on 2026-10-16); the
    loop's goal is the object's own place (it stays put from look to look), and the hop lands LOOP_SHORT of it."""
    open_ground = (ORIGIN + 80.5, ORIGIN + 80.5)
    chest = (open_ground[0] + 12.0, open_ground[1])  # in one hop: without `short` the landing is its own spot
    found = standing(open_ground, charges=30, in_hand=True, slots=(TELEPORT,))
    leg = movement.hop_leg(found, chest, travel.LOOPED)
    assert isinstance(leg, Step)
    assert leg.skill == TELEPORT
    assert math.dist(leg.spot, chest) >= travel.LOOP_SHORT - 1e-9


class Fickle:
    """A set whose first way gives nothing and says so: its second is asked once the first is distrusted."""

    name, sources = 'fickle', ()

    def applies(self, facts: MoveFacts) -> bool:
        return True

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent):
        if 'first way' not in facts.distrusted:
            return NoWay('the first way has nothing', distrust='first way')
        return Step((1.0, 1.0))


def test_travel_remembers_a_way_the_set_distrusts_and_asks_again() -> None:
    journey = Travel((Fickle(),))  # type: ignore[arg-type]
    found, movement_, leg = journey.asked(standing(IN_POCKET, charges=0), BEHIND, PRESSED)
    assert leg == Step((1.0, 1.0))
    assert journey.distrusted == {'first way': 100.0}
    assert found.distrusted == {'first way': 100.0}
    assert movement_ is not None


# -- the recorder's row ---------------------------------------------------------------------------------


def test_the_snapshot_carries_the_pursuits_goal_only_with_the_switch_on() -> None:
    from types import SimpleNamespace

    from inventory_tracking.takes import macro_state

    def runner(pursuing: bool) -> SimpleNamespace:
        hunter = SimpleNamespace(pursuing=pursuing, pursued=BOSS, pursuit=PRESS, sweep=SimpleNamespace(steps=0))
        return SimpleNamespace(
            attack_mode=True, working=True, routine='hunt any', build=None, hunter=hunter, progress=None, target=None
        )

    assert 'pursuit' not in macro_state.snapshot(runner(False))
    assert macro_state.snapshot(runner(True))['pursuit'] == {
        'goal': {
            'label': 'Grand Vizier of Chaos',
            'do': FIGHT,
            'place': [50.0, 0.0],
            'near': REACH_UNITS,
            'unit': 7,
            'known': True,
        },
        'key': TELEPORT_KEY,
        'pressed_at': 10.0,
        'run_mode': None,  # no look has named the run mode yet (macros/runmode.py)
    }


def test_the_loops_charges_are_spent_only_toward_a_goal_hop_from_and_further() -> None:
    # The player, 2026-10-17: "it looks like we're constantly low on tp charges": ~7 a cycle, most on the last 14-20
    # units to a chest in Blade Warp's delay; the loop's move (LOOPED) hops only toward a goal HOP_FROM and further
    from inventory_tracking.macros.movement import hops
    from inventory_tracking.macros.travel import LOOPED

    here = (ORIGIN + 10.5, ORIGIN + 10.5)
    near = (here[0], here[1] + 20.0)
    facts = standing(here, charges=40, in_hand=True)
    assert not hops(facts, near, LOOPED)
    assert not hops(facts, (here[0], here[1] + 80.0), LOOPED)  # 13:36: no Teleport in the loop at all (HOP_FROM inf)
    assert hops(facts, near, PRESSED)  # the player's own key: as before


def test_a_door_entry_no_hop_lands_nearer_to_ends_the_run_there() -> None:
    # 12:46:41 on 2026-10-18: the run to Catacombs 3's stairs aimed at the remembered entry (within 2) stood 48 s 5.4
    # units off it, "no footing in view brings the character nearer by hops"
    from dataclasses import replace

    from inventory_tracking.macros.goals import ENTRY_GOAL_NEAR
    from inventory_tracking.macros.movement import NO_LANDING
    from inventory_tracking.macros.pursuit import Ended, to_the_door

    stairs = card('the stairs', (4.0, 4.0), warp=True)
    door = goal_named(card=stairs, entry=(18.0, 22.0))
    assert door.near == ENTRY_GOAL_NEAR
    near = replace(facts(door, way=lambda: NoWay(NO_LANDING)), beyond=3.4, attacking=False)
    assert isinstance(to_the_door(near, door), Ended)
    far = replace(near, beyond=20.0)
    assert not isinstance(to_the_door(far, door), Ended)  # far off: not at the door


# -- F1: the run's boss is rushed while nothing hurts (rca/2026-10-18/andariel-cadence-findings.md §5 F1) ------------


def _andariel_look(**given):
    """The look of 11:41:45.63 on 2026-10-18 (take 084143Z-37, the study's §6): landed among Andariel's pack 0.8 s after
    the last strike, a Hold (3.112 s) and a plain Teleport toward her (2.627 s, 0.81 s unstruck, landing in reach)."""
    from inventory_tracking.combat.harm import Harm
    from inventory_tracking.macros.pursuit import FULL, Candidate

    goal = Goal('Andariel', (40.0, 0.0), FIGHT, REACH_UNITS, PRESSED, unit=7, stage=fight('Andariel'))
    goal = replace(goal, **{k: v for k, v in given.items() if k in ('stage', 'clearing', 'do')})
    hold = Candidate(Hold(goal), 3.112, Harm(10, 30), unstruck=0.0, strikes=True)
    step = Step((25.0, 0.0), TELEPORT)
    hop = Candidate(Move(step, goal), 2.627, Harm(10, 30), unstruck=0.81, strikes=True)
    hop = replace(hop, harm=given.get('harm', hop.harm))
    look = Facts(
        100.0, goal, False, True, True, lambda: step, area=37, candidates=(hold, hop), priced=True,
        budget=500, life=1800, near=True, quiet=0.8, hurt=given.get('hurt', False),
    )  # fmt: skip
    run = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=37, looped=True)
    return look, given.get('run', run), hold, hop


def test_a_move_toward_the_runs_boss_is_not_held_to_the_strike_gap_while_nothing_hurts(monkeypatch) -> None:
    # 11:41:45.63: "decision Hold (Hold T3.112, Move/Teleport T2.627)", one strike, then the Move; 1.34 s a hop cycle
    # where a chained hop takes ~0.6 s (the player, 18:00 on 2026-10-18: "F1: ok")
    from inventory_tracking.combat.harm import Harm
    from inventory_tracking.macros import pursuit

    monkeypatch.setattr(pursuit, 'RUSH_THE_BOSS', True)
    look, run, hold, hop = _andariel_look()
    assert decide(look, run) == hop.act
    # Anything hurts: I2 is whole again, one strike first
    look, run, hold, hop = _andariel_look(hurt=True)
    assert decide(look, run) == hold.act
    # The move dearer in life than the hold (and over RUSH_HARM_SHARE of the life): held to the gap as before
    look, run, hold, hop = _andariel_look(harm=Harm(200, 300))
    assert decide(look, run) == hold.act
    # The switch off: today's I2
    monkeypatch.setattr(pursuit, 'RUSH_THE_BOSS', False)
    look, run, hold, hop = _andariel_look()
    assert decide(look, run) == hold.act


def test_the_strike_gap_holds_as_before_on_every_goal_but_the_runs_boss(monkeypatch) -> None:
    from inventory_tracking.macros import pursuit

    monkeypatch.setattr(pursuit, 'RUSH_THE_BOSS', True)
    # No level run: the key's own press (KP_4) toward the same boss
    look, _, hold, _ = _andariel_look()
    assert decide(look, Pursuit('teleport', 99.9)) == hold.act
    assert decide(look, None) == hold.act
    # A run's fight on its way (`clear_way`) or of the rest of the level, and a goal of no fight stage
    for given in ({'clearing': True}, {'stage': None}, {'stage': use('seal')}):
        look, run, hold, _ = _andariel_look(**given)
        assert decide(look, run) == hold.act, given
    # A run paused by the player's hand is no run working
    look, run, hold, _ = _andariel_look()
    assert decide(look, replace(run, paused=True)) == hold.act
