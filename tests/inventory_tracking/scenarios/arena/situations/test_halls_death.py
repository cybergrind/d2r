"""The death in Halls of the Dead Level 2 (halls_death.py; rca/2026-10-23/death-halls-findings.md): the reviver's goal
took over a guarded potion's fight with no route stage, and each of the loop's legs handed its press to the pickup step
or ended under a tier 5 pack. With pursuit.py FIGHT_BEFORE_END, or hunting/revive.py REVIVER_OWN_RUN, the run fights
instead (the player: "we have lost almost ALL EXPERIENCE ... our top most prioritiy: exp/hour"). macros/pickup.py
PACK_GOLD_WAIT (2026-10-24, the game-5 agent's) closes it a third way, the gold held while the pack stands: each arm
names all three, so the off arm is the 23:31 code (2026-10-24: with PACK_GOLD_WAIT live the off arm died no more)."""

import pytest

from inventory_tracking.macros import pickup, pursuit
from inventory_tracking.macros.hunting import revive
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import halls_death
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_pack_its_reviver_the_short_belt_and_the_drops():
    situation = halls_death.stored()
    mobs = situation.scene.mobs + [mob for spawn in situation.spawns for mob in spawn.mobs]
    pack = [mob for mob in mobs if mob.tier == 5]
    assert len(pack) == 15  # the Herald and 14 minions
    assert any(mob.unit == halls_death.REVIVER for mob in mobs)
    assert situation.scene.hero.belt == halls_death.BELT
    assert len(situation.scene.drops) == len(halls_death.DROPS)


def plays(monkeypatch, fight: bool, own: bool, gold: bool = False) -> list:
    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    monkeypatch.setattr(game, 'MERC_HURT', True)
    monkeypatch.setattr(pursuit, 'FIGHT_BEFORE_END', fight)
    monkeypatch.setattr(revive, 'REVIVER_OWN_RUN', own)
    monkeypatch.setattr(pickup, 'PACK_GOLD_WAIT', gold)
    return [halls_death.play(ALL_ON, seed)[0] for seed in SEEDS]


@pytest.mark.slow
def test_off_the_legs_die_and_any_fix_on_no_play_dies(monkeypatch):
    off = plays(monkeypatch, fight=False, own=False)
    assert sum(m.dead for m in off) >= 5
    assert not [m.seed for m in plays(monkeypatch, fight=True, own=False) if m.dead]
    assert not [m.seed for m in plays(monkeypatch, fight=False, own=True) if m.dead]
    assert not [m.seed for m in plays(monkeypatch, fight=False, own=False, gold=True) if m.dead]
