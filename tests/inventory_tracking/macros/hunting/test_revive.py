"""The firing spot at a reviver raising its pack (macros/hunting/revive.py REVIVER_STAND): when its fight goal is the
reviver, and that every raising reviver is a boss to the hunt (never left alone as one that takes no damage)."""

from dataclasses import dataclass, field, replace

import pytest

from inventory_tracking.game.layout import MINION_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import pursuit
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import revive
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.routes.model import FIGHT, USE
from tests.inventory_tracking.macros.fakes import world
from tests.inventory_tracking.scenarios.revivers.table import raised, reviver


SHAMAN = reviver('fallenshaman1')['txt']
FALLEN = raised('FallenShaman')['fallen1']
HERE = (5000.0, 5000.0)


@dataclass
class Hunter:
    """What `reviver_goal` reads and writes of the hunt."""

    reach: float = 20.0
    raisers: frozenset[int] = field(default_factory=frozenset)
    passed: dict[object, float] = field(default_factory=dict)
    running: bool = False


def mob(unit: int, txt: int, east: float, flags: int = MINION_FLAG) -> Monster:
    return Monster(unit, txt, 1, HERE[0] + east, HERE[1], flags=flags, life=100, max_life=100)


@pytest.fixture
def stand(monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_STAND', True)


def look(*monsters: Monster):
    return replace(world(), monsters=monsters), list(monsters)


def test_off_the_goal_is_left_as_it_is(monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_STAND', False)
    hunter, (seen, foes) = Hunter(), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    assert revive.reviver_goal(hunter, seen, foes, None) is None
    assert hunter.raisers == frozenset()


def test_a_shaman_past_the_reach_raising_the_pack_in_reach_is_the_fight(stand):
    hunter, (seen, foes) = Hunter(), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, None)
    assert goal is not None
    assert (goal.unit, goal.do, goal.near) == (2, FIGHT, revive.STAND_NEAR)
    assert not goal.clearing  # the pursued fight's boss: never left alone (hunt.py `Hunter.boss`)
    assert hunter.raisers == frozenset({2})


def test_a_reviver_with_nothing_of_its_family_near_is_no_goal(stand):
    hunter, (seen, foes) = Hunter(), look(mob(2, SHAMAN, 25.0))
    assert revive.reviver_goal(hunter, seen, foes, None) is None
    assert hunter.raisers == frozenset()


def test_a_reviver_too_far_to_go_for_is_no_goal_but_still_never_left_alone(stand):
    far = revive.STAND_FROM + 5.0
    hunter, (seen, foes) = Hunter(), look(mob(1, FALLEN, far - 10.0), mob(2, SHAMAN, far))
    assert revive.reviver_goal(hunter, seen, foes, None) is None
    assert hunter.raisers == frozenset({2})


def test_a_use_and_a_route_boss_stay_their_own(stand):
    hunter, (seen, foes) = Hunter(), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    use = Goal('a chest', (5010.0, 5000.0), USE, 3.0, STANDING)
    assert revive.reviver_goal(hunter, seen, foes, use) is use


def test_the_reviver_goal_is_kept_once_it_is_the_goal(stand):
    hunter, (seen, foes) = Hunter(), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 10.0))
    first = revive.reviver_goal(hunter, seen, foes, None)
    assert first is not None
    assert revive.reviver_goal(hunter, seen, foes, first) is first


# --- The run's own goal kept (REVIVER_KEEPS_RUN, 2026-10-23; rca/2026-10-23/unraveler-findings.md §5) ---


def clearing_goal(unit: int = 1):
    """The agenda's goal of 08:51:43: "full clear: the elite 61 (1190739679)", a level run's clearing fight."""
    return Goal('full clear: the elite 61', (HERE[0] + 12.0, HERE[1]), FIGHT, 20.0, STANDING, unit=unit, clearing=True)


def test_the_reviver_takes_over_the_runs_clearing_goal_and_the_run_goes_on(stand):
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, clearing_goal())
    assert goal is not None
    assert (goal.unit, goal.do, goal.near, goal.place) == (2, FIGHT, revive.STAND_NEAR, (HERE[0] + 25.0, HERE[1]))
    assert goal.clearing
    assert pursuit.routed(goal)  # the run's own: run_level fights it, neither ends the run nor hands the press on
    assert not pursuit.ends_run(goal, pressed=False)


def test_the_08_51_goal_read_no_route_stage_without_the_fix(stand, monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_KEEPS_RUN', False)
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, clearing_goal())
    assert goal is not None
    assert not pursuit.routed(goal)  # "the level run ends: nothing is left to go to" / "the route's own step"
    assert pursuit.ends_run(goal, pressed=False)


def test_with_no_goal_a_level_runs_reviver_goal_is_a_clearing_one(stand):
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, None)
    assert goal is not None
    assert goal.clearing
    assert pursuit.routed(goal)


def test_a_reviver_the_run_passed_is_not_gone_for_again(stand):
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    hunter.passed[2] = 99.0  # no way to it: hunting/choice.py `pass_by`
    goal = clearing_goal()
    assert revive.reviver_goal(hunter, seen, foes, goal) is goal
    assert hunter.raisers == frozenset({2})  # still never left alone where it stands in reach


# --- A guarded drop's fight taken over stays the run's (REVIVER_OWN_RUN, 2026-10-24; death-halls-findings.md) ---


def guarded_fight(unit: int = 1):
    """23:30:44 on 2026-10-23: a level run's healing potion's guards "the fight first" (hunting/choice.py `goal`:
    `first_fight` keeps `guarded`, the goal's only claim to be the run's)."""
    return Goal('a super healing potion, on the way: the fight first (15 in the way)', (HERE[0] + 12.0, HERE[1]), FIGHT,
                20.0, STANDING, unit=unit, guarded=True)  # fmt: skip


def test_the_2331_takeover_read_no_route_stage_without_the_fix(stand, monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_OWN_RUN', False)
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    assert pursuit.routed(guarded_fight())
    goal = revive.reviver_goal(hunter, seen, foes, guarded_fight())
    assert goal is not None
    assert goal.unit == 2
    assert not pursuit.routed(goal)  # the live bug: every leg ended or handed its press on
    assert pursuit.ends_run(goal, pressed=False)


def test_a_guarded_fight_taken_over_in_a_level_run_stays_the_runs(stand, monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_OWN_RUN', True)
    hunter, (seen, foes) = Hunter(running=True), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, guarded_fight())
    assert goal is not None
    assert goal.unit == 2
    assert goal.clearing  # the run's own fight
    assert not goal.guarded  # at the reviver, no pickup's guard
    assert pursuit.routed(goal)
    assert not pursuit.ends_run(goal, pressed=False)


def test_out_of_a_level_run_a_takeover_claims_no_run(stand, monkeypatch):
    monkeypatch.setattr(revive, 'REVIVER_OWN_RUN', True)
    hunter, (seen, foes) = Hunter(running=False), look(mob(1, FALLEN, 12.0), mob(2, SHAMAN, 25.0))
    goal = revive.reviver_goal(hunter, seen, foes, guarded_fight())
    assert goal is not None
    assert not goal.clearing
