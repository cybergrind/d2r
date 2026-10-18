"""The shared movement sets (macros/movement.py): facts and an intent in, a decision out; no game."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.combat.stance import RUN_SPEED, WALK_LATENCY, Jump
from inventory_tracking.macros.build import JumpSource, NoWay, Step
from inventory_tracking.macros.movement import (
    OWN_TELEPORT,
    SHARED,
    STAFF_TELEPORT,
    TELEPORT_JUMP,
    TELEPORT_SECONDS,
    OwnTeleport,
    StaffTeleport,
    Walk,
)
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import (
    JUMP_DISTRUST,
    JUMP_LEAST,
    JUMP_REACH,
    LOW_CHARGES,
    OWN_MOVE,
    PLAYER_STEP,
    SEEK,
    STRIDE,
    THERE,
    WALLED,
    around_of,
    navigator,
    stride_of,
)
from tests.inventory_tracking.macros.moves import HERE, IN_HAND, NOW, facts, skills, wall_with_a_gap, walled


DART = Jump(900, 0.3, 40.0, JUMP_REACH, JUMP_LEAST, line=True)  # a thrown jump of no build
DELAY = 0.8
SLOW_DART = JumpSource(DART, delay=DELAY)
GOAL = (HERE[0] + 30.0, HERE[1])


def worn(charges: int = 69, **changes):
    return facts(staff=replace(IN_HAND, charges=charges, **changes))


def test_the_shared_sets_are_the_staff_the_own_skill_and_the_walk_in_that_order():
    assert [type(shared) for shared in SHARED] == [StaffTeleport, OwnTeleport, Walk]
    assert [shared.name for shared in SHARED] == ['staff teleport', 'own teleport', 'walk']
    assert [shared.sources for shared in SHARED] == [(STAFF_TELEPORT,), (OWN_TELEPORT,), ()]
    assert Jump(TELEPORT, TELEPORT_SECONDS, math.inf, JUMP_REACH, JUMP_LEAST, line=False) == TELEPORT_JUMP


def test_each_set_applies_to_its_own_situation():
    staff, own, walk = SHARED
    situations = (worn(), worn(0, in_hand=False), facts(), facts(slots=()))
    assert [staff.applies(here) for here in situations] == [True, True, False, False]
    assert [own.applies(here) for here in situations] == [False, False, True, False]
    assert [walk.applies(here) for here in situations] == [True, True, True, True]


def test_the_staff_in_hand_is_jumped_by_down_to_the_intents_reserve():
    staff = StaffTeleport()
    assert skills(staff.jumps(worn(69), OWN_MOVE)) == [TELEPORT]
    assert skills(staff.jumps(worn(LOW_CHARGES), OWN_MOVE)) == [TELEPORT]  # with the reserve itself left, still
    assert staff.jumps(worn(LOW_CHARGES - 1), OWN_MOVE) == ()
    assert staff.jumps(worn(0), OWN_MOVE) == ()
    assert staff.jumps(worn(14), replace(OWN_MOVE, reserve=15)) == ()
    assert skills(staff.jumps(worn(1), replace(OWN_MOVE, reserve=1))) == [TELEPORT]
    assert skills(staff.jumps(worn(0), replace(OWN_MOVE, reserve=0))) == [TELEPORT]  # 0: spent to the last and beyond


def test_the_staff_in_the_other_weapon_set_is_a_swap_away_and_no_jump():
    staff = StaffTeleport()
    assert staff.jumps(worn(in_hand=False), OWN_MOVE) == ()
    assert staff.jumps(worn(in_hand=False), replace(PLAYER_STEP, reserve=0)) == ()  # whoever asks: a set never swaps


def test_teleport_as_the_characters_own_skill_asks_for_no_charges():
    own = OwnTeleport()
    assert skills(own.jumps(facts(), replace(OWN_MOVE, reserve=1000))) == [TELEPORT]
    assert Walk().jumps(facts(), OWN_MOVE) == ()


def test_a_skill_that_is_on_no_key_is_no_jump():
    assert StaffTeleport().jumps(replace(worn(), slots=(None, 7)), OWN_MOVE) == ()
    assert OwnTeleport().jumps(facts(slots=()), OWN_MOVE) == ()


def test_a_jump_that_moved_nothing_is_distrusted_for_as_long_as_the_intent_says():
    own = OwnTeleport()
    failed = facts(failed={TELEPORT: NOW - JUMP_DISTRUST})
    assert own.jumps(failed, OWN_MOVE) == ()  # to the second: left out
    assert skills(own.jumps(replace(failed, now=NOW + 0.5), OWN_MOVE)) == [TELEPORT]
    assert skills(own.jumps(failed, PLAYER_STEP)) == [TELEPORT]  # three seconds for the player's step


def test_a_source_with_a_casting_delay_is_ready_when_the_delay_is_over():
    assert not SLOW_DART.ready(facts(slots=(DART.skill,), last_used={DART.skill: NOW - 0.1}), OWN_MOVE)
    made = facts(slots=(DART.skill,), now=0.5, last_used={DART.skill: 0.0})
    assert not SLOW_DART.ready(made, OWN_MOVE)
    assert SLOW_DART.ready(replace(made, now=DELAY), OWN_MOVE)  # over at the delay itself
    assert SLOW_DART.ready(facts(slots=(DART.skill,)), OWN_MOVE)  # never made
    assert SLOW_DART.cooling(made) == pytest.approx(0.3)
    assert SLOW_DART.cooling(replace(made, now=DELAY)) == 0.0
    assert SLOW_DART.cooling(facts()) == 0.0
    assert STAFF_TELEPORT.cooling(facts(last_used={TELEPORT: NOW})) == 0.0  # no delay: nothing to run


def test_jumps_a_build_adds_come_before_the_sets_own():
    led = OwnTeleport().led_by(SLOW_DART)
    assert led.sources == (SLOW_DART, OWN_TELEPORT)
    assert (led.name, type(led)) == ('own teleport', OwnTeleport)
    on_keys = facts(slots=(DART.skill, TELEPORT))
    assert led.jumps(on_keys, OWN_MOVE) == (DART, TELEPORT_JUMP)
    assert led.jumps(replace(on_keys, last_used={DART.skill: NOW}), OWN_MOVE) == (TELEPORT_JUMP,)
    assert OwnTeleport().sources == (OWN_TELEPORT,)  # the shared set is not changed


def test_a_leg_is_the_stride_by_the_sets_jumps_and_with_a_detour_the_way_round():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    for movement, here in ((OwnTeleport(), facts(ground=ground)), (Walk(), facts(ground=ground, slots=()))):
        jumps = movement.jumps(here, OWN_MOVE)
        for intent in (OWN_MOVE, replace(SEEK, short=3.0, shot=True), PLAYER_STEP):
            straight = stride_of(here, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)
            assert movement.leg(here, goal, intent) == straight
            assert movement.leg(here, goal, replace(intent, detour=True)) == around_of(here, goal, jumps=jumps)
    assert Walk().leg(facts(ground=ground, slots=()), goal, OWN_MOVE) == NoWay(WALLED)
    assert isinstance(Walk().leg(facts(ground=ground, slots=()), goal, replace(OWN_MOVE, detour=True)), Step)
    assert OwnTeleport().leg(facts(), GOAL, replace(OWN_MOVE, shuns=lambda spot: True)) == NoWay(
        'the place a stride toward the goal ends at is shunned'
    )


def test_eta_is_priced_from_the_leg_and_is_inf_where_there_is_none():
    walk, own = Walk(), OwnTeleport()
    afoot = facts(slots=())
    far = (HERE[0] + 2 * STRIDE, HERE[1])
    assert walk.eta(afoot, far, OWN_MOVE) == pytest.approx(2 * (WALK_LATENCY + STRIDE / RUN_SPEED))
    assert walk.eta(afoot, (HERE[0] + 6.0, HERE[1]), OWN_MOVE) == pytest.approx(WALK_LATENCY + 6.0 / RUN_SPEED)
    assert own.eta(facts(), (HERE[0] + 20.0, HERE[1]), OWN_MOVE) == pytest.approx(TELEPORT_SECONDS)
    assert own.eta(facts(), (HERE[0] + 30.0, HERE[1]), replace(OWN_MOVE, short=14.0)) == pytest.approx(TELEPORT_SECONDS)
    assert walk.leg(afoot, HERE, OWN_MOVE) == NoWay(THERE, arrived=True)
    assert walk.eta(afoot, HERE, OWN_MOVE) == math.inf
    assert walk.eta(facts(ground=walled(wall_with_a_gap), slots=()), (5020.5, 5000.5), OWN_MOVE) == math.inf


def test_a_casting_delay_is_waited_out_only_for_a_jump_worth_having_toward_the_goal():
    led = Walk().led_by(SLOW_DART)
    cooling = facts(slots=(DART.skill,), last_used={DART.skill: NOW - 0.3})
    assert led.wait(cooling, GOAL, SEEK) == pytest.approx(0.5)
    assert led.wait(cooling, GOAL, OWN_MOVE) == 0.0  # this caller does not wait
    assert led.wait(replace(cooling, slots=()), GOAL, SEEK) == 0.0  # on no key
    assert led.wait(replace(cooling, last_used={}), GOAL, SEEK) == 0.0  # no delay runs
    assert led.wait(replace(cooling, last_used={DART.skill: NOW - 1.0}), GOAL, SEEK) == 0.0  # over
    assert led.wait(cooling, (HERE[0] + 1.0, HERE[1]), SEEK) == 0.0  # there already, as far as a move counts
    behind = replace(cooling, ground=walled(wall_with_a_gap))
    assert led.wait(behind, (5020.5, 5000.5), SEEK) == 0.0  # a wall in the thrown jump's line
    assert led.wait(behind, (HERE[0], HERE[1] + 20.0), SEEK) == pytest.approx(0.5)  # south: the line is clear
    # The player's step waits without a look at the line: its caller has looked, or takes what comes
    assert led.wait(behind, (5020.5, 5000.5), PLAYER_STEP) == pytest.approx(0.5)
    assert led.wait(cooling, (HERE[0] + 1.0, HERE[1]), PLAYER_STEP) == pytest.approx(0.5)
    assert Walk().wait(cooling, GOAL, SEEK) == 0.0  # no source has a delay


def test_the_navigators_set_answers_for_every_situation_of_the_staff():
    for here in (worn(), worn(0), worn(in_hand=False), facts(), facts(slots=())):
        movement = navigator(SHARED, here)
        assert movement is not None
        assert movement.applies(here)
        assert isinstance(movement.leg(here, GOAL, OWN_MOVE), Step)


def test_a_hop_toward_a_doors_spot_lands_on_it_with_nothing_short():
    # The Catacombs stairs (13:00-13:10 on 2026-10-18): the run east of the block of walls went to the door's spot 3
    # units south-west of the mark; the loop's LOOP_SHORT took the last hop 3 units back toward the character, east of
    # the block, and the click walked round it. A door's goal goes with nothing short (macros/goals.py `way_out`).
    from inventory_tracking.levels.model import Room
    from inventory_tracking.macros.travel import LOOP_SHORT, LOOPED_TELEPORT

    mark = (5020.5, 5000.5)

    def stairs(x, y) -> bool:  # the block x -7..0, y -7..+1 from the mark, an alcove x -4..-2, y -1..+1 open south
        dx, dy = int(x - mark[0] + 0.5), int(y - mark[1] + 0.5)
        return not (-7 <= dx <= 0 and -7 <= dy <= 1) or (-4 <= dx <= -2 and -1 <= dy <= 1)

    spot = (mark[0] - 3.0, mark[1] + 2.0)
    east = facts(here=(mark[0] + 5.0, mark[1]), ground=walled(stairs), area=35, rooms=(Room(1, 984, 984, 32, 32),))
    own = OwnTeleport()
    assert own.leg(east, spot, replace(LOOPED_TELEPORT, short=0.0)) == Step(spot, TELEPORT)
    short = own.leg(east, spot, LOOPED_TELEPORT)
    assert isinstance(short, Step)
    assert math.dist(short.spot, spot) == pytest.approx(LOOP_SHORT)  # on the character's side: east of the block
