"""READ_THROWS (combat/bolts.py, combat/harm.py, macros/safety.py `Safety.throws_read`; rca/2026-10-23/
death-canyon-findings.md): the tier 5 Herald pack of 15 Hell Slingers threw 8-12 javelins a second at the character's
place; the pooled shooter fit priced the pack at 2.8 life a second and the character died at 14:52:24.7."""

import math

import pytest

from inventory_tracking.combat import bolts
from inventory_tracking.combat.harm import Hostile, Look, harm
from inventory_tracking.macros import safety as safety_module


SLINGER, JAVELIN, SPEED = 376, 229, 23.5
HERALD_MODS = (28, 9, 6)


def slinger(unit: int, at: tuple[float, float], throws: float = 0.0) -> Hostile:
    return Hostile(
        unit, SLINGER, at, flags=16, modifiers=HERALD_MODS, tier=5, level=96, active=True, raised=3.85, throws=throws
    )


def javelins(owner: tuple[float, float], unit: int, count: int, at: tuple[float, float] = (0.0, 0.0)) -> tuple:
    """`count` javelins of `unit` let go from `owner` toward `at`, spread along the way: (owner, where, heading,
    class)."""
    heading = math.atan2(at[1] - owner[1], at[0] - owner[0])
    gap = math.dist(owner, at)
    steps = [gap * k / (count + 1) for k in range(1, count + 1)]
    return tuple(
        (unit, (owner[0] + math.cos(heading) * step, owner[1] + math.sin(heading) * step), heading, JAVELIN)
        for step in steps
    )


@pytest.fixture
def throws_on(monkeypatch):
    monkeypatch.setattr(bolts, 'READ_THROWS', True)


def test_the_slingers_javelin_is_read_only_with_the_switch(monkeypatch):
    assert bolts.thrown(SLINGER) == frozenset((JAVELIN,))  # monstats MissA1 pantherjav4
    monkeypatch.setattr(bolts, 'READ_THROWS', False)
    assert bolts.classes_of(SLINGER) == frozenset()
    assert bolts.speed_of(JAVELIN) == SPEED  # measured
    assert bolts.speed_of(226) is None  # pantherjav1: not priced off
    monkeypatch.setattr(bolts, 'READ_THROWS', True)
    assert bolts.classes_of(SLINGER) == frozenset((JAVELIN,))
    assert bolts.speed_of(226) == 20.0  # missiles.txt Vel
    assert bolts.classes_of(636) == frozenset((665,))  # the Dominus family's, as before


def test_the_throw_count_is_the_bolts_coming_and_their_flight():
    shooters = {unit: (20.0, float(y)) for unit, y in enumerate(range(-7, 8))}  # 15 at ~20 units
    flying = [(unit, at, heading) for unit, owner in shooters.items() for _, at, heading, _ in javelins(owner, unit, 1)]
    flight = sum(math.dist(owner, (0.0, 0.0)) for owner in shooters.values()) / SPEED
    coming, seconds = bolts.throw_count(flying, SPEED, shooters, [(0.0, 0.0)], 30.0)
    assert coming == 15
    assert seconds == pytest.approx(flight)  # 15 / flight: ~1.1 a second each, one javelin each in flight
    assert bolts.throw_count(flying, SPEED, shooters, [(0.0, 12.0)], 30.0)[0] < 15  # not all at that place
    # A shooter out of reach: neither its bolts nor its flight
    far = {**shooters, 99: (60.0, 0.0)}
    coming, seconds = bolts.throw_count([*flying, (99, (40.0, 0.0), math.pi)], SPEED, far, [(0.0, 0.0)], 30.0)
    assert coming == 15
    assert seconds == pytest.approx(flight)


def test_read_throws_price_the_pack_not_the_pooled_fit(throws_on):
    pack = tuple(slinger(unit, (20.0, float(y))) for unit, y in enumerate(range(-7, 8)))
    fitted = harm(Look(pack, life=2943), (0.0, 0.0), 2.0, 'battle')
    assert fitted.mean < 100  # the fit: 2.4 % of shots taking life
    read = tuple(slinger(h.unit, h.at, throws=0.58) for h in pack)
    priced = harm(Look(read, life=2943), (0.0, 0.0), 2.0, 'battle')
    # 15 x 0.58 a second x 1.15 s (2 s less a throw's 0.85 s flight from 20 units) x 0.95 to hit x the javelin's
    # 210-410 raw (stat 25 x3.85 over 50-85 at level 96)
    assert 2000 < priced.mean < 4500
    # A throw let go now lands after its flight: the bolts already in flight are `bolt_exposure`'s
    assert harm(Look(read, life=2943), (0.0, 0.0), 0.5, 'battle').mean < 100
    far = harm(Look(read, life=2943), (-60.0, 0.0), 2.0, 'battle')
    assert far.mean < priced.mean / 10  # out of reach, the walk to it first


def test_off_read_throws_are_not_priced(monkeypatch):
    monkeypatch.setattr(bolts, 'READ_THROWS', False)
    read = tuple(slinger(unit, (20.0, float(y)), throws=0.58) for unit, y in enumerate(range(-7, 8)))
    assert harm(Look(read, life=2943), (0.0, 0.0), 2.0, 'battle').mean < 100


def test_the_safety_reads_the_rate_and_holds_it_after_a_hop(throws_on):
    safety = safety_module.Safety()
    pack = tuple(slinger(unit, (20.0, float(y))) for unit, y in enumerate(range(-7, 8)))
    flying = tuple(m for h in pack for m in javelins(h.at, h.unit, 1))
    seen = safety.throws_read(Look(pack, life=2943, missiles=flying), (0.0, 0.0), 10.0)
    rate = seen.hostiles[0].throws
    assert rate > 0.5
    assert all(h.throws == rate for h in seen.hostiles)
    # A hop away: the javelins in flight go to the old place (still read: the last look's place), then none come
    moved = safety.throws_read(Look(pack, life=2943, missiles=flying), (0.0, 12.0), 10.4)
    assert moved.hostiles[0].throws == pytest.approx(rate, rel=0.1)
    later = safety.throws_read(Look(pack, life=2943), (0.0, 12.0), 12.0)
    # One look with none coming: the rate over the window's looks, two of three with the pack's bolts
    assert rate / 2 < later.hostiles[0].throws < rate
    gone = safety.throws_read(Look(pack, life=2943), (0.0, 12.0), 10.0 + safety_module.THROWS_HOLD + 1.0)
    assert gone.hostiles[0].throws == 0.0


def test_off_the_safety_reads_no_rate(monkeypatch):
    monkeypatch.setattr(bolts, 'READ_THROWS', False)
    pack = (slinger(1, (20.0, 0.0)),)
    seen = Look(pack, life=2943, missiles=javelins((20.0, 0.0), 1, 2))
    assert safety_module.Safety().throws_read(seen, (0.0, 0.0), 1.0) is seen


def test_a_companion_on_the_line_takes_the_throw():
    shooter, place = (20.0, 0.0), (0.0, 0.0)
    assert bolts.covered([(0.6, 0.0)], shooter, place) == bolts.COVER_LEAK  # the bound demon on the character's place
    assert bolts.covered([(10.0, 1.0)], shooter, place) == bolts.COVER_LEAK  # on the way
    assert bolts.covered([(10.0, 4.0)], shooter, place) == 1.0  # beside the way
    assert bolts.covered([(-4.0, 0.0)], shooter, place) == 1.0  # behind the character
    assert bolts.covered([], shooter, place) == 1.0


def test_read_throws_at_a_covered_place_are_the_leak(throws_on):
    read = tuple(slinger(unit, (20.0, float(y)), throws=0.58) for unit, y in enumerate(range(-7, 8)))
    open_ = harm(Look(read, life=2943), (0.0, 0.0), 2.0, 'battle').mean
    covered = harm(Look(read, life=2943, cover=((0.6, 0.0), (0.0, 0.8))), (0.0, 0.0), 2.0, 'battle').mean
    assert covered < open_ * bolts.COVER_LEAK * 1.5


def test_the_companions_near_come_along_as_cover():
    cover = ((0.6, 0.0), (15.0, 0.0))
    assert bolts.cover_at(cover, (0.0, 0.0), (0.0, 0.0)) == cover
    moved = bolts.cover_at(cover, (0.0, 0.0), (-20.0, 0.0))
    assert moved[0] == pytest.approx((-19.4, 0.0))  # within TAKEN_ALONG: along, to the same side
    assert moved[1] == (15.0, 0.0)  # farther: left where it stands


def test_the_escapes_leave_the_throwers_reach():
    pack = tuple(slinger(unit, (20.0, float(y)), throws=0.58) for unit, y in enumerate(range(-7, 8)))
    places = safety_module.out_of_throws((0.0, 0.0), Look(pack, life=2943))
    assert places
    for place in places:
        assert min(math.dist(place, h.at) for h in pack) >= safety_module.SHOT_REACH + safety_module.THROWS_CLEAR
    assert safety_module.out_of_throws((0.0, 0.0), Look((slinger(1, (20.0, 0.0)),), life=2943)) == []
