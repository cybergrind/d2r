"""The arena's blows as the game's (rca/2026-10-25/t5-blow-findings.md): the holder's own aura raises it (mobs.py
`_raised`), a capped blow is the fitted spread's cut at the game's most (`bounded`), every set lets the live physical
share through and shows it (game.py PHYSICAL_THROUGH), and the tier 5 Herald scene is capped (situations/herald.py)."""

import random

import pytest

from inventory_tracking.combat.sim.monsters import MELEE, Blow
from tests.inventory_tracking.scenarios.arena.game import PHYSICAL_THROUGH, Arena
from tests.inventory_tracking.scenarios.arena.mobs import AURA_FACTOR, AURA_MOD, AURA_RAISE, Mobs
from tests.inventory_tracking.scenarios.arena.situations import herald
from tests.inventory_tracking.scenarios.arena.test_mobs import GHOUL, HELL_BOVINE, mob, scene


STAT_PHYSICAL = 36  # macros/safety.py RESISTS: damage resist


def test_an_aura_raises_its_holders_own_blows_and_shows_on_it():
    # In the takes of 10-23..25 the unique's stat 25 equals its minions' in all 27 tier 5 packs read with both
    mobs = Mobs(scene([mob(1, GHOUL, 2.0, 0.0, mods=(AURA_MOD,)), mob(2, HELL_BOVINE, 2.0, 3.0)]), random.Random(1))
    assert mobs._raised(2) == pytest.approx(AURA_FACTOR)  # a neighbour
    assert mobs._raised(1) == pytest.approx(AURA_FACTOR)  # the holder
    assert mobs.shown_percent(1) == round(AURA_RAISE)  # what the safety reads as stat 25


def test_a_capped_blow_is_the_fitted_spreads_cut_at_its_most():
    # Not the uniform roll: the takes' clean tier 5 minion blows land at 0.38-0.76 of their priced most
    mobs = Mobs(scene([mob(1, HELL_BOVINE, 2.0, 0.0)]), random.Random(2))
    most = mobs.pack.walkers[1].traits.damage[1]
    huge = Blow(frame=0, unit=1, target=0, damage=most * 4.0, kind=MELEE, parts={})  # the fitted spread's tail
    small = Blow(frame=0, unit=1, target=0, damage=most * 0.4, kind=MELEE, parts={})
    assert [blow.damage for blow in mobs.bounded([huge, small])] == pytest.approx([most, most * 0.4])


def test_a_set_lets_the_live_physical_share_through_and_shows_it():
    arena = Arena(herald.t5_hulks().scene)  # sets with known raw resistances (fla/uit, 6cs/wa3), physical 0.9 in them
    assert all(resist['physical'] == pytest.approx(PHYSICAL_THROUGH) for resist in arena.resists)
    arena.show()
    assert dict(arena.loot.stats).get(STAT_PHYSICAL) == round((1 - PHYSICAL_THROUGH) * 100)


def test_the_t5_hulk_scene_plays_the_games_blows():
    assert herald.t5_hulks().capped
