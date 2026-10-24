"""The death in Flayer Dungeon Level 1 (manaburn_death.py; rca/2026-10-23/death-manaburn-findings.md): the scene plays
the take's mana (costs, regeneration, the Dark Shapes' burns, the Rejuvenation's fill); with combat/threats/
drain_escape.py MANA_ESCAPE the character leaves the drainers before the pool is gone instead of standing among them
(the player: "we must not die or we lose exp and our gear")."""

import pytest

from inventory_tracking.combat.threats import drain_escape
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import manaburn_death


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_take_s_dark_shapes_and_the_herald_pack():
    situation = manaburn_death.stored()
    assert situation.scene.ground
    assert game.MANA_SHOWN in situation.rules
    assert situation.scene.hero.max_mana == 745.0
    pack = [mob for spawn in situation.spawns for mob in spawn.mobs if mob.txt == manaburn_death.WRAITH and mob.tier]
    assert len(pack) >= 15
    assert all(mob.tier == 5 and 25 in mob.mods for mob in pack)  # tier 5, Mana Burn
    plain = [mob for mob in situation.scene.mobs if mob.txt == manaburn_death.WRAITH and 25 not in mob.mods]
    assert plain  # the plain Dark Shapes that burnt the pool in the take


@pytest.mark.slow
def test_off_the_pool_burns_out_and_some_plays_die_and_on_none_does(monkeypatch):
    # The companions as in the game: a Teleport takes them along and the merc takes blows (2026-10-23)
    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    monkeypatch.setattr(game, 'MERC_HURT', True)
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    off = [manaburn_death.summary(seed) for seed in SEEDS]
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)
    on = [manaburn_death.summary(seed) for seed in SEEDS]
    assert sum(row['dead'] is not None for row in off) >= 3  # 10 of 20 on 2026-10-23 (12 of 30)
    assert not [row['seed'] for row in on if row['dead'] is not None]  # 0 of 20 (4 of 50: seeds 22, 30, 35, 49)
    assert sum(row['contact'] for row in on) < sum(row['contact'] for row in off) / 2
    assert sorted(row['low'] for row in on)[10] > sorted(row['low'] for row in off)[10]  # 0.84 against 0.24
