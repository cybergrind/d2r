"""The Dominus Herald burst (dominus.py; rca/2026-10-23/dominus-burst-findings.md): the scene plays the take's bolts,
and with combat/harm.py BOLTS_IN_FLIGHT the character steps out of their lane instead of standing under them."""

import pytest

from inventory_tracking.combat import harm as harm_module
from tests.inventory_tracking.scenarios.arena.situations import dominus
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_take_s_walls_stat_25_and_the_dominus_pack():
    situation = dominus.stored()
    assert situation.scene.ground
    assert situation.capped
    assert situation.damage_percent
    pack = [mob for mob in situation.scene.mobs if mob.txt == dominus.DOMINUS]
    assert len(pack) >= 10
    assert all(29 in mob.mods for mob in pack)  # Multiple Shots


@pytest.mark.slow
def test_off_the_bolts_take_the_life_as_the_take_did_and_on_none_lands_deep(monkeypatch):
    monkeypatch.setattr(harm_module, 'BOLTS_IN_FLIGHT', False)
    off = [dominus.play(ALL_ON, seed) for seed in SEEDS]
    monkeypatch.setattr(harm_module, 'BOLTS_IN_FLIGHT', True)
    on = [dominus.play(ALL_ON, seed) for seed in SEEDS]
    assert not [m.seed for m, _ in off + on if m.dead]
    off_lows = sorted(dip for _, dip in off)
    assert off_lows[2] <= dominus.RECORDED_LOW <= off_lows[-3]  # the recording inside the off plays' 10-90 %
    assert min(dip for _, dip in on) > max(0.6, min(off_lows))
    assert sum(m.rejuvenations for m, _ in on) < sum(m.rejuvenations for m, _ in off)
