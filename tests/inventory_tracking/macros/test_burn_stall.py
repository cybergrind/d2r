"""BURN_STALL_COMMIT's memory in the safety (combat/threats/manaburn.py, macros/safety.py `Safety.burn_stalls`,
`commit_of`; rca/2026-10-24/manaburn-cycle-findings.md §1): take 20261024T132953Z-63, 16:31:13-33, a tier 5 Herald pack
of Sand Warriors (monstats 92, Extra Fast and Mana Burn) held the fight off 20 s by the keep range's LANDED bar, the
life and the mana full throughout."""

from types import SimpleNamespace

import pytest

from inventory_tracking.combat.harm import Harm
from inventory_tracking.combat.survival import CALM
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING


SAND_WARRIOR = 92
EXTRA_FAST_BURN = (20, 27, 6, 25)
GOAL = Goal('full clear: the elite 92', (0.0, 30.0), 'fight', 22.0, STANDING)


def warrior(unit: int, at: tuple[float, float], life: float = 1.0, txt: int = SAND_WARRIOR) -> SimpleNamespace:
    return SimpleNamespace(unit=unit, at=at, txt=txt, modifiers=EXTRA_FAST_BURN, flags=16, life=life, tier=5)


PACK = (warrior(1, (0.0, 30.0)), warrior(2, (4.0, 31.0)))


def look(now: float, hostiles=PACK, landed: bool = True) -> SimpleNamespace:
    """One look's pricing as `burn_stalls` reads it: the approach barred by the keep range (`landed`) or not."""
    approach = p.Candidate(
        p.Move(Step((0.0, 25.0), TELEPORT), GOAL, ''), 1.0, Harm(0.0, 0.0, barred=manaburn.LANDED if landed else None)
    )
    return SimpleNamespace(
        facts=SimpleNamespace(now=now),
        burning=tuple(manaburn.burners(hostiles)),
        look=SimpleNamespace(hostiles=tuple(hostiles)),
        candidates=[approach],
        here=(0.0, 0.0),
    )


LOOT = SimpleNamespace(life=2943.0, max_life=2943.0)
RETREAT = p.Move(Step((0.0, -14.0), TELEPORT), GOAL, 'retreating: every progress act is vetoed')


@pytest.fixture
def safety(monkeypatch) -> module.Safety:
    monkeypatch.setattr(manaburn, 'BURN_STALL_COMMIT', True)
    found = module.Safety()
    found.mana_safe = True
    return found


def stalled(safety: module.Safety, seconds: float, step: float = 0.4, **kw) -> None:
    now = 0.0
    while now <= seconds:
        safety.burn_stalls(look(now, **kw), RETREAT, LOOT)  # pyrefly: ignore[bad-argument-type]  # a look's reads only
        now += step


def kept(safety: module.Safety, hostiles=PACK) -> list[manaburn.Burner]:
    burning = manaburn.burners(hostiles)
    look = SimpleNamespace(hostiles=hostiles)
    key = safety.commit_of((0.0, 0.0), burning, look, CALM, 1.0)  # pyrefly: ignore[bad-argument-type]  # its hostiles only
    return manaburn.committed(burning, key)


def test_the_take_s_twenty_seconds_of_bars_commit_to_the_pack_after_five(safety) -> None:
    stalled(safety, manaburn.COMMIT_SECONDS - 0.5)
    assert safety.burn_commit is None
    stalled(safety, manaburn.COMMIT_SECONDS + 0.5)
    assert safety.burn_commit == manaburn.key_of(manaburn.burners(PACK))
    assert kept(safety) == []  # fought as any tier 4-5 Herald pack: no keep range, no LANDED, no burn hop


def test_with_the_switch_off_nothing_is_remembered(safety, monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'BURN_STALL_COMMIT', False)
    stalled(safety, 10.0)
    assert safety.burn_stall is None
    assert safety.burn_commit is None


def test_a_member_dented_meanwhile_is_progress_and_no_stall(safety) -> None:
    now = 0.0
    while now <= 10.0:
        hurt = (warrior(1, (0.0, 30.0), life=1.0 - now / 10.0), PACK[1])
        safety.burn_stalls(look(now, hostiles=hurt), RETREAT, LOOT)
        now += 0.4
    assert safety.burn_commit is None


def test_the_bar_gone_longer_than_the_gap_ends_the_stall(safety) -> None:
    stalled(safety, 3.0)
    safety.burn_stalls(look(3.0 + manaburn.STALL_GAP + 0.5, landed=False), RETREAT, LOOT)
    assert safety.burn_stall is None


def test_no_commit_with_the_mana_unsafe_or_a_ghost_about(safety) -> None:
    safety.mana_safe = False
    stalled(safety, 10.0)
    assert safety.burn_commit is None
    safety.mana_safe = True
    ghost = warrior(3, (6.0, 6.0), txt=38)  # wraith1: its blows burn 200-300 by its own row
    stalled(safety, 10.0, hostiles=(*PACK, ghost))
    assert safety.burn_commit is None


def test_a_burn_or_a_hurt_while_committed_keeps_the_pack_at_range_again_for_good(safety) -> None:
    stalled(safety, 6.0)
    key = safety.burn_commit
    assert key is not None
    safety.burn_leaving = 'mana 400 of 745, burnt 300 0.2 s ago, 2 drainers in reach'
    assert kept(safety) == manaburn.burners(PACK)
    assert safety.burn_commit is None
    assert key in safety.burn_spoiled
    safety.burn_leaving = None
    stalled(safety, 12.0)
    assert safety.burn_commit is None  # spoiled: not again for this pack
