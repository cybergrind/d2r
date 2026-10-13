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
from inventory_tracking.levels.model import Ground, Room, Target, Walkable, pack_cells
from inventory_tracking.macros import goals, hunt, movement, pickup, route, teleport, travel
from inventory_tracking.macros.build import BuildSettings, Intent, JumpSource, MoveFacts, NoWay, Step
from inventory_tracking.macros.goals import PICK_UP, PURSUED, REACH, Goal, goal_of
from inventory_tracking.macros.pursuit import FRESH, Defer, Facts, Hold, Move, Operate, Pursuit, Told, decide
from inventory_tracking.macros.runner import EXPIRES, TELEPORT as TELEPORT_KEY
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED, STANDING, Travel, Walked, navigator, way_leg
from inventory_tracking.macros.world import NO_OWNER, VALUABLE, Drop, Monster, Teleport
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, enter, fight, leave, loot, stand, use
from inventory_tracking.terror.bosses import SUPER_UNIQUE_FLAG


Point = tuple[float, float]
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


def test_the_goals_distances_are_the_hands_own() -> None:
    assert goals.USE_NEAR == teleport.THING_REACH
    assert goals.STAND_NEAR == route.STAND_NEAR
    assert goals.PLACE_NEAR == teleport.SPOT_NEAR
    assert goals.PICK_NEAR == pickup.STOP_UNITS
    assert goals.BOSS_MARK_UNITS == hunt.BOSS_MARK_UNITS


def test_a_use_stage_is_the_object_on_the_stages_mark_within_a_clicks_reach() -> None:
    seal = card('Vizier seal 1', (10.0, 20.0), use_=396)
    found = named(stage=use('Vizier seal 1'), route='Diablo', card=seal)
    assert found is not None
    assert (found.do, found.place, found.near, found.label) == (USE, (50.0, 100.0), goals.USE_NEAR, 'Vizier seal 1')
    assert found.mark is seal
    assert found.spend is PRESSED


def test_a_stand_and_a_way_on_are_their_marks() -> None:
    assert named(stage=stand('the altar'), card=card('the altar', (2.0, 2.0))).do == STAND
    door = named(stage=enter('River of Flame', 107), card=card('River of Flame', (2.0, 2.0), warp=True))
    assert door.do == ENTER
    assert door.do not in PURSUED


def test_a_fight_with_no_mark_is_the_boss_where_it_stands() -> None:
    boss = monster(7, (60.0, 0.0), SUPER_UNIQUE_FLAG | 0x08)
    pack = [monster(8, (20.0, 0.0), 0x10), monster(9, (25.0, 0.0), 0x08)]  # a minion, a plain unique
    found = named(stage=fight('Grand Vizier of Chaos'), foes=[*pack, boss])
    assert (found.do, found.place, found.unit, found.near) == (FIGHT, (60.0, 0.0), 7, REACH_UNITS)
    assert found.known
    assert found.label == 'Grand Vizier of Chaos'


def test_a_boss_out_of_sight_is_where_one_was_last_seen_alive() -> None:
    # The tracker holds every super unique's last place, the dead ones too; alive are the remembered ones.
    remembered = [(7, 300.0, 0.0, True), (8, 100.0, 0.0, True), (9, 50.0, 0.0, False)]
    supers = [(300.0, 0.0), (40.0, 40.0)]  # the boss alive at 300, a boss dead at (40, 40); 8 is a plain unique
    found = named(stage=fight('Lord De Seis'), remembered=remembered, supers=supers)
    assert (found.place, found.unit, found.known) == ((300.0, 0.0), None, True)
    assert 'last seen' in found.label
    assert named(stage=fight('Lord De Seis'), remembered=remembered, supers=supers, gone=frozenset({7})) is None


def test_a_fight_with_a_mark_is_the_boss_by_it_else_the_mark() -> None:
    mark = card('Diablo', (20.0, 20.0))
    stage = fight('Diablo', 'Diablo')
    far = monster(7, (400.0, 400.0), SUPER_UNIQUE_FLAG)  # a super unique that is not this mark's
    near = monster(8, (120.0, 110.0), 0, txt=243)  # the act boss, by its type
    assert named(stage=stage, card=mark, foes=[far]).place == (100.0, 100.0)
    found = named(stage=stage, card=mark, foes=[far, near])
    assert (found.unit, found.place) == (8, (120.0, 110.0))


def test_a_boss_nothing_is_known_of_is_sought_and_the_label_says_so() -> None:
    found = named(stage=fight('Infector of Souls'), elsewhere=lambda: ((70.0, 0.0), 'an unexplored room'))
    assert (found.do, found.place, found.known) == (FIGHT, (70.0, 0.0), False)
    assert found.label == 'seek Infector of Souls: toward an unexplored room'
    assert named(stage=fight('Infector of Souls'), elsewhere=lambda: None) is None
    assert named(stage=fight('Infector of Souls')) is None


def test_elsewhere_is_asked_only_when_nothing_is_known() -> None:
    def never():
        raise AssertionError('asked')

    assert named(stage=fight('x'), foes=[monster(7, (9.0, 9.0), SUPER_UNIQUE_FLAG)], elsewhere=never).unit == 7


def test_a_valuable_beside_the_character_comes_before_the_routes_goal() -> None:
    drop = Drop(55, 4.0, 3.0, 'Ring', VALUABLE)
    found = named(stage=use('Vizier seal 1'), card=card('Vizier seal 1', (10.0, 20.0), use_=396), drop=drop)
    assert (found.do, found.place, found.unit) == (PICK_UP, (4.0, 3.0), 55)
    assert 'Ring' in found.label


def test_without_a_stage_the_goal_is_the_cards_first_mark() -> None:
    assert named(card=card('a room', (4.0, 4.0), kind='explore')).do == REACH
    assert named(card=card('the chest', (4.0, 4.0), use_=5)).do == USE
    assert named(card=card('the stairs', (4.0, 4.0), warp=True)).do == ENTER
    assert named() is None


def test_a_stage_whose_mark_the_card_does_not_hold_follows_the_card_and_says_so() -> None:
    found = named(stage=use('Vizier seal 1'), card=card('Diablo', (4.0, 4.0)))
    assert (found.do, found.place) == (REACH, (20.0, 20.0))
    assert 'Vizier seal 1 is not marked yet' in found.label


def test_the_loot_and_the_leaving_are_the_routes_own_step() -> None:
    for stage in (loot(), leave()):
        found = named(stage=stage, card=card('Diablo', (4.0, 4.0)))
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
    assert decide(facts(door, way=unasked), PRESS) == Defer(door)
    assert isinstance(decide(facts(door, in_reach=True, now=20.0, way=unasked), PRESS), Hold)  # the press is old


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
    there = lambda: NoWay('there', arrived=True)  # ruff: ignore[lambda-assignment]
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


def walk_it(found: MoveFacts, goal: Point, intent: Intent, most: int = 40) -> list[tuple[Point, int | None, float]]:
    """The moves the set gives from `found` to the goal, each made as it is given: (from, by, eta before)."""
    made = []
    for _ in range(most):
        movement_ = navigator(SETS, found)
        assert movement_ is not None
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
    assert navigator(SETS, standing(IN_POCKET, charges=None, slots=(SPARE,))).name == 'walk'
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
    spared = navigator(SETS, standing(open_start, charges=5)).leg(standing(open_start, charges=5), goal, PRESSED)
    assert isinstance(spared, Step)
    assert spared.skill == SPARE
    walled = navigator(SETS, standing(IN_POCKET, charges=5)).leg(standing(IN_POCKET, charges=5), BEHIND, PRESSED)
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
        movement_ = navigator(SETS, found)
        assert movement_ is not None
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
    leg = navigator(SETS, found).leg(found, inside_wall, PRESSED)
    assert isinstance(leg, NoWay)
    assert not leg.arrived
    assert navigator(SETS, found).eta(found, inside_wall, PRESSED) == math.inf


def test_on_open_ground_the_way_is_the_straight_stride() -> None:
    found = replace(standing(IN_POCKET, charges=0), ground=None, rooms=())
    leg = way_leg(found, BEHIND, PRESSED, jumps=(SPARE_JUMP,))
    assert isinstance(leg, Step)
    assert leg.skill == SPARE
    assert leg.spot[1] == pytest.approx(IN_POCKET[1])
    assert leg.spot[0] < IN_POCKET[0]


def test_a_casting_delay_is_waited_out_only_for_a_jump_the_way_would_take() -> None:
    mouth = (ORIGIN + 80.5, ORIGIN + 50.5)  # open ground north of it: the next move is a jump
    found = replace(standing(mouth, charges=0), last_used={SPARE: 99.6})
    movement_ = navigator(SETS, found)
    assert movement_.wait(found, BEHIND, PRESSED) == pytest.approx(0.6)
    assert movement_.wait(replace(found, last_used={SPARE: 90.0}), BEHIND, PRESSED) == 0.0
    assert movement_.wait(found, BEHIND, replace(PRESSED, may_wait=False)) == 0.0


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

    from inventory_tracking.combat import macro_state

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
    }
