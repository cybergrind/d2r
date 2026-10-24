"""T5_BEST_LINE (builds/warlock/echoing_strike/attack.py, 2026-10-23; the player ~20:35: "Best line in T5 packs
(Recommended)"): a tier 5 Herald is struck by the best line, its minions included, not held; every other leader is
held as before."""

from dataclasses import replace

from inventory_tracking.builds.warlock.echoing_strike import attack as module
from inventory_tracking.builds.warlock.echoing_strike.attack import EchoingStrike
from inventory_tracking.combat.policy import Foe, Observation


HERE = (5000.0, 5000.0)


def flat(txt):
    return 1400.0


def seen(tier: int) -> Observation:
    """Three minions on one bearing (one line takes all three) and their Herald (`tier`) alone on another."""
    pack = {unit: Foe(310, (HERE[0] + dx, HERE[1]), 5000.0, tier=tier) for unit, dx in ((1, 8.0), (2, 10.0), (3, 12.0))}
    return Observation(HERE, {**pack, 9: Foe(310, (HERE[0], HERE[1] + 10.0), 5000.0, True, tier=tier)})


def aimed(look: Observation) -> tuple[int, int | None]:
    attack = EchoingStrike(damage_of=flat, hold=True)
    found = attack.aim(look)
    assert found is not None
    return found.unit, attack.held.unit


def test_a_tier_5_herald_is_not_held_the_best_line_goes_through_its_pack(monkeypatch) -> None:
    monkeypatch.setattr(module, 'T5_BEST_LINE', True)
    unit, held = aimed(seen(5))
    assert unit in {1, 2, 3}
    assert held is None


def test_a_tier_4_herald_and_any_with_the_switch_off_are_held(monkeypatch) -> None:
    monkeypatch.setattr(module, 'T5_BEST_LINE', True)
    assert aimed(seen(4)) == (9, 9)
    monkeypatch.setattr(module, 'T5_BEST_LINE', False)
    assert aimed(seen(5)) == (9, 9)


def test_a_held_tier_5_herald_is_let_go_and_a_plain_leader_is_still_held(monkeypatch) -> None:
    monkeypatch.setattr(module, 'T5_BEST_LINE', True)
    attack = EchoingStrike(damage_of=flat, hold=True)
    attack.held.unit = 9
    found = attack.aim(seen(5))
    assert found is not None
    assert attack.held.unit is None
    look = seen(5)
    unique = replace(look.foes[9], tier=0)  # a unique of no Herald's pack
    found = attack.aim(Observation(HERE, {**look.foes, 9: unique}))
    assert found is not None
    assert found.unit == 9
