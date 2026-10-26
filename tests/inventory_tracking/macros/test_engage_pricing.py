"""The T5 pack's plan in the safety's prices (combat/engage.py ENGAGE_PLAN through combat/pack.py `jump_hold`, `held`,
`walk_free` and macros/safety.py `move_price`). The player, 2026-10-26 ~09:10: "teleport to safe spot, once; ... walk
closer, behind the daemons that gets aggro". The looks are test_herald_pricing.py's, cut from take
20261021T063019Z-77: H-A tanked (surrounded: a real threat, the hop goes); H-B with the pack on the demons."""

import pytest

from inventory_tracking.combat import engage, pack
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.skills import TELEPORT
from tests.inventory_tracking.macros.test_herald_pricing import priced


@pytest.fixture(autouse=True)
def plan_on(monkeypatch):
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', True)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)  # as test_herald_pack.py: the Herald tactic alone


def jumps(decision: dict) -> list[dict]:
    return [c for c in decision['candidates'] if c['act'] == 'Move' and c.get('skill') == TELEPORT]


def test_surrounded_is_a_real_threat_the_hop_out_goes() -> None:
    act, _ = priced('herald-t5-tanked')
    assert isinstance(act, p.Move)
    assert act.reason.startswith(pack.BACK_SAID)  # the safety's survival move stays above the plan
    assert act.step.skill == TELEPORT


def test_with_the_pack_on_the_demons_no_voluntary_jump_is_made() -> None:
    safety = module.Safety()
    act, decision = priced('herald-t5-held', safety)
    plan = engage.active()
    assert plan is not None
    assert plan.committed
    assert not (isinstance(act, p.Move) and act.step.skill == TELEPORT and not act.dodge and not act.reason)
    for c in jumps(decision):
        if not c['why'] and not c.get('retreat'):
            assert 'ENGAGE_PLAN' in (c.get('barred') or ''), c


def test_off_the_held_look_prices_as_before(monkeypatch) -> None:
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', False)
    act, decision = priced('herald-t5-held')
    assert engage.active() is None
    assert not any('ENGAGE_PLAN' in (c.get('barred') or '') for c in decision['candidates'])
    assert act is not None
