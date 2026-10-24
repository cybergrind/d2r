"""The death in the Canyon of the Magi (canyon_death.py; rca/2026-10-23/death-canyon-findings.md): the scene plays the
tier 5 Hell Slinger pack's javelins in the take's walls; with combat/bolts.py READ_THROWS the character keeps out of
their reach instead of standing in their lines (the player: "we must not die or we lose exp and our gear")."""

import pytest

from inventory_tracking.combat import bolts
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import canyon_death
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON


SEEDS = tuple(range(1, 21))


def test_the_scene_carries_the_take_s_walls_stat_25_and_the_slinger_pack():
    situation = canyon_death.stored()
    assert situation.scene.ground
    assert situation.capped
    pack = [mob for spawn in situation.spawns for mob in spawn.mobs if mob.txt == canyon_death.SLINGER]
    assert len(pack) == 15
    assert all(mob.tier == 5 and 9 in mob.mods for mob in pack)  # tier 5, Fire Enchanted
    rows = situation.damage_percent
    assert rows is not None
    assert all(any(value == 285.0 for _, value in rows[mob.unit]) for mob in pack)  # stat 25 on every one
    mercenary = next(mob for mob in situation.scene.mobs if mob.txt == canyon_death.MERCENARY)
    assert mercenary.life == mercenary.full


@pytest.mark.slow
def test_off_the_pack_kills_as_the_take_did_and_on_no_play_dies(monkeypatch):
    # The companions as in the game: a Teleport takes them along and the merc takes blows; the demon and the merc fall
    # when they fell in the take (2026-10-23; left behind, the pricing's cover is not the world's)
    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    monkeypatch.setattr(game, 'MERC_HURT', True)
    monkeypatch.setattr(bolts, 'READ_THROWS', False)
    off = [canyon_death.play(ALL_ON, seed, lap=0.02)[0] for seed in SEEDS]
    monkeypatch.setattr(bolts, 'READ_THROWS', True)
    on = [canyon_death.play(ALL_ON, seed, lap=0.02)[0] for seed in SEEDS]
    assert sum(m.dead for m in off) >= 1  # 2 of 20 on 2026-10-23, kept alive by 6.3 Rejuvenations a play
    assert not [m.seed for m in on if m.dead]
    assert sum(m.rejuvenations for m in on) < sum(m.rejuvenations for m in off)
