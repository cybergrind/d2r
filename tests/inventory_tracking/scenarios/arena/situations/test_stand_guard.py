"""The stand after a stop of the loop's own, the stand guard off and on (stand_guard.py; macros/guard.py;
rca/2026-10-22/guard-findings.md): off, the 20:48 stand in the Arcane Sanctuary takes its damage and the dangerous
fights kill; on, the guard fights back in place and no seed dies."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations.stand_guard import NAME, STANDS, played, stand, stored


TWENTY = tuple(range(1, 21))


def test_the_stand_is_cut_with_the_walls_the_cap_and_no_press():
    situation = stored(NAME)
    assert situation.scene.ground
    assert situation.capped
    assert situation.aware == 35.0
    assert situation.scene.hero.area == 74
    standing = stand(NAME)
    assert standing.presses == ()
    assert not standing.attack


def test_the_2048_stand_takes_hits_with_the_guard_off_and_none_with_it_on():
    off, on = played(NAME, False, (1,)), played(NAME, True, (1,))
    assert off[0].taken > 500  # the stand under fire, as the take had it (2943 -> 2779 in its first minute)
    assert off[0].fights == 0
    assert on[0].fights >= 1
    assert on[0].taken < off[0].taken / 4
    assert not on[0].dead


@pytest.mark.slow
@pytest.mark.parametrize('name', STANDS)
def test_with_the_guard_on_no_stand_dies(name):
    # Off, fane-death-24 lost 14 of 20 seeds, fane-death-20 13, danger-area89-0428 2 (the findings' table)
    plays = played(name, True, TWENTY)
    assert not [play.seed for play in plays if play.dead], name
    assert all(play.fights >= 1 for play in plays if play.taken), name  # a hit is always fought back
