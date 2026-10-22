"""The death in the Disused Fane (fane_death.py; rca/2026-10-21/fane-death-sim-findings.md): what the scene carries,
the walls it plays, the game's own blows and chance to hit it plays them with, and the claims the findings could not
make (strict xfails).

The plays found (2026-10-22 ~12:45, findings §9; 20 seeds each, late looks lap 0.02; the blows and shots capped at
the game's most, raised by each unit's own stat 25 and shown to the macro as the live client shows it; melee within 4):
with every fix off fane-death-24 dies in 8 of 20 (6.6-17.8 s), drawn 8, fane-death-20 5, drawn 2; with every fix on
none of the 80 dies. Battle Orders is cast again at 3.68 s on seed 1 (REBUFF), before the take's 8.67 s."""

import functools
import math

import pytest

from inventory_tracking.combat.sim.monsters import MELEE, PHYSICAL, Blow
from inventory_tracking.game.layout import FULL_REJUVENATION
from tests.inventory_tracking.scenarios.arena.situations.fane_death import (
    ALL_OFF,
    ALL_ON,
    AWARE,
    DEFENCE,
    FRAME,
    HERALD,
    NIGHT_LORD_TYPE,
    SECOND,
    TZ_LEVEL,
    WINDOWED,
    Measures,
    brisk,
    drawing,
    fast,
    measures,
    play,
    stored,
)
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


TWENTY = tuple(range(1, 21))
LAP = 0.02  # a look's timer late at its fifth reading, as the take's looks of 81-99 ms (fane_death.py `late_timer`)
UNIQUE_NIGHT_LORD = 4206932652  # Cursed, Extra Strong, Fire Enchanted


@functools.cache
def played(name: str, which: str, seed: int, drawn: bool = False) -> Measures:
    extra = drawing(name) if drawn else None
    return measures(play(stored(name), ALL_ON if which == 'on' else ALL_OFF, seed, lap=LAP, extra=extra))


def test_the_types_walk_at_the_takes_windowed_pace_and_the_fast_variant_at_the_frame_to_frame_one():
    # fane_death.py WINDOWED (2026-10-22): a Flesh Hunter 10.56 a second over 0.5 s windows, not the 18.63 frame to
    # frame that ran the arena's in twice as fast as the game's (f24 drawn seed 4)
    situation = stored('fane-death-24')
    assert situation.speeds == {txt: WINDOWED[txt] for txt in (47, 132, 27)}
    assert situation.speeds is not None
    assert situation.speeds[47] == 10.56
    assert fast(situation).speeds == {txt: FRAME[txt] for txt in (47, 132, 27)}
    quick = brisk(situation).speeds
    assert quick is not None
    assert quick[47] > situation.speeds[47]


def test_the_scene_carries_the_fight_as_the_take_holds_it():
    situation = stored('fane-death-24')
    mobs = {mob.unit: mob for mob in situation.scene.mobs}
    herald = mobs[HERALD]
    assert herald.tier == 2
    assert 30 in herald.mods
    assert herald.level == TZ_LEVEL == 96
    assert set(mobs[SECOND].mods) == {9, 30, 6}  # Fire Enchanted, Aura Enchanted, Extra Fast
    assert mobs[4206932652].mods == (7, 5, 9)  # the unique Night Lord: Cursed, Extra Strong, Fire Enchanted
    assert NIGHT_LORD_TYPE in situation.melee
    assert situation.auras == {SECOND: pytest.approx(2.0)}
    # Amplify Damage on at the cut, Conviction 0.18 s in: physical 1.82, fire 0.91, lightning 1.02, cold 0.82 through
    assert (0.0, 'physical', 1.82) in situation.curses
    assert {(0.18, 'fire', 0.91), (0.18, 'lightning', 1.02), (0.18, 'cold', 0.82)} <= set(situation.curses)
    orders = situation.orders
    assert orders is not None
    assert orders.ends == pytest.approx(8.67)
    assert orders.cast_at is None
    assert orders.factor == pytest.approx(2943 / 1896, abs=1e-3)
    hero = situation.scene.hero
    assert situation.own_teleport
    assert all(found.teleport_charges is None for found in hero.sets)
    assert sum(1 for cell in hero.belt if cell == FULL_REJUVENATION) == 8
    assert hero.max_life == 2943
    assert situation.capped
    assert situation.defence is None  # the fit's chance to take life (the population, findings §8)
    assert situation.block is None
    percent = situation.damage_percent
    assert percent is not None
    assert percent[SECOND][0][1] == 190  # Might L16 on the second unique as the take read it
    assert max(value for _, value in percent[UNIQUE_NIGHT_LORD]) == 475  # Might L16 190 + Concentration L16 285
    assert situation.aware == AWARE == 35.0


def test_a_blow_is_at_most_the_game_s_most_and_might_raises_its_physical_points_alone():
    situation = stored('fane-death-24')
    stage = Stage(situation.scene, capped=True, auras=situation.auras)
    walker = stage.cast.pack.walkers[UNIQUE_NIGHT_LORD]
    least, most = walker.traits.damage
    assert (least, most) == pytest.approx((226.175, 452.35))  # 50-100 x DM(H) 109% x unique 1.66 x Extra Strong 2.5
    huge = Blow(0, UNIQUE_NIGHT_LORD, 0, 5000.0, MELEE, {PHYSICAL: 3000.0, 'fire': 2000.0})
    (cut,) = stage.cast.bounded([huge])
    assert dict(cut.parts) == pytest.approx({PHYSICAL: most, 'fire': most})  # fire at most 100% of the physical
    mob = stage.cast.mobs[UNIQUE_NIGHT_LORD]
    stage.cast.mobs[SECOND].at = mob.at  # the Might unique beside it
    assert stage.cast.landed(cut, {}) == pytest.approx(most * 2.0 + most)  # Might's x2 on the physical points only


def test_a_swing_hits_with_the_game_s_chance_against_the_character_s_defence():
    situation = stored('fane-death-24')
    stage = Stage(situation.scene, capped=True, defence=(DEFENCE, 96))
    walkers = stage.cast.pack.walkers
    # AR = A1TH(H) x monlvl 96 TH(H) 3826 / 100 x the rank's bonus, against defence 1530 at level 96
    assert stage.cast.to_hit(walkers[HERALD]) == pytest.approx(0.8667, abs=1e-4)  # 130, unique +100%
    assert stage.cast.to_hit(walkers[UNIQUE_NIGHT_LORD]) == pytest.approx(0.8572, abs=1e-4)  # 120, unique +100%
    minion = next(w for w in walkers.values() if w.txt == 47 and w.traits.rank == 'minion')
    assert stage.cast.to_hit(minion) == pytest.approx(0.8298, abs=1e-4)  # 130, a unique's minion +50%
    assert dict(stage.loot.stats)[31] == 1530  # the macro reads the take's defence too


def test_the_stage_shows_the_macro_each_hostile_s_damage_percent_as_the_take_read_it():
    # The live client's full stat list holds stat 25 (game/decode.py `Monster.damage_percent`); the arena shows the
    # reading its blows play by (mobs.py `shown_percent`): Might L16's 190 on the second unique at the start
    situation = stored('fane-death-24')
    stage = Stage(situation.scene, capped=True, damage_percent=situation.damage_percent)
    shown = {monster.unit_id: monster.damage_percent for monster in stage.mobs.monsters()}
    assert shown[SECOND] == 190
    assert shown[HERALD] == 285  # Concentration L16 on the Herald (its Conviction is the curse)
    assert all(shown[mob.unit] is None for mob in situation.scene.mobs if mob.ally or mob.owner is not None)


def test_a_capped_melee_blow_lands_only_within_the_game_s_reach():
    # sim/monsters.py's fitted reach tail would land a blow from 9.8 units (mobs.py `in_reach`)
    situation = stored('fane-death-24')
    stage = Stage(situation.scene, capped=True)
    walker = stage.cast.pack.walkers[UNIQUE_NIGHT_LORD]
    blow = Blow(0, UNIQUE_NIGHT_LORD, 0, 300.0, MELEE, {PHYSICAL: 300.0})
    assert stage.cast.in_reach(blow, (walker.x + 3.9, walker.y))
    assert not stage.cast.in_reach(blow, (walker.x + 9.8, walker.y))


def test_a_teleport_into_a_wall_of_the_fane_is_refused_and_one_onto_footing_lands():
    situation = stored('fane-death-24')
    stage = Stage(situation.scene, orders=situation.orders, own_teleport=True, rules=situation.rules)
    here = stage.here
    assert stage.barred is not None
    spots = [(here[0] + dx, here[1] + dy) for dx in range(-40, 41, 2) for dy in range(-40, 41, 2)]
    wall = min((spot for spot in spots if stage.barred(spot)), key=lambda spot: math.dist(spot, here))
    assert math.dist(wall, here) < 5.0  # the corridor's south wall
    stage.ground_under_pointer = lambda: wall  # type: ignore[method-assign]
    stage.hop()
    assert stage.refused == [wall]
    assert stage.landing is None
    assert stage.hops == []
    floor = next(spot for spot in spots if not stage.barred(spot) and math.dist(spot, here) > 10)
    stage.ground_under_pointer = lambda: floor  # type: ignore[method-assign]
    stage.hop()
    assert stage.landing is not None
    assert stage.hops[-1][2] == stage.landing.spot


def test_battle_orders_is_cast_again_before_it_would_run_out_at_the_take_s_moment():
    # The REBUFF design (death-findings.md Round 3: its age not known after the restart, it is due at once and cast
    # when safe, else after a rebuff retreat): seed 1 casts it before the take's 8.67 s (3.68 s until the arena showed
    # a walker's motion, mobs.py SHOWN_MOTION; 6.8 s since, 2026-10-22); it never runs out
    found = played('fane-death-24', 'on', 1)
    assert found.orders[0][1] == 'cast'
    assert found.orders[0][0] < stored('fane-death-24').orders.ends  # type: ignore[union-attr]
    assert 'ran out' not in [what for _, what in found.orders]


@pytest.mark.slow
@pytest.mark.xdist_group('fane death: on')
def test_every_escape_lands_on_footing():
    for seed in TWENTY:
        assert played('fane-death-24', 'on', seed).off_footing == 0, seed


@pytest.mark.slow
@pytest.mark.xdist_group('fane death: off')
@pytest.mark.xfail(
    strict=True,
    reason='with every fix off 8 of 20 die (6.6-17.8 s), the median lowest life 47%: the game died once in 1658 fight '
    'windows (findings §8, §9), and the arena loses 40% of its seeds here, not most',
)
def test_with_every_fix_off_most_seeds_die_as_the_game_did():
    deaths = sum(played('fane-death-24', 'off', seed).dead for seed in TWENTY)
    assert deaths >= 10


@pytest.mark.slow
@pytest.mark.xdist_group('fane death: on')
def test_with_every_fix_on_no_seed_of_the_late_cut_dies():
    assert not any(played('fane-death-24', 'on', seed).dead for seed in TWENTY)


@pytest.mark.slow
@pytest.mark.xdist_group('fane death: on 20')
def test_with_every_fix_on_seed_19_of_the_early_cut_lives():
    # It died at 10.56 s before round 3 (findings §7): two blows in 0.12 s, the unique Night Lord's 2058 the second
    assert not played('fane-death-20', 'on', 19).dead


@pytest.mark.slow
@pytest.mark.xdist_group('fane death: drawn')
def test_with_every_fix_on_the_drawn_pack_kills_no_seed():
    # Seed 3 died at 21.76 s before round 3 (findings §7), six rejuvenations drunk, Battle Orders never cast again
    assert not played('fane-death-20', 'on', 3, drawn=True).dead
