"""THROWN_OUT (macros/pursuit.py; rca/2026-10-23/death-canyon-findings.md): with throws read, a retreat is a jump out
of the throwers' lines, never a walk inside them (the arena's canyon re-cut died in a retreat walk of 16 at 4.6 s)."""

import pytest

from inventory_tracking.combat.harm import Harm
from inventory_tracking.macros import pursuit as p
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.routes.model import FIGHT


PACK = tuple((20.0, float(y)) for y in range(-7, 8))


def retreat(spot, skill, mean):
    goal = Goal('the pack', (20.0, 0.0), FIGHT, 22.0, STANDING)
    return p.Candidate(p.Move(Step(spot, skill), goal), 1.0, Harm(mean, mean, (), (mean,) * 4), True, clear=10.0)


def facts(*candidates, throwers=PACK):
    return p.Facts(
        0.0, None, False, True, True, lambda: Step((0.0, 0.0)), candidates=candidates, priced=True, budget=1000.0,
        life=2943.0, clear=20.0, throwers=throwers,
    )  # fmt: skip


def test_a_retreat_under_read_throws_is_the_jump_out_of_reach_not_the_cheaper_walk():
    walk = retreat((-16.0, 0.0), None, 10.0)
    inside = retreat((-5.0, 0.0), TELEPORT, 20.0)
    out = retreat((-14.0, 0.0), TELEPORT, 40.0)
    chosen = p.arbitrate(facts(walk, inside, out))
    assert isinstance(chosen, p.Move)
    assert chosen.step.spot == (-14.0, 0.0)  # 34 from the pack: out of SHOT_REACH


def test_with_no_jump_priced_the_walk_is_still_made():
    walk = retreat((-16.0, 0.0), None, 10.0)
    chosen = p.arbitrate(facts(walk))
    assert isinstance(chosen, p.Move)
    assert chosen.step.skill is None


@pytest.mark.parametrize('switch', [False, True])
def test_with_no_throws_read_or_the_switch_off_the_cheapest_retreat_as_before(monkeypatch, switch):
    monkeypatch.setattr(p, 'THROWN_OUT', switch)
    walk = retreat((-16.0, 0.0), None, 10.0)
    out = retreat((-14.0, 0.0), TELEPORT, 40.0)
    chosen = p.arbitrate(facts(walk, out, throwers=() if switch else PACK))
    assert isinstance(chosen, p.Move)
    assert chosen.step.skill is None
