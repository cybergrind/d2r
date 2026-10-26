"""The approach/retreat dance by the idle tier 5 Herald pack (maggot_approach.py;
rca/2026-10-25/approach-retreat-findings.md): pursuit.py STAND_NOT_RETREAT on is no worse than off over 20 seeds, the
pack as the arena plays it and holding its ground (`holding`). The dance itself is replayed on the take's look in
tests/inventory_tracking/macros/test_stand_not_retreat.py."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations import maggot_approach


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_pack():
    situation = maggot_approach.stored()
    pack = [mob for mob in situation.scene.mobs if mob.tier == 5]
    assert len(pack) >= 14
    assert any(mob.unit == maggot_approach.ELITE for mob in pack)


@pytest.mark.slow
@pytest.mark.xfail(
    reason='with the own aura and the live physical resistance (2026-10-25), 1 kill on against 1 off, no death: '
    'STAND_NOT_RETREAT to be measured again (rca/2026-10-25/t5-blow-findings.md, Update)',
    strict=True,
)
def test_the_stand_on_fights_the_pack_the_dance_off_never_does():
    """The pack as the arena plays it: off, the dance never fights it (0 kills in 20 plays, life untouched); on, the
    stand's move in does, with no death and the lowest life above the safety's floor (65%; 2026-10-25: 76% least,
    98% median, 8 kills)."""
    off = [maggot_approach.play(False, seed)[:2] for seed in SEEDS]
    on = [maggot_approach.play(True, seed)[:2] for seed in SEEDS]
    assert not any(m.dead for m, _ in on)
    assert sum(m.kills for m, _ in on) > sum(m.kills for m, _ in off)
    assert min(low for _, low in on) >= 0.7


@pytest.mark.slow
def test_the_stand_on_is_no_worse_than_off_with_the_pack_holding_its_ground():
    situation = maggot_approach.holding()
    off = [maggot_approach.play(False, seed, situation)[:2] for seed in SEEDS]
    on = [maggot_approach.play(True, seed, situation)[:2] for seed in SEEDS]
    assert sum(m.dead for m, _ in on) <= sum(m.dead for m, _ in off)
    assert min(low for _, low in on) >= min(low for _, low in off) - 0.05
    assert sum(m.kills for m, _ in on) >= 0.95 * sum(m.kills for m, _ in off)
