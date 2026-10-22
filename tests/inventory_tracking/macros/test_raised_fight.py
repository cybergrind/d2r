"""The safety's round-5 rules (2026-10-22, rca/2026-10-21/death-findings.md "Round 5"): a hostile seen to move is
active whatever its mode (MOVED_ACTIVE), the spread harm of an aura-raised fight still names a hostile to keep in
reach (RAISED_KEEP), and the rollouts' veto drop (REJUV_REACTS, off) copies the settings without breaking them."""

from dataclasses import replace
from typing import Any

from inventory_tracking.combat.harm import Harm, Hostile, Look, Protection
from inventory_tracking.combat.policy import Foe, Observation
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import safety as module
from inventory_tracking.macros.safety import Safety, SafetySettings


def walker(x: float, mode: int = 1) -> Monster:
    return Monster(9, 47, mode, x, 0.0, 0xFFFFFFFF, flags=8, life=900, max_life=1000)


def test_a_hostile_seen_to_move_is_active_for_a_second_whatever_its_mode(monkeypatch) -> None:
    """fane-death-20 (drawn, seed 5, pursuit): the unique ran in from 20 to 2.7 in mode 1; read as neutral it was
    priced at nothing behind a wall. Moved a unit or more between looks, it counts as active MOVED_SECONDS."""
    safety = Safety()
    assert safety.moving([walker(20.0)], 1.0) == frozenset()  # first seen: not known to move
    assert safety.moving([walker(10.0)], 1.4) == {9}
    assert safety.moving([walker(10.0)], 2.0) == {9}  # still within MOVED_SECONDS of the move
    assert safety.moving([walker(10.0)], 2.5) == frozenset()
    assert safety.moving([walker(10.5)], 2.6) == frozenset()  # under MOVED_UNITS
    monkeypatch.setattr(module, 'MOVED_ACTIVE', False)
    assert Safety().moving([walker(20.0)], 1.0) == frozenset()
    off = Safety()
    off.moving([walker(20.0)], 1.0)
    assert off.moving([walker(10.0)], 1.4) == frozenset()


def test_a_spread_harm_names_the_hostile_that_brings_the_most_in_a_raised_fight(monkeypatch) -> None:
    """RAISED_KEEP: the capped t5 Bramble Hulks (seed 6, 12.04 s) spread the harm over the pack, so `keeper` named
    none and every retreat landed out of the strike's reach; `spread` names the one that brings the most."""
    pack = Look(tuple(Hostile(unit, 345, (10.0, unit), raised=2.9) for unit in range(10, 15)))
    seen = Observation((0.0, 0.0), {h.unit: Foe(h.txt, h.at, 1000.0) for h in pack.hostiles})
    harm = Harm(100, 200, by=((10, 20.0), (11, 30.0), (12, 20.0), (13, 20.0), (14, 10.0)))
    assert module.keeper(pack, seen, harm) is None
    assert module.keeper(pack, seen, harm, spread=True) == 11
    assert module.raised_fight(pack)
    assert not module.raised_fight(Look(tuple(Hostile(h.unit, h.txt, h.at) for h in pack.hostiles)))


def test_the_veto_drop_copies_the_settings_once() -> None:
    """REJUV_REACTS' `no_veto` (off since 2026-10-22: the Fane's lowest life fell to 11%) copies the pydantic
    settings with `with_overrides` (a dataclasses.replace crashed 22 plays at 13:01) and keeps the copy."""
    safety, settings = Safety(), SafetySettings()
    copied = safety.no_veto(settings)
    assert copied.veto_share == 100.0
    assert settings.veto_share != 100.0
    assert safety.no_veto(settings) is copied
    assert safety.no_veto(SafetySettings()) is not copied


def priced(*hostiles: Hostile, life: float = 2500.0, reach: float = 22.0, left: float = 1000.0) -> Any:
    """The parts of a `Pricing` that `kill_first` and `cast_reach` read: the look, the observation, the place and the
    strike's reach."""
    from types import SimpleNamespace

    look = Look(hostiles, life=life)
    seen = Observation((0.0, 0.0), {h.unit: Foe(h.txt, h.at, left, elite=bool(h.flags & 8)) for h in hostiles})
    return SimpleNamespace(look=look, seen=seen, here=(0.0, 0.0), attack=SimpleNamespace(reach=reach))


NIGHT_LORD = 47  # the Fane's unique of the Might pack: a table blow of 300, 1727 at x5.75 (combat/harm.py `most_blow`)


def test_a_one_shot_unit_that_dies_before_it_reaches_is_killed_ahead_of_the_rebuff(monkeypatch) -> None:
    """KILL_FIRST: its life to come over KILL_RATE under its walk to the character's reach, its blow over the life;
    not when it would reach first, nor when its blow does not take the life; never with the switch off."""
    lord = Hostile(1, NIGHT_LORD, (20.0, 0.0), flags=8, tier=2, raised=5.75)
    p = priced(lord, life=1500.0, left=1000.0)  # 2000 points at 8800 a second: 0.23 s; its walk of 16 at 8.8: 1.8 s
    assert module.kill_first(p, None) is not None
    assert module.kill_first(p, 0.1) is None  # Battle Orders ends before the kill
    assert module.kill_first(priced(lord, life=1500.0, left=40000.0), None) is None  # 9 s to kill: it reaches first
    assert module.kill_first(priced(lord, life=2500.0), None) is None  # its blow does not take the life
    assert module.kill_first(priced(Hostile(1, NIGHT_LORD, (30.0, 0.0), raised=5.75), life=1500.0), None) is None
    monkeypatch.setattr(module, 'KILL_FIRST', False)
    assert module.kill_first(p, None) is None


def test_a_cast_in_place_is_barred_by_blows_that_can_come_within_its_time(monkeypatch) -> None:
    """CAST_REACH: the most blows together of the melee hostiles within REACH_UNITS plus their walk in CAST_SECONDS
    against the life; not when they do not take it, nor from beyond the walk (the rebuff's landing is clear of it)."""
    lord = Hostile(1, NIGHT_LORD, (12.0, 0.0), flags=8, tier=2, raised=5.75)  # 4 + 8.8 x 1 = 12.8 of reach

    def barred(*hostiles: Hostile, life: float) -> str | None:
        return module.cast_reach(hostiles, (0.0, 0.0), Protection(), life)

    assert barred(lord, life=1500.0) is not None
    assert barred(lord, life=2500.0) is None
    assert barred(replace(lord, at=(14.0, 0.0)), life=1500.0) is None  # the rebuff's landing, REBUFF_CLEAR off
    assert barred(lord, replace(lord, unit=2, at=(0.0, 10.0)), life=2500.0) is not None  # together they take it
    monkeypatch.setattr(module, 'CAST_REACH', False)
    assert barred(lord, life=1500.0) is None


def test_the_safety_bars_the_swap_from_the_world_read_at_the_cast(monkeypatch) -> None:
    """`Safety.cast_threat` (CAST_REACH), asked fresh by macros/cta.py `threat_hold`: the Fane's Night Lord unique
    with Might (stat 25, the Fane's 190) 8 units off at Kurast Bazaar's terrorized level 96 bars the swap at 1500
    life; 30 off, or with 2943 life, it does not; no life read, no bar."""
    from tests.inventory_tracking.macros.fakes import world

    lord = Monster(9, NIGHT_LORD, 2, 5008.0, 5000.0, 0xFFFFFFFF, flags=8, life=900, max_life=1000, tier=2)
    lord = replace(lord, damage_percent=475)
    safety = Safety()
    near = world(80, monsters=(lord,))
    assert safety.cast_threat(near, 1500.0) is not None
    assert safety.cast_threat(near, 2943.0) is None
    assert safety.cast_threat(world(80, monsters=(replace(lord, x=5030.0),)), 1500.0) is None
    assert safety.cast_threat(near, None) is None
    monkeypatch.setattr(module, 'CAST_REACH', False)
    assert safety.cast_threat(near, 1500.0) is None


def test_a_neutral_unit_with_no_line_prices_when_it_can_walk_to_the_place(monkeypatch) -> None:
    """NEAR_WAKES (fane-death-20, seed 7, pursuit: a landing beside the idle Night Lord priced at nothing): a neutral
    hostile with no line to the place prices as any other within its walk of WAKE_SECONDS; a far one at nothing."""
    from inventory_tracking.combat import harm as harm_module

    def wall(point) -> bool:
        return 4.0 < point[0] < 5.0  # a wall between the place and the unit

    settings = SafetySettings()
    near = Look((Hostile(1, NIGHT_LORD, (8.0, 0.0), flags=8, raised=5.75),), life=2500.0, blocked=wall)
    far = Look((Hostile(1, NIGHT_LORD, (30.0, 0.0), flags=8, raised=5.75),), life=2500.0, blocked=wall)
    assert harm_module.harm(near, (0.0, 0.0), 2.0, 'battle', settings).worst > 0
    assert harm_module.harm(far, (0.0, 0.0), 2.0, 'battle', settings).worst == 0
    monkeypatch.setattr(harm_module, 'NEAR_WAKES', False)
    near = replace(near, memo={})
    assert harm_module.harm(near, (0.0, 0.0), 2.0, 'battle', settings).worst == 0


def test_a_units_raise_is_the_most_read_on_it_within_seconds(monkeypatch) -> None:
    """RAISE_KEEP: the Fane's unique Night Lord read stat 25 at 285 or 475 as a Concentration minion came and went; its
    raise is the most read within RAISE_SECONDS, then the reads age out."""
    safety = Safety()
    lord = replace(walker(5000.0), damage_percent=475)
    safety.raise_clock = 1.0
    assert safety.unit_raise(lord) == 5.75
    safety.raise_clock = 3.0
    assert safety.unit_raise(replace(lord, damage_percent=285)) == 5.75
    safety.raise_clock = 7.0
    assert safety.unit_raise(replace(lord, damage_percent=285)) == 3.85
    monkeypatch.setattr(module, 'RAISE_KEEP', False)
    safety.raise_clock = 7.5
    assert Safety().unit_raise(replace(lord, damage_percent=285)) == 3.85


def test_the_strike_bout_yields_where_holding_is_barred(monkeypatch) -> None:
    """BOUT_REACH (fane-death-24, seed 16, pursuit: 1.76 s of bout with no look while the unique walked in): the
    blows that come within REACH_UNITS in REACH_SECONDS, against the life; a farther one does not stop the bout."""
    lord = Hostile(1, NIGHT_LORD, (8.0, 0.0), flags=8, tier=2, raised=5.75)  # 4 + 8.8 x 0.5 = 8.4

    def bout(*hostiles: Hostile, life: float) -> str | None:
        return module.cast_reach(hostiles, (0.0, 0.0), Protection(), life, bout=True)

    assert bout(lord, life=1500.0) is not None
    assert bout(replace(lord, at=(12.0, 0.0)), life=1500.0) is None  # within the cast's reach, not the bout's
    assert module.cast_reach((replace(lord, at=(12.0, 0.0)),), (0.0, 0.0), Protection(), 1500.0) is not None
    monkeypatch.setattr(module, 'BOUT_REACH', False)
    assert bout(lord, life=1500.0) is None


def test_an_escape_landing_beside_a_live_doll_gives_way_to_one_that_lands_clear(monkeypatch) -> None:
    """DOLL_ESCAPES (danger-durance-1956: a retreat jumped from 15.6 to 6.6 units of a Stygian Doll walking in, which
    died on arrival 2.8 off): with DOLL_LAND off, an escape's jump within `dolls.land_units` of a live doll is soft,
    barred by `doll_escapes` when another escape lands clear; the asked move is not touched."""
    from types import SimpleNamespace

    from inventory_tracking.combat.threats import dolls
    from inventory_tracking.macros.build import Step
    from inventory_tracking.macros.skills import TELEPORT

    doll = Hostile(1, 216, (20.0, 0.0), mode=2)  # bonefetish5, a Stygian Doll (exploding.json), walking
    pricing: Any = SimpleNamespace(
        facts=SimpleNamespace(attacking=True), look=Look((doll,)), here=(0.0, 0.0), patient=False, close=False,
        soft=[], candidates=[],
    )  # fmt: skip
    near = Step((14.0, 0.0), TELEPORT)
    assert not dolls.DOLL_LAND
    module.Pricing.doll_landing(pricing, near, 0.3, Harm(0, 0), escape=True, asked=False)
    assert pricing.soft == [0]
    pricing.soft = []
    assert module.Pricing.doll_landing(pricing, near, 0.3, Harm(0, 0), escape=False, asked=True).barred is None
    away = Step((-30.0, 0.0), TELEPORT)
    clear = module.Pricing.doll_landing(pricing, away, 0.3, Harm(0, 0), escape=True, asked=False)
    assert pricing.soft == []
    assert clear.barred is None
    monkeypatch.setattr(module, 'DOLL_ESCAPES', False)
    module.Pricing.doll_landing(pricing, near, 0.3, Harm(0, 0), escape=True, asked=False)
    assert pricing.soft == []
