"""A doll Herald is killed before Battle Orders is renewed or rebuffed (macros/cta.py DOLL_HERALD_FIRST, hunt.py
DOLL_HERALD_MARK, combat/threats/dolls.py `herald_doll`). The player, 2026-10-22, of danger-durance-1956: "you just
aggro doll herald with death mark and then kill him VERY fast, because it has relatively low life even T5"."""

from inventory_tracking.combat.threats import dolls
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import cta
from inventory_tracking.macros.build import BuffFacts
from tests.inventory_tracking.macros.fakes import player, world


DURANCE_2 = 101
STYGIAN_DOLL, NOBODY, UNIQUE, MINION = 216, 0xFFFFFFFF, 0x08, 0x10


def doll(unit: int, x: float, flags: int = UNIQUE, tier: int = 1) -> Monster:
    return Monster(unit, STYGIAN_DOLL, 1, x, 5000.0, NOBODY, flags, life=3, max_life=128, tier=tier)


HERALD = doll(1, 5025.0)  # 25 off, as the seed 9 killer at the cut
MINION_DOLL = doll(2, 5010.0, MINION)


def seen(*foes: Monster):
    return world(DURANCE_2, player=player(DURANCE_2, battle_orders=True), monsters=foes)


def test_a_doll_herald_is_told_from_its_minions_and_other_types() -> None:
    assert dolls.herald_doll(HERALD)
    assert not dolls.herald_doll(MINION_DOLL)  # a minion carries the tier but is no leader
    assert not dolls.herald_doll(doll(3, 5025.0, tier=0))  # a unique doll, no Herald
    assert not dolls.herald_doll(Monster(4, 610, 1, 5025.0, 5000.0, NOBODY, UNIQUE, tier=5))  # a Slinger Herald


def test_battle_orders_waits_for_the_doll_herald_s_kill_when_its_time_left_allows() -> None:
    at = seen(HERALD, MINION_DOLL)
    assert cta.doll_first(at, (HERALD, MINION_DOLL), True, None) == 'a doll Herald 25 off: killed first'
    assert cta.doll_first(at, (HERALD,), True, 90.0) is not None
    assert cta.doll_first(at, (HERALD,), True, cta.DOLL_KILL_SECONDS) is None  # about to run out: the rebuff's rules
    assert cta.doll_first(at, (HERALD,), False, 0.0) is None  # run out
    far = doll(5, 5000.0 + cta.DOLL_HERALD_NEAR + 1)
    assert cta.doll_first(seen(far), (far,), True, None) is None
    assert cta.renew_orders(BuffFacts(at, 100.0, (HERALD,), hurt=lambda: False), None) is None  # not even in the quiet


def test_with_the_switch_off_battle_orders_goes_as_before(monkeypatch) -> None:
    monkeypatch.setattr(cta, 'DOLL_HERALD_FIRST', False)
    at = seen(HERALD, MINION_DOLL)
    assert cta.doll_first(at, (HERALD,), True, None) is None
    assert cta.renew_orders(BuffFacts(at, 100.0, (HERALD,), hurt=lambda: False), None) is not None
