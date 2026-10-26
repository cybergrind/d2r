"""The T5 pack's plan and Death Mark (builds/warlock/mark.py `plan_mark`, combat/engage.py ENGAGE_PLAN). The player,
2026-10-26 ~09:10: "move daemons to get aggro with DM between char and pack". Today 08:52:49.9-54.4 (session
20261026T025911Z, rca/2026-10-26/herald-engage-findings.md §1.4): five marks in 4.5 s on minions of 28-84/128 life,
the demons on the pack all the while: the plan marks once a MARK phase, and again only when the demons lost the pack."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import engage, pack
from tests.inventory_tracking.builds.warlock.test_pack_mark import FAR, HERALD, demon, facts, hulk


NOW = 100.0  # test_pack_mark's clock
NEAR = hulk(5, 5011.0, 5003.0)  # 11.4 off, no body in front of it
ON_THE_PACK = (demon(70, 744, 5012.0, 5002.0), demon(71, 189, 5013.0, 4999.0))


@pytest.fixture(autouse=True)
def plan_on(monkeypatch):
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', True)
    pack.FIRST.add(DEATH_MARK)
    yield
    pack.FIRST.discard(DEATH_MARK)


def test_off_the_rules_as_before(monkeypatch):
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', False)
    assert mark.plan_mark(facts(HERALD, NEAR, FAR)) == (False, None)
    assert mark.target(facts(HERALD, NEAR, FAR)) == HERALD


def test_the_plan_marks_once_a_phase_then_waits_for_the_landing():
    asked = facts(HERALD, NEAR, FAR)
    assert mark.target(asked) == HERALD  # the Herald, which can be clicked
    assert engage.PLAN.phase is engage.Phase.MARK
    pack.keyed(DEATH_MARK, NOW + 0.05)
    assert mark.plan_mark(facts(HERALD, NEAR, FAR)) == (True, None)  # its key is out: no second key


def test_the_demons_on_the_pack_no_mark_goes_on_a_dying_member():
    asked = facts(HERALD, NEAR, FAR)
    assert mark.target(asked) == HERALD
    pack.keyed(DEATH_MARK, NOW)
    cast_at = {(DEATH_MARK, HERALD.unit_id): NOW, (DEATH_MARK, None): NOW - 3.0}
    dying = replace(NEAR, life=2)
    later = replace(facts(dying, demons=ON_THE_PACK, cast_at=cast_at), now=NOW + 1.0)  # the marked Herald died
    assert mark.plan_mark(later) == (False, None)
    assert engage.PLAN.phase is engage.Phase.CLOSE_IN
    assert mark.target(later) is None  # before the plan: the pack's order marked the dying member at once
    alive = replace(facts(NEAR, demons=ON_THE_PACK, cast_at=cast_at), now=NOW + 1.1)
    assert mark.target(alive) == NEAR  # one that outlives the strike's casts: the rules' mark stands
