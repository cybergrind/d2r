"""The helm by the idle tier 5 Herald pack (harem_helm.py; rca/2026-10-25/pickup-veto-pingpong-findings.md):
macros/hunt.py QUIET_HOLD on is no worse than off over 20 seeds, the pack as the arena plays it and holding its
ground (`holding`). The flip itself is replayed on the take's look in
tests/inventory_tracking/macros/test_quiet_hold_replay.py."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations import harem_helm


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_pack_and_the_helm():
    situation = harem_helm.stored()
    pack = [mob for mob in situation.scene.mobs if mob.tier == 5]
    assert len(pack) == 14  # the Herald and 13 of his pack
    assert any(mob.unit == harem_helm.HERALD for mob in pack)
    assert [(drop.code, drop.at) for drop in situation.scene.drops] == [(harem_helm.HELM_CODE, harem_helm.HELM_AT)]


@pytest.mark.slow
@pytest.mark.parametrize('holding', [False, True])
def test_the_hold_on_is_no_worse_than_off(holding):
    situation = harem_helm.holding() if holding else None
    off = [harem_helm.play(False, seed, situation)[:2] for seed in SEEDS]
    on = [harem_helm.play(True, seed, situation)[:2] for seed in SEEDS]
    assert sum(m.dead for m, _ in on) <= sum(m.dead for m, _ in off)
    assert min(low for _, low in on) >= min(low for _, low in off) - 0.05
    assert sum(m.kills for m, _ in on) >= 0.9 * sum(m.kills for m, _ in off)
