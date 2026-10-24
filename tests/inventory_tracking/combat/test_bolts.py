"""Bolts in flight of the unread shooters (combat/bolts.py, combat/harm.py BOLTS_IN_FLIGHT; rca/2026-10-23/
dominus-burst-findings.md): the Dominus Herald pack's volleys of 3 bolts were priced at 4 points over a hold they took
1701 of 2943 from."""

import math

import pytest

from inventory_tracking.combat import bolts, harm as harm_module
from inventory_tracking.combat.harm import Hostile, Look, harm, harm_path


DOMINUS, BOLT = 636, 665
SHOOTER = (20.0, 0.0)


def volley(at_x: float) -> tuple:
    """Three bolts of the shooter at SHOOTER flying at the origin, `at_x` units out (owner, where, heading, class)."""
    heading = math.atan2(-SHOOTER[1], -SHOOTER[0])
    return tuple((1, (at_x, offset), heading, BOLT) for offset in (-0.3, 0.0, 0.3))


def look(missiles: tuple = ()) -> Look:
    hostile = Hostile(1, DOMINUS, SHOOTER, flags=16, modifiers=(29, 25, 27), tier=5, level=83, raised=3.85)
    return Look((hostile,), life=2943, missiles=missiles)


@pytest.fixture
def bolts_on(monkeypatch):
    monkeypatch.setattr(harm_module, 'BOLTS_IN_FLIGHT', True)


def test_a_bolt_meets_the_way_where_the_way_is_when_it_arrives():
    legs = (((0.0, 0.0), 1.5),)
    assert bolts.hit_time((10.0, 0.0), math.pi, 10.0, legs) == pytest.approx(1.0)
    assert bolts.hit_time((10.0, 0.0), math.pi, 10.0, (((0.0, 5.0), 1.5),)) is None  # out of its lane
    assert bolts.hit_time((10.0, 0.0), 0.0, 10.0, legs) is None  # flying away
    # Gone from its lane before it comes: a 3 unit side step done in 0.3 s, the bolt 0.6 s away
    assert bolts.hit_time((6.0, 0.0), math.pi, 10.0, (((0.0, 0.0), 0.3), ((0.0, 3.0), 1.2))) is None


def test_the_dominus_bolt_is_sized_by_its_stat_25_not_the_herald_boost_alone():
    plain = bolts.points(DOMINUS, 83, 16, (29, 25, 27), 5, 1.0)
    raised = bolts.points(DOMINUS, 83, 16, (29, 25, 27), 5, 3.85)
    kinds = {kind: (low, high) for kind, low, high in raised}
    assert set(kinds) == {'physical', 'magic'}
    assert sum(high for _, high in kinds.values()) > 700  # the take's largest bolt took 749
    assert sum(high for *_, high in raised) > 2 * sum(high for *_, high in plain)


def test_bolts_in_flight_at_a_hold_are_priced_and_a_step_out_of_their_lane_is_not(bolts_on):
    coming = look(volley(4.0))
    held = harm(coming, (0.0, 0.0), 1.5, 'battle')
    assert held.mean > 600  # three bolts of ~500, each landing with LANDS
    assert held.worst > 1200
    assert harm(look(), (0.0, 0.0), 1.5, 'battle').mean < 50  # the fitted rate alone, as before
    stepped = harm_path(coming, (((0.0, 0.0), 0.12, 'battle'), ((0.0, 5.0), 1.38, 'battle')))
    assert stepped.mean < 50


def test_off_the_bolts_are_their_fitted_rate_as_before(monkeypatch):
    monkeypatch.setattr(harm_module, 'BOLTS_IN_FLIGHT', False)
    assert harm(look(volley(4.0)), (0.0, 0.0), 1.5, 'battle').mean < 50


def test_dodges_are_square_to_the_lane_and_out_of_it():
    flying = [(at, heading) for _, at, heading, _ in volley(6.0)]
    places = bolts.dodges(flying, (0.0, 0.0))
    assert places
    for place in places:
        assert abs(place[0]) < 1e-6
        assert abs(place[1]) >= 5.0
        assert all(bolts.hit_time(at, heading, 10.1, ((place, 1.5),)) is None for at, heading in flying)
    assert bolts.dodges([((6.0, 10.0), 0.0)], (0.0, 0.0)) == []  # nothing comes at the character
