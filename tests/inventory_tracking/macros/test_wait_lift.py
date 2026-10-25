"""WAIT_LIFT (macros/safety.py, 2026-10-23; rca/2026-10-23/death-canyon-findings.md §9): a stand with nothing in
reach that changes nothing lifts the keep ranges' bars after WAIT_HORIZON s. The arena's Chaos Sanctuary run, with the
companions taken along by each Teleport as the game does, stood on WAITING from 48 s to its stall at 103 s ("the loop
never stands")."""

from types import SimpleNamespace
from typing import Any

import pytest

from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import NoWay, Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from tests.inventory_tracking.macros.test_herald_pricing import NOW
from tests.inventory_tracking.macros.test_manaburn_pricing import HERALD, INTO_THE_PACK, priced_toward


KEY = ('fight', HERALD, 'the elite 38')  # `priced_toward`'s goal, as the safety keys a wait
MOST = 2943.0


def asked(monkeypatch, since: float | None) -> dict:
    """The asked move into the arriving Mana Burn pack (herald-manaburn-arriving), after a wait from `since`."""
    monkeypatch.setattr(herald_pack, 'RANGE_LEAD', False)  # the Herald pack's led range is not a keep range here
    made = p.Facts
    # Nothing in reach, as at the stall: the look's pack is 15.7-30 off, its nearest within the strike's reach
    monkeypatch.setattr(
        p, 'Facts', lambda now, goal, there, _in_reach, *rest, **more: made(now, goal, there, False, *rest, **more)
    )

    def waited(safety) -> None:
        if since is not None:
            safety.wait_since = (KEY, since, {}, 1e9)

    decision = priced_toward('herald-manaburn-arriving', Step(INTO_THE_PACK, TELEPORT), before=waited)
    return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == INTO_THE_PACK)


def test_a_wait_past_the_horizon_lifts_the_keep_range_bar(monkeypatch) -> None:
    monkeypatch.setattr(module, 'WAIT_LIFT', True)
    assert asked(monkeypatch, None)['veto'] == manaburn.LANDED
    assert asked(monkeypatch, NOW - module.WAIT_HORIZON / 2)['veto'] == manaburn.LANDED
    assert asked(monkeypatch, NOW - module.WAIT_HORIZON - 0.1)['veto'] is None


def test_off_the_wait_lifts_nothing(monkeypatch) -> None:
    monkeypatch.setattr(module, 'WAIT_LIFT', False)
    assert asked(monkeypatch, NOW - 60.0)['veto'] == manaburn.LANDED


def pricing(now: float, places: dict[int, tuple[float, float]], life: float = 2000.0, in_reach: bool = False) -> Any:
    hostiles = tuple(SimpleNamespace(unit=unit, at=at) for unit, at in places.items())
    return SimpleNamespace(
        facts=SimpleNamespace(now=now, in_reach=in_reach), look=SimpleNamespace(hostiles=hostiles, life=life),
        waited=False,
    )  # fmt: skip


STAND = NoWay(module.WAITING)
GO = p.Move(Step((0.0, 0.0), TELEPORT), Goal('Vizier seal 1', (0.0, 0.0), 'use', 25.0, STANDING))


def test_a_stand_starts_the_wait_and_the_moves_it_lets_go_keep_it(monkeypatch) -> None:
    monkeypatch.setattr(module, 'WAIT_LIFT', True)
    safety, pack = module.Safety(), {7: (30.0, 0.0)}
    safety.waits(pricing(1.0, pack), KEY, GO, MOST)
    assert safety.wait_since is None  # a move is no stand
    safety.waits(pricing(2.0, pack), KEY, STAND, MOST)
    assert safety.wait_since is not None
    assert safety.wait_since[1] == 2.0
    safety.waits(pricing(7.0, pack), KEY, GO, MOST)  # the move the lift let go
    assert safety.wait_since is not None
    assert safety.wait_since[1] == 2.0


def test_a_hostile_coming_a_blow_taken_reach_or_another_goal_ends_the_wait(monkeypatch) -> None:
    monkeypatch.setattr(module, 'WAIT_LIFT', True)
    for after in (
        pricing(5.0, {7: (30.0 - module.WAIT_MOVED, 0.0)}),
        pricing(5.0, {7: (30.0, 0.0)}, life=2000.0 - module.WAIT_LOST * MOST - 1.0),
        pricing(5.0, {7: (30.0, 0.0)}, in_reach=True),
    ):
        safety = module.Safety()
        safety.waits(pricing(1.0, {7: (30.0, 0.0)}), KEY, STAND, MOST)
        safety.waits(after, KEY, GO, MOST)
        assert safety.wait_since is None
    safety = module.Safety()
    safety.waits(pricing(1.0, {7: (30.0, 0.0)}), KEY, STAND, MOST)
    safety.waits(pricing(5.0, {7: (30.0, 0.0)}), ('use', None, 'Vizier seal 1'), GO, MOST)
    assert safety.wait_since is None


@pytest.mark.slow
def test_the_chaos_sanctuary_run_with_the_companions_along_no_longer_stands(monkeypatch) -> None:
    """The arena's pursuit loop of test_cs_run.py (seed 1) with the companions as the game moves them: off it stalls on
    WAITING at the Vizier's seal; on it works the whole route alive. Seed 1 since 2026-10-24: seed 3's off arm no
    longer stalls after that day's other changes (rca/2026-10-24/red-goldens-findings.md §5); seed 1 stands on WAITING
    toward Vizier seal 1 at 57 s off and takes all five seals alive on."""
    from tests.inventory_tracking.scenarios.arena import game
    from tests.inventory_tracking.scenarios.arena.situations.cs_run import FULL, ONCE, pair, played

    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    label, run, presses = pair(ONCE, FULL)[1]
    monkeypatch.setattr(module, 'WAIT_LIFT', False)
    stood, _, _ = played(label, run, presses, 1)
    monkeypatch.setattr(module, 'WAIT_LIFT', True)
    went, _, _ = played(label, run, presses, 1)
    assert stood.ended == 'stalled'
    assert went.done
    assert went.dead_at is None
    assert all(at is not None for at in went.seals.values())
