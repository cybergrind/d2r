"""How a Warlock moves (builds/warlock/movement.py): Blade Warp as a jump source, before a staff's Teleport and after
Teleport of the character's own (Enigma).

The first half asks the sets with facts alone; the second makes moves with `Travel` in the fakes' game.
"""

import itertools
import logging
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.movement import (
    BLADE_WARP_JUMP,
    BLADE_WARP_SOURCE,
    MOVEMENT,
    WARP_CLEARED,
    WARP_DELAY,
    WARP_SECONDS,
    WARP_SPEED,
)
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.game.records import Teleport
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import MoveFacts, NoWay
from inventory_tracking.macros.movement import SHARED, OwnTeleport, StaffTeleport, Walk
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import (
    DELAY_SHOWN,
    DELAY_TICK,
    JUMP_DISTRUST,
    JUMP_LEAST,
    JUMP_REACH,
    KEY_POLL,
    LOW_CHARGES,
    OWN_MOVE,
    PLAN_AHEAD,
    PLAYER_STEP,
    PRESSED,
    SEEK,
    STRIDE,
    WALLED,
    Stale,
    Step,
    Travel,
    move_facts,
    navigator,
    spare_jump,
    step_line,
)
from tests.inventory_tracking.macros import moves
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, character_of, world
from tests.inventory_tracking.macros.moves import ASPECT, HERE, IN_HAND, NOW, skills, wall_with_a_gap, walled


def facts(**changes) -> MoveFacts:
    """The character at HERE on a level with no wall read, Blade Warp and Teleport on keys, a staff with charges in
    hand (where the blade comes first)."""
    changes.setdefault('slots', (BLADE_WARP, None, TELEPORT))
    changes.setdefault('staff', IN_HAND)
    return moves.facts(**changes)


def jumps_of(here: MoveFacts, intent=OWN_MOVE):
    """The jumps of the set that applies, as `Travel.jumps` asks them."""
    movement = navigator(MOVEMENT, here)
    assert movement is not None
    return movement.jumps(here, intent)


def leg_of(here: MoveFacts, goal, intent=OWN_MOVE):
    movement = navigator(MOVEMENT, here)
    assert movement is not None
    return movement.leg(here, goal, intent)


def test_the_blade_is_a_thrown_jump_with_a_casting_delay():
    assert (BLADE_WARP_JUMP.skill, BLADE_WARP_JUMP.line) == (BLADE_WARP, True)
    assert (BLADE_WARP_JUMP.seconds, BLADE_WARP_JUMP.speed) == (WARP_SECONDS, WARP_SPEED) == (0.35, 45.0)
    assert (BLADE_WARP_JUMP.reach, BLADE_WARP_JUMP.least) == (JUMP_REACH, JUMP_LEAST)
    assert (BLADE_WARP_SOURCE.jump, BLADE_WARP_SOURCE.delay) == (BLADE_WARP_JUMP, WARP_DELAY)
    assert WARP_DELAY == 1.05  # from the key: the game's 0.8 s runs from the cast's action frame, 0.2 s later


def test_the_warlocks_sets_are_the_shared_ones_with_the_blade_first_but_after_its_own_teleport():
    assert [type(movement) for movement in MOVEMENT] == [StaffTeleport, OwnTeleport, Walk]
    staff, own, walk = MOVEMENT
    assert staff.sources == (BLADE_WARP_SOURCE, *SHARED[0].sources)
    assert own.sources == (*SHARED[1].sources, BLADE_WARP_SOURCE)
    assert walk.sources == (BLADE_WARP_SOURCE,)
    assert spare_jump(MOVEMENT, HUNT_SLOTS) == BLADE_WARP_JUMP
    assert spare_jump(MOVEMENT, (TELEPORT,)) is None


def test_blade_warp_ready_comes_before_teleport():
    found = jumps_of(facts())
    assert skills(found) == [BLADE_WARP, TELEPORT]
    assert [(jump.line, jump.reach, jump.least) for jump in found] == [
        (True, JUMP_REACH, JUMP_LEAST),
        (False, JUMP_REACH, JUMP_LEAST),
    ]


def test_blade_warp_in_its_casting_delay_is_no_jump_until_the_delay_is_over():
    assert skills(jumps_of(facts(last_used={BLADE_WARP: NOW - 0.1}))) == [TELEPORT]
    made = facts(now=0.5, last_used={BLADE_WARP: 0.0})
    assert skills(jumps_of(made)) == [TELEPORT]
    assert skills(jumps_of(replace(made, now=WARP_DELAY))) == [BLADE_WARP, TELEPORT]  # over at the delay itself
    assert skills(jumps_of(facts(last_used={BLADE_WARP: -math.inf}))) == [BLADE_WARP, TELEPORT]  # never made
    assert skills(jumps_of(facts(last_used={TELEPORT: NOW}))) == [BLADE_WARP, TELEPORT]  # Teleport has no delay


def test_a_jump_that_moved_nothing_is_distrusted_for_as_long_as_the_caller_says():
    failed = facts(failed={BLADE_WARP: NOW - JUMP_DISTRUST})
    assert skills(jumps_of(failed)) == [TELEPORT]  # to the second: left out
    assert skills(jumps_of(replace(failed, now=NOW + 0.5))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(failed, PLAYER_STEP)) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(facts(failed={TELEPORT: NOW - 1.0}))) == [BLADE_WARP]
    assert jumps_of(facts(failed={BLADE_WARP: NOW - 1.0, TELEPORT: NOW - 1.0})) == ()


def test_the_staff_in_hand_is_jumped_by_down_to_the_floor_of_charges():
    def worn(charges: int) -> MoveFacts:
        return facts(staff=replace(IN_HAND, charges=charges))

    assert skills(jumps_of(worn(69))) == [BLADE_WARP, TELEPORT]
    assert skills(jumps_of(worn(LOW_CHARGES))) == [BLADE_WARP, TELEPORT]  # the floor itself is still spent
    assert skills(jumps_of(worn(LOW_CHARGES - 1))) == [BLADE_WARP]
    assert skills(jumps_of(worn(0))) == [BLADE_WARP]
    for intent in (SEEK, PLAYER_STEP):  # the same floor whoever asks a set: the player's hop is not a set's
        assert skills(jumps_of(worn(LOW_CHARGES - 1), intent)) == [BLADE_WARP]


def test_the_staff_in_the_other_weapon_set_is_a_swap_away_and_no_jump():
    assert skills(jumps_of(facts(staff=replace(IN_HAND, in_hand=False)))) == [BLADE_WARP]


def test_with_no_staff_teleport_is_the_characters_own_skill_and_comes_before_the_blade():
    # The player, 2026-10-18: "now we have an enigma ... stop using blade warp in almost all situations"
    assert skills(jumps_of(facts(staff=None))) == [TELEPORT, BLADE_WARP]
    assert skills(jumps_of(facts(staff=None, slots=(TELEPORT,)))) == [TELEPORT]
    # Teleport distrusted (a hop that moved nobody): the blade is the jump left
    assert skills(jumps_of(facts(staff=None, failed={TELEPORT: NOW - 1.0}))) == [BLADE_WARP]


def test_with_its_own_teleport_a_stride_is_teleported_and_the_blades_delay_is_never_waited_for():
    goal = (HERE[0] + 30.0, HERE[1])
    short = replace(OWN_MOVE, short=14.0)
    own = facts(staff=None)
    assert leg_of(own, goal, short) == Step(
        pytest.approx((HERE[0] + 16.0, HERE[1])),  # pyrefly: ignore[bad-argument-type]
        TELEPORT,
    )
    # Over a wall too: Teleport needs no line (the blade would have walked)
    over = leg_of(facts(staff=None, ground=walled(wall_with_a_gap)), (5020.5, 5000.5))
    assert isinstance(over, Step)
    assert over.skill == TELEPORT
    # The blade in its delay: Teleport is ready, nothing is waited for, whoever asks
    just = replace(own, last_used={BLADE_WARP: NOW - 0.3})
    movement = navigator(MOVEMENT, just)
    assert isinstance(movement, OwnTeleport)
    for intent in (SEEK, PRESSED, OWN_MOVE):
        assert movement.wait(just, goal, intent) == 0.0


def test_a_skill_that_is_on_no_key_is_no_jump():
    assert jumps_of(facts(slots=())) == ()
    assert jumps_of(facts(slots=(None, 7))) == ()
    assert skills(jumps_of(facts(slots=(BLADE_WARP,), staff=IN_HAND))) == [BLADE_WARP]


def test_a_stride_is_by_the_blade_and_by_teleport_while_its_delay_runs():
    goal = (HERE[0] + 30.0, HERE[1])
    short = replace(OWN_MOVE, short=14.0)
    # approx spots: the Step's == compares them with a tolerance
    assert leg_of(facts(), goal, short) == Step(
        pytest.approx((HERE[0] + 16.0, HERE[1])),  # pyrefly: ignore[bad-argument-type]
        BLADE_WARP,
    )
    delayed = facts(last_used={BLADE_WARP: NOW})
    assert leg_of(delayed, goal, short) == Step(
        pytest.approx((HERE[0] + 16.0, HERE[1])),  # pyrefly: ignore[bad-argument-type]
        TELEPORT,
    )
    assert leg_of(facts(slots=()), goal) == Step(
        pytest.approx((HERE[0] + STRIDE, HERE[1]))  # pyrefly: ignore[bad-argument-type]
    )


def test_a_wall_in_the_blades_line_is_not_handed_to_teleport():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    assert leg_of(facts(ground=ground, slots=(BLADE_WARP,)), goal) == NoWay(WALLED)
    # The stride asks for one jump: with the blade ready and a wall in its line it is not handed to Teleport
    assert leg_of(facts(ground=ground), goal) == NoWay(WALLED)
    # Teleport, when it is the jump, needs no line: it lands beyond the wall
    over = leg_of(facts(ground=ground, last_used={BLADE_WARP: NOW}), goal)
    assert isinstance(over, Step)
    assert (over.skill, over.spot) == (TELEPORT, pytest.approx(goal))


def test_the_way_round_is_jumped_along_by_the_blade_and_walked_otherwise():
    ground = walled(wall_with_a_gap)
    goal = (5020.5, 5000.5)
    round_it = replace(SEEK, detour=True)
    empty = facts(ground=ground, staff=replace(IN_HAND, charges=0))
    jumped = leg_of(empty, goal, round_it)
    assert isinstance(jumped, Step)
    assert jumped.skill == BLADE_WARP
    assert JUMP_LEAST <= math.dist(HERE, jumped.spot) <= JUMP_REACH
    for other in (replace(empty, last_used={BLADE_WARP: NOW}), replace(empty, staff=IN_HAND, slots=(TELEPORT,))):
        walk = leg_of(other, goal, round_it)  # the blade in its delay, or Teleport alone: the way is walked
        assert isinstance(walk, Step)
        assert walk.skill is None
        assert math.dist(HERE, walk.spot) <= STRIDE


def test_the_blades_delay_is_waited_out_for_the_seek_step_where_its_line_is_clear():
    goal = (HERE[0] + 30.0, HERE[1])
    just = facts(last_used={BLADE_WARP: NOW - 0.3})
    for movement in MOVEMENT:
        assert movement.wait(just, goal, SEEK) == pytest.approx(WARP_DELAY - 0.3)
        assert movement.wait(just, goal, OWN_MOVE) == 0.0
        assert movement.wait(replace(just, ground=walled(wall_with_a_gap)), (5020.5, 5000.5), SEEK) == 0.0
        assert movement.wait(replace(just, slots=(TELEPORT,)), goal, SEEK) == 0.0


# --- Travel, in the fakes' game, with the Warlock's sets -------------------------------------------------


def keys(_world, wanted):
    return {skill: KEYS[skill] for skill in wanted}


def staff_of(play: Game) -> Teleport:
    """The staff `game` gave the character (or a later copy of it)."""
    assert play.staff is not None
    return play.staff


def game(**changes):
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    play = Game(world(**changes))
    play.staff = Teleport(10, 20, True)
    return play


def test_the_jumps_are_blade_warp_first_then_teleport_without_a_swap():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    assert [jump.line for jump in travel.jumps(run, play.world)] == [True, False]
    travel.warped_at = play.clock.now  # its casting delay runs
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += WARP_DELAY
    assert travel.jump_by(run, play.world) == BLADE_WARP
    travel.warped_at = play.clock.now
    play.staff = replace(staff_of(play), in_hand=False)  # a swap away: not a jump
    assert travel.jump_by(run, play.world) is None


def test_low_on_charges_the_modes_own_jumps_leave_the_staff_alone():
    # user, 2026-10-11: "track number of tp charges when using staff, and leverage warp more when low"
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    play.staff = replace(staff_of(play), charges=LOW_CHARGES)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP, TELEPORT]
    play.staff = replace(staff_of(play), charges=LOW_CHARGES - 1)
    assert [jump.skill for jump in travel.jumps(run, play.world)] == [BLADE_WARP]
    travel.warped_at = play.clock.now
    assert travel.jump_by(run, play.world) is None  # its delay runs: a walk, not a charge


def test_a_blade_warp_that_moved_nothing_is_left_out_for_a_while():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    play.warp_lands = False
    with pytest.raises(Abort, match='Blade Warp: the character did not move'):
        travel.make(run, Step((5012.0, 5000.0), BLADE_WARP), play.world, ASPECT, keys, Ground(()))
    assert travel.jump_by(run, play.world) == TELEPORT
    play.clock.now += JUMP_DISTRUST + 1
    assert travel.jump_by(run, play.world) == BLADE_WARP


def test_a_blade_warp_made_is_remembered_for_its_casting_delay():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    assert travel.delayed == {BLADE_WARP}
    travel.make(run, Step((5012.0, 5000.0), BLADE_WARP), play.world, ASPECT, keys, Ground(()))
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert travel.warped_at == pytest.approx(play.clock.now, abs=2.0)
    assert set(travel.jumped_at) == {BLADE_WARP}
    # The key's down is remembered, and its release: with no delay state read (the fakes' character) the
    # clock counts the delay from the release, as before the state was read.
    assert travel.warped_at < travel.released_at[BLADE_WARP] <= play.clock.now
    read = move_facts(run, run.world(), None, ASPECT, travel)
    assert read.since_used(BLADE_WARP) == pytest.approx(play.clock.now - travel.released_at[BLADE_WARP])


def test_a_straight_stride_is_by_blade_warp_and_ends_short_of_its_goal():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    found = travel.stride(run, play.world, Ground(()), ASPECT, (5030.0, 5000.0), replace(OWN_MOVE, short=14.0))
    assert found is not None
    assert found.skill == BLADE_WARP
    assert found.spot == pytest.approx((5016.0, 5000.0))
    assert step_line(found, (5000.0, 5000.0)) == 'a stride of 16 toward the nearest, by Blade Warp'


def test_with_no_straight_stride_a_move_is_made_along_the_way_round_the_wall():
    # Drifter Cavern, 09:43 on 2026-10-12: the staff empty and the firing spot behind a wall.
    play = game()
    play.staff = replace(staff_of(play), charges=0)
    ground = walled(wall_with_a_gap)
    travel, run = Travel(MOVEMENT), play.run()
    goal = (5020.5, 5000.5)
    assert travel.stride(run, play.world, ground, ASPECT, goal) is None
    found = travel.around(run, play.world, ground, ASPECT, goal)
    assert found is not None
    assert found.skill == BLADE_WARP  # a clear line to a spot further along the way
    assert found.spot[1] > 5005
    travel.warped_at = play.clock.now  # under its casting delay: walked
    walk = travel.around(run, play.world, ground, ASPECT, goal)
    assert walk is not None
    assert walk.skill is None
    assert walk.spot[1] > 5002


# --- Blade Warp's casting delay as the game shows it (rca/2026-10-13/latency-findings.md, fix 2) -------------

# From a key's down to state 185 set and cleared, seconds, as the takes of 2026-10-13 have them: the median of
# the 123 keys of 21:42, its p90, its p99 and its latest (a cast begun late with the recorder starved). Counted as
# WARP_DELAY from the key's down, the last two would be refused: the key waits for the state instead.
RECORDED = [(0.19, 1.00), (0.24, 1.07), (0.35, 1.17), (0.40, 1.555)]
FAR = (5200.0, 5000.0)  # a goal many Blade Warps away, on open ground
NO_TELEPORT = tuple(None if skill == TELEPORT else skill for skill in HUNT_SLOTS)  # no staff: the walk's set


class Delayed(Game):
    """The fakes' game with Blade Warp's casting delay as the game plays it, from the key's down: the delay state
    is set `shown` seconds after a key the game took and cleared `over` after it; a key before `accepts` (`over`
    unless said) is refused, it moves nobody and sets no state (`refused`: seconds after the key before). `reads`
    off: the state is not read (None)."""

    def __init__(self, shown: float, over: float, reads: bool = True, accepts: float | None = None) -> None:
        super().__init__(world(area=101, slots=NO_TELEPORT))
        self.shown, self.over, self.reads = shown, over, reads
        self.accepts = over if accepts is None else accepts
        self.taken: list[float] = []  # the clock at each key's down the game took
        self.released: list[float] = []
        self.refused: list[float] = []
        self.refusing = False
        codes = self.keys.keycodes([KEYS[BLADE_WARP].encode()])
        assert codes is not None
        code = codes[0]
        press = self.keys.press

        def down(key: int) -> bool:
            if key == code:
                now = self.clock.now
                self.refusing = bool(self.taken) and now - self.taken[-1] < self.accepts
                (self.refused if self.refusing else self.taken).append(now - self.taken[-1] if self.refusing else now)
            return press(key)

        self.keys.press = down

    def react(self, event) -> None:
        if event == ('key', KEYS[BLADE_WARP]):
            self.released.append(self.clock.now)
            if self.refusing:
                self.refusing = False
                return
        super().react(event)

    def read(self):
        found = super().read()
        since = self.clock.now - self.taken[-1] if self.taken else math.inf
        cooling = (self.shown <= since < self.over) if self.reads else None
        self.world = replace(found, player=replace(character_of(found), cooldown=cooling))
        return self.world


def legs(play: Game, travel: Travel, run, count: int = 3, intent=PRESSED) -> None:
    """`count` Blade Warps toward FAR as the pursuit makes them (hunting/moves.py `advance`): a delay not about to end
    slept out (`Travel.pause`), then the leg asked for (`toward`) and made (`make`)."""
    for _ in range(count):
        while (wait := travel.pause(run, run.world(), Ground(()), ASPECT, FAR, intent)) > 0:
            run.pace.sleep(max(wait, 0.04))
        step = travel.toward(run, run.world(), Ground(()), ASPECT, FAR, intent)
        assert isinstance(step, Step)
        assert step.skill == BLADE_WARP
        travel.make(run, step, run.world(), ASPECT, keys, Ground(()), intent=intent, goal=FAR)


@pytest.mark.parametrize(('shown', 'over'), RECORDED)
def test_with_the_delay_state_read_the_key_goes_down_at_its_clear_and_never_before(shown, over):
    play = Delayed(shown, over)
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run)
    assert play.refused == []
    gaps = [b - a for a, b in itertools.pairwise(play.taken)]
    assert len(gaps) == 2
    # at the first look that has it clear: a look every KEY_POLL, and `press_skill`'s own for the character
    assert all(over <= gap <= over + KEY_POLL + 0.03 + 1e-9 for gap in gaps), gaps


def test_with_no_delay_state_read_the_clock_counts_from_the_keys_release_as_before():
    play = Delayed(*RECORDED[0], reads=False)
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run)
    assert play.refused == []
    assert len(play.taken) == 3
    for released, next_down in zip(play.released, play.taken[1:], strict=False):
        assert next_down >= released + WARP_DELAY - 1e-9


def test_a_clear_state_before_the_cast_threw_is_not_the_delay_over():
    play = Delayed(0.40, 1.0)
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run, count=1)
    keyed = play.taken[0]
    play.clock.now = keyed + 0.3  # the state not set yet: the cast has not thrown
    assert travel.left(BLADE_WARP, play.clock.now, False) == pytest.approx(WARP_DELAY - 0.3)
    # clear once it should have shown: over at WARP_CLEARED from the key (run-0305-findings.md §5.1)
    shown = travel.left(BLADE_WARP, keyed + DELAY_SHOWN + 1e-6, False)
    assert shown == pytest.approx(WARP_CLEARED - DELAY_SHOWN, abs=1e-5)
    assert travel.left(BLADE_WARP, keyed + WARP_CLEARED + 1e-6, False) == -math.inf
    assert travel.left(BLADE_WARP, keyed + 1.2, True) == DELAY_TICK  # still set: the next tick at the soonest


# The game of 06:05 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §5.1): keys at 06:07:16.802 and 06:08:01.594,
# 0.977 and 0.986 s after the key before, went down on a look that read state 185 clear and were refused. Over
# three games every refused key came 0.928 to 0.986 s after the one before (11 of 17 such keys); 0 of 35 keys
# 0.99 to 1.06 s after it were refused. The state clears 0.96 to 1.03 s after the key (travel.py's comment).
CLEAR_EARLY, TAKEN_FROM = 0.96, 0.99


def test_a_clear_state_read_before_the_cooldown_is_over_holds_the_key():
    play = Delayed(RECORDED[0][0], CLEAR_EARLY, accepts=TAKEN_FROM)
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run, count=1)
    keyed = play.taken[0]
    assert travel.left(BLADE_WARP, keyed + 0.977, False) > 0  # the 06:07:16.802 key: the state clear, too soon
    assert travel.left(BLADE_WARP, keyed + WARP_CLEARED, False) == -math.inf
    legs(play, travel, run, count=2)
    assert play.refused == []
    gaps = [b - a for a, b in itertools.pairwise(play.taken)]
    assert all(WARP_CLEARED - 1e-9 <= gap <= WARP_CLEARED + KEY_POLL + 0.03 + 1e-9 for gap in gaps), gaps


def warp_again(play: Game, travel: Travel, run) -> Step:
    """The next leg toward FAR as the pursuit asks it after a move that failed: the delay waited, the leg chosen."""
    while (wait := travel.pause(run, run.world(), Ground(()), ASPECT, FAR, PRESSED)) > 0:
        run.pace.sleep(max(wait, 0.04))
    step = travel.toward(run, run.world(), Ground(()), ASPECT, FAR, PRESSED)
    assert isinstance(step, Step)
    return step


def test_a_warp_the_game_did_not_take_is_tried_again_when_due_and_not_walked():
    # §5.1: after each refused key the navigator walked three 15-unit legs before it warped again (5.2 to 5.5 s
    # for what two warps make in 2.3). A key the game took no cast for (the state never set after it) is the
    # cooldown's refusal, not a way that leads nowhere: the warp is made again as soon as it is due.
    play = Delayed(RECORDED[0][0], CLEAR_EARLY, accepts=WARP_CLEARED + 0.03)  # refused even at the floor
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run, count=1)
    step = warp_again(play, travel, run)
    with pytest.raises(Abort, match='did not move'):
        travel.make(run, step, run.world(), ASPECT, keys, Ground(()), intent=PRESSED, goal=FAR)
    assert len(play.refused) == 1
    assert travel.jump_failed == {}
    again = warp_again(play, travel, run)
    assert again.skill == BLADE_WARP  # not a walk
    travel.make(run, again, run.world(), ASPECT, keys, Ground(()), intent=PRESSED, goal=FAR)
    assert len(play.taken) == 2


def test_a_second_warp_in_a_row_the_game_did_not_take_is_a_failure_to_leave_alone():
    # The retry is one: a cast the game keeps refusing (no mana, say) is a way that leads nowhere for a while.
    play = Delayed(RECORDED[0][0], CLEAR_EARLY, accepts=math.inf)
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run, count=1)
    for _ in range(2):
        step = warp_again(play, travel, run)
        assert step.skill == BLADE_WARP
        with pytest.raises(Abort, match='did not move'):
            travel.make(run, step, run.world(), ASPECT, keys, Ground(()), intent=PRESSED, goal=FAR)
    assert len(play.refused) == 2
    assert set(travel.jump_failed) == {BLADE_WARP}
    assert warp_again(play, travel, run).skill is None  # walked


def test_a_jump_is_offered_plan_ahead_before_its_delay_ends_to_an_intent_that_may_wait():
    play = game()
    travel, run = Travel(MOVEMENT), play.run()
    travel.warped_at = play.clock.now
    play.clock.now += WARP_DELAY - PLAN_AHEAD + 0.01
    assert travel.jump_by(run, play.world, PRESSED) == BLADE_WARP  # its key then waits for the delay's end
    assert travel.jump_by(run, play.world, OWN_MOVE) == TELEPORT  # the mode's own move does not wait
    assert travel.pause(run, play.world, Ground(()), ASPECT, FAR, PRESSED) == 0.0
    play.clock.now += PLAN_AHEAD
    assert travel.jump_by(run, play.world, OWN_MOVE) == BLADE_WARP


def test_a_character_moved_while_the_jump_waits_for_its_delay_has_the_leg_chosen_again():
    play = Delayed(*RECORDED[0])
    travel, run = Travel(MOVEMENT), play.run()
    legs(play, travel, run, count=1)
    while (wait := travel.pause(run, run.world(), Ground(()), ASPECT, FAR, PRESSED)) > 0:
        run.pace.sleep(wait)
    step = travel.toward(run, run.world(), Ground(()), ASPECT, FAR, PRESSED)
    assert isinstance(step, Step)
    chosen = run.world()

    def pushed() -> None:
        stand = play.character
        play.world = replace(play.world, player=replace(stand, x=stand.x + 3.0))

    play.arrivals.append((play.clock.now + 0.05, pushed))
    with pytest.raises(Stale, match='the leg is chosen again'):
        travel.make(run, step, chosen, ASPECT, keys, Ground(()), intent=PRESSED, goal=FAR)
    assert len(play.taken) == 1  # no key
    assert travel.jump_failed == {}  # not a failed way to distrust


def test_the_pointer_waits_on_the_next_aim_during_the_flight_and_the_legs_are_timed(caplog):
    play = Delayed(*RECORDED[0])
    travel, run = Travel(MOVEMENT), play.run()
    snaps = []
    snap = run.actuator.snap

    def counted(*args, **kwargs):
        snaps.append(args)
        snap(*args, **kwargs)

    run.actuator.snap = counted
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        legs(play, travel, run)
        travel.paced(play.clock.now, 'a test')
    assert len(snaps) == 2  # the second and third aims: a step from where the flight before left the pointer
    timed = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: leg time: Blade Warp')]
    assert len(timed) == 2
    gaps = [b - a for a, b in itertools.pairwise(play.taken)]
    assert [float(line.split()[5].removesuffix('s')) for line in timed] == pytest.approx(gaps, abs=1e-3)
    pace = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: leg time: level run')]
    assert len(pace) == 1
    places = [(5000.0, 5000.0), *play.warps]
    assert f'level run (a test): {sum(math.dist(a, b) for a, b in itertools.pairwise(places)):.0f} units' in pace[0]
    assert '3 jumps, 0 walks' in pace[0]
    assert travel.tally.since is None  # begun again


def test_the_loops_goals_spare_the_staff_where_blade_warp_reaches_and_keep_its_last_charges():
    # The player, 2026-10-16: "it actually can get too expensive (~100k+ for full recharge), so probably we need to
    # carefully use teleport staff charges when running loop". The KP_6 loop's goals (travel.py LOOPED) take a Blade
    # Warp wherever it reaches toward the hop's landing, whatever the charges; the key's own goal (PRESSED) hops by
    # Teleport while the staff holds WARP_CHARGES (the player, 2026-10-11).
    from inventory_tracking.macros.travel import LOOPED, WARP_CHARGES
    from tests.inventory_tracking.macros.test_hunt import ROOMS

    play = game()
    play.staff = Teleport(60, 69, True)
    travel, run = Travel(MOVEMENT), play.run()
    goal = (5040.0, 5000.0)  # one hop away, over open ground

    pressed = travel.toward(run, run.world(), Ground(()), ASPECT, goal, PRESSED, ROOMS)
    looped = travel.toward(run, run.world(), Ground(()), ASPECT, goal, LOOPED, ROOMS)

    assert isinstance(pressed, Step)
    assert pressed.skill == TELEPORT
    assert isinstance(looped, Step)
    assert looped.skill == BLADE_WARP
    assert LOOPED.reserve == LOW_CHARGES  # the player's own steps keep the last of them
    assert WARP_CHARGES < 60
