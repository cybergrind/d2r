"""The Baal fight (baal.py, constructed) and the Throne's waves (throne.py, recorded); rca/2026-10-14/baal-sim.md."""

import functools

import pytest

from inventory_tracking.combat.sim import baal as rules
from tests.inventory_tracking.scenarios.arena.mobs import SUMMONED
from tests.inventory_tracking.scenarios.arena.situations import baal, catalog, throne
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome


@functools.cache
def played(label: str, seed: int) -> Outcome:
    situation, presses = {name: (s, p) for name, s, p in baal.variants()}[label]
    return situation.play(presses, seed=seed, keep=True)


def test_both_are_in_the_catalog_with_today_and_new():
    found = catalog.catalog()
    assert [label for label, _, _ in found[baal.NAME].variants()] == [
        'attack mode alone: today', 'attack mode alone: new',
        'from the portal, KP_1 once: today', 'from the portal, KP_1 once: new',
    ]  # fmt: skip
    assert found[baal.NAME].kind == 'constructed'
    assert found[throne.NAME].kind == 'recorded'


def test_the_chamber_is_the_probes():
    situation = baal.stored()
    portal = baal.stored(None)
    ((unit, name),) = situation.bosses
    boss = next(mob for mob in situation.scene.mobs if mob.unit == unit)
    assert (name, boss.txt, boss.full) == ('Baal', 544, 293800.0)
    assert boss.at == pytest.approx((portal.scene.hero.at[0] - 38.0, portal.scene.hero.at[1] + 32.0))
    assert situation.scene.hero.area == 132
    assert sorted(mob.txt for mob in situation.scene.mobs if mob.ally) == [338, 361, 744]


@pytest.mark.xdist_group('situations: baal')
def test_attack_mode_kills_him_in_the_probes_time_and_his_casts_take_life():
    outcome = played('attack mode alone: new', 1)
    assert outcome == played('attack mode alone: new', 1)
    assert not outcome.dead
    killed = outcome.boss_dead['Baal']
    assert killed is not None
    assert 20.0 <= killed <= 45.0  # the probe: 23.5 to 40.0 s from his first sight
    fight = baal.fight(outcome)
    assert {'nova', 'cold missiles'} <= set(fight.by)
    assert fight.tentacles >= 2
    assert min(baal.PROBE_FALLS) <= fight.falls <= max(baal.PROBE_FALLS)
    stage = outcome.stage_  # type: ignore[attr-defined]
    raised = [mob for unit, mob in stage.cast.mobs.items() if unit > SUMMONED]
    assert all(mob.life <= 0 for mob in raised)  # gone with him, or their time up, or killed
    assert not stage.cast.summoned
    assert stage.cast.mates  # the companions drew some of his casts


@pytest.mark.xdist_group('situations: baal')
def test_the_pursuit_loop_steps_across_his_inferno():
    outcome = played('attack mode alone: new', 3)
    assert outcome.said_count("Stepping across Baal's inferno") >= 1
    assert outcome.boss_dead['Baal'] is not None
    assert not outcome.dead


@pytest.mark.xdist_group('situations: throne')
@pytest.mark.xfail(
    strict=False,
    reason=(
        'attack mode alone never walks back after a safety retreat (rca/2026-10-21/arena-failures-findings.md T1): '
        "waiting for the player's ruling"
    ),
)
def test_the_waves_come_as_the_take_saw_them_and_the_venom_lords_burn():
    situation = throne.stored()
    assert situation.source is not None
    assert situation.source['take'] == throne.TAKE
    assert not any(mob.txt in throne.THRONE for spawn in situation.spawns for mob in spawn.mobs)
    assert not any(mob.txt in throne.THRONE for mob in situation.scene.mobs)
    outcome = situation.play([], seed=1)
    assert not outcome.dead
    assert len(outcome.appeared) == len(situation.spawns) == 8  # five waves and the Council's hydras
    by = outcome.taken_by()
    assert by.get(('VenomLord', 'spell'), 0.0) > 0
    assert len(outcome.kills) > 40
    assert rules.CLONE not in {mob.txt for mob in situation.scene.mobs}
