"""The monsters of the simulator that walk, strike and shoot by themselves (combat/sim/monsters.py).

Where a test is of how a monster moves or of what a blow is made of, every swing lands in it
(`sure`: the fit's chances set to certain); the chances themselves, fitted to the takes
(data/monsters_fit.json), have their own tests at the end.
"""

import dataclasses
import itertools
import json
import math
import statistics

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import (
    AWARE,
    COLD,
    FIT,
    HOLD,
    MELEE,
    NOVA,
    PACE,
    REACH,
    SHOT,
    SHOT_CONTACT,
    SHOT_REACH,
    SPARK,
    SPARK_CONTACT,
    SPARK_FRAMES,
    SPARK_GAP,
    SPARKS,
    STRIKE,
    Blow,
    Pack,
    Traits,
    Walker,
    favour,
    fitted,
    idle,
    nova_points,
    nova_reach,
    reach_of,
    shooter_of,
    spark_points,
    spread,
    swing_of,
)
from tests.inventory_tracking.scenarios.arena.evidence.sure import sure


BLOOD_CLAN, DEVILKIN, DARK_ARCHER = 55, 21, 162
HERE = (5000.0, 5000.0)


def played(pack: Pack, frames: int, targets=(HERE,)):
    blows = []
    for frame in range(1, frames + 1):
        blows += pack.step(frame, list(targets))
    return blows


def away(walker: Walker, point=HERE) -> float:
    return math.dist(walker.at, point)


def test_a_monster_further_off_than_it_is_aware_stands():
    walker = Walker(1, BLOOD_CLAN, HERE[0] + AWARE + 5, HERE[1])
    played(Pack([walker]), 250)
    assert away(walker) == AWARE + 5


def test_a_blood_clan_walks_up_at_its_pace_and_holds_seven_units_off_before_it_goes_in(monkeypatch):
    sure(monkeypatch)  # every swing lands, from the body's reach, for the table's own roll
    walker = Walker(1, BLOOD_CLAN, HERE[0] + 18.0, HERE[1])
    pack = Pack([walker])
    played(pack, 25)
    # A second: its Velocity of 7 times PACE at the most, less the frames it stood thinking.
    assert 18.0 - 7 * PACE - 0.01 <= away(walker) < 18.0
    played(pack, 60)  # (50 before the refit: a think draws more rolls now, and this seed's stand one more time)
    assert away(walker) <= HOLD['Goatman'] + 0.01  # at its hold or already past it
    blows = played(pack, 500)
    assert away(walker) <= REACH  # it went in
    assert blows  # and struck
    # monstats A1MinD(H) to A1MaxD(H), percent of its level's monlvl DM(H)
    base = float(tables()['monlvl'][str(walker.traits.level)]['DM(H)']) / 100
    assert all(65 * base <= blow.damage <= 120 * base for blow in blows)
    assert all(blow.kind == MELEE and set(blow.parts) == {'physical'} for blow in blows)
    assert all(blow.target == 0 for blow in blows)


def test_whom_a_monster_goes_for_is_the_takes_share_of_its_case_and_it_keeps_to_it():
    # Before the fit: the nearest of all, the character first for a Goatman. The takes' path records
    # name the character 0.93 of the time for a Devilkin when it is the nearer and 0.66 when a companion
    # is (data/monsters_fit.json `targets`); each monster has one roll for whom it goes for.
    near, far = favour(DEVILKIN)
    assert (near, far) == (pytest.approx(0.9265), pytest.approx(0.6564))
    demon = (HERE[0] + 10.0, HERE[1])
    pack = Pack([Walker(unit, DEVILKIN, HERE[0] + 15.0, HERE[1] + unit / 1000) for unit in range(1, 1001)])
    walkers = list(pack.walkers.values())
    beside_the_demon = [pack._target(walker, [HERE, demon]) for walker in walkers]
    assert beside_the_demon.count(0) / 1000 == pytest.approx(far, abs=0.04)
    beside_the_character = [pack._target(walker, [demon, HERE]) for walker in walkers]
    assert beside_the_character.count(0) / 1000 == pytest.approx(near, abs=0.03)
    # One that goes for the character with a companion nearer goes for it when it is the nearer too.
    assert all(late == 0 for early, late in zip(beside_the_demon, beside_the_character, strict=True) if early == 0)
    assert beside_the_demon == [pack._target(walker, [HERE, demon]) for walker in walkers]  # no new roll
    assert all(pack._target(walker, [HERE]) == 0 for walker in walkers[:20])  # alone, the character
    # Of two companions it is the nearer one; a target beyond what it is aware of gives way to the other.
    other = (HERE[0] + 40.0, HERE[1])
    assert {pack._target(walker, [HERE, other, demon]) for walker in walkers} == {0, 2}
    assert {pack._target(walker, [(HERE[0] - 30.0, HERE[1]), demon]) for walker in walkers} == {1}


def test_a_monster_walks_to_the_one_it_goes_for(monkeypatch):
    sure(monkeypatch)
    demon = (HERE[0] + 10.0, HERE[1])
    walkers = [Walker(unit, BLOOD_CLAN, HERE[0] + 15.0, HERE[1] + unit) for unit in range(1, 9)]
    pack = Pack(walkers)
    chosen = {walker.unit: pack._target(walker, [HERE, demon]) for walker in walkers}
    assert set(chosen.values()) == {0, 1}
    played(pack, 600, (HERE, demon))
    for walker in walkers:
        mine, other = (HERE, demon) if chosen[walker.unit] == 0 else (demon, HERE)
        assert away(walker, mine) <= REACH < away(walker, other)


def test_a_blow_lands_only_on_a_target_still_in_reach(monkeypatch):
    sure(monkeypatch)
    walker = Walker(1, DEVILKIN, HERE[0] + 2.0, HERE[1])
    pack = Pack([walker])
    frame, target = 0, HERE
    while walker.doing != STRIKE and frame < 200:
        frame += 1
        pack.step(frame, [target])
    assert walker.doing == STRIKE
    gone = (HERE[0] - 30.0, HERE[1])  # the character teleports away under the blow
    assert [blow for step in range(frame + 1, frame + 20) for blow in pack.step(step, [gone])] == []


def test_a_monster_that_is_no_fighter_by_its_row_and_was_given_no_shot_stands():
    walker = Walker(1, DARK_ARCHER, HERE[0] + 10.0, HERE[1])
    assert played(Pack([walker]), 250) == []
    assert away(walker) == 10.0


def test_a_monsters_rolls_are_its_own():
    def path(others):
        walker = Walker(1, BLOOD_CLAN, HERE[0] + 18.0, HERE[1])
        pack = Pack([walker, *others], seed=7)
        played(pack, 200)
        return walker.at

    assert path([]) == path([Walker(2, DEVILKIN, HERE[0] - 12.0, HERE[1])])


# -- rank, Herald tier and enchantments (2026-10-12) ---------------------------------------------------

UNIQUE, MINION = 0x08, 0x10  # the type flags
STONE_SKIN, LIGHTNING, AURA, STRONG = 28, 17, 30, 5
FAR = (9000.0, 9000.0)  # a target no spark reaches


def herald(**given) -> Walker:
    """The Herald of Tower Cellar 5: a unique Blood Clan of tier 2, Lightning Enchanted."""
    mods = (AURA, STONE_SKIN, LIGHTNING)
    return Walker(1, BLOOD_CLAN, HERE[0] + 1.0, HERE[1], flags=UNIQUE, mods=mods, tier=2, **given)


def test_a_blow_is_raised_by_the_rank_extra_strong_and_the_tier_of_the_herald():
    plain = Traits.of(BLOOD_CLAN).damage[1]
    unique, tiers = tables()['unique'], tables()['heralds']['2']

    leader = Traits.of(BLOOD_CLAN, flags=UNIQUE).damage[1]
    assert leader == pytest.approx(plain * (1 + unique['unique_damage'][0] / 100))
    assert Traits.of(BLOOD_CLAN, flags=MINION).damage[1] == plain  # a minion has no bonus of its own
    strong = Traits.of(BLOOD_CLAN, flags=MINION, mods=(STRONG,)).damage[1]
    assert strong == pytest.approx(plain * (1 + unique['minion_strong_damage'][0] / 100))
    assert herald().traits.damage[1] == pytest.approx(plain * 1.66 * (1 + tiers['damage'] / 100))
    follower = Traits.of(BLOOD_CLAN, flags=MINION, tier=2).damage[1]
    assert follower == pytest.approx(plain * (1 + tiers['minion_damage'] / 100))
    # A higher monster level is a higher base (monlvl DM(H)).
    assert Traits.of(BLOOD_CLAN, level=95).damage[1] > Traits.of(BLOOD_CLAN, level=75).damage[1]


def test_a_lightning_enchanted_blow_carries_a_share_of_itself_as_lightning_by_rank(monkeypatch):
    sure(monkeypatch, spread=True)  # the spread of a blow's size is on all its parts alike
    for walker, (least, most) in (
        (herald(), (0.66, 1.0)),
        (Walker(2, BLOOD_CLAN, HERE[0] + 1.0, HERE[1], flags=MINION, mods=(STONE_SKIN, LIGHTNING)), (0.33, 0.5)),
    ):
        blows = played(Pack([walker]), 1500)
        assert len(blows) > 20
        for blow in blows:
            assert set(blow.parts) == {'physical', 'lightning'}
            assert least - 1e-9 <= blow.parts['lightning'] / blow.parts['physical'] <= most + 1e-9
            assert blow.damage == pytest.approx(sum(blow.parts.values()))


def test_whoever_takes_a_blow_cuts_each_part_by_its_own_resistance():
    blow = Blow(1, 1, 0, 300.0, MELEE, {'physical': 200.0, 'lightning': 100.0})
    assert blow.taken({}) == 300.0
    assert blow.taken({'lightning': 0.75}) == 225.0
    assert blow.taken({'lightning': 0.75, 'physical': 0.5}) == 125.0
    assert Blow(1, 1, 0, 80.0).taken({'physical': 0.25}) == 60.0  # a blow without parts is physical


def test_struck_a_lightning_enchanted_monster_lets_eight_sparks_go_one_to_each_45_degrees():
    pack = Pack([herald(), Walker(2, BLOOD_CLAN, HERE[0] + 5, HERE[1])])
    assert all(pack.struck(2, frame) == 0 for frame in range(200))  # not enchanted: never
    releases = [frame for frame in range(1000) if pack.struck(1, frame)]
    assert len(pack.sparks) >= SPARKS
    first = [spark for spark in pack.sparks if spark.born == releases[0]]
    assert sorted(round(math.degrees(spark.course)) for spark in first) == [0, 45, 90, 135, 180, 225, 270, 315]
    assert all(later - sooner >= SPARK_GAP for sooner, later in itertools.pairwise(releases))
    # Struck in every frame of 40 s: a release in a third of the frames it is free to, about every 12 frames.
    assert 70 <= len(releases) <= 1000 // SPARK_GAP


def test_a_spark_weaves_outward_at_the_missiles_speed_and_is_gone_after_three_seconds():
    pack = Pack([herald()], seed=5)
    start = herald().at
    frame = next(frame for frame in range(100) if pack.struck(1, frame))
    pack.remove(1)  # the sparks fly on without it
    reached = {}
    for step in range(1, SPARK_FRAMES + 1):
        before = {id(spark): (spark.x, spark.y) for spark in pack.sparks}
        assert pack.step(frame + step, [FAR]) == []
        for spark in pack.sparks:
            if id(spark) in before:
                assert math.dist(before[id(spark)], (spark.x, spark.y)) == pytest.approx(12 / 25)  # Vel 12
            reached[id(spark)] = math.dist(start, (spark.x, spark.y))
    assert pack.sparks == []
    # The take: 26.1 to 31.4 units out at three seconds; straight would be 37.
    assert len(reached) == SPARKS
    assert all(24.0 <= far <= 36.0 for far in reached.values())


def test_a_spark_ends_on_the_first_body_in_its_way_for_its_points_of_lightning():
    walker = herald(level=75)
    pack = Pack([walker], seed=5)
    frame = next(frame for frame in range(100) if pack.struck(1, frame))
    pack.remove(1)
    east = (walker.x + 4.0, walker.y)  # in the way of the spark going east; one beside it may weave in too
    blows = []
    for step in range(1, 30):
        blows += pack.step(frame + step, [FAR, east])
    assert 1 <= len(blows) <= 3
    assert all((blow.kind, blow.unit, blow.target) == (SPARK, 1, 1) for blow in blows)
    assert blows[0].parts == {'lightning': spark_points(75)}
    assert blows[0].damage == 2 * 75 - 1
    assert len(pack.sparks) == SPARKS - len(blows)  # a spark is gone with its blow
    assert blows[0].frame - frame <= math.ceil((4.0 - SPARK_CONTACT) / (12 / 25 * math.cos(math.pi / 4))) + 1


# -- what the train half of all takes gives (data/monsters_fit.json, 2026-10-12) --------------------------

DARK_ARCHER_SHOT = {'physical': 40.0, 'cold': 60.0}
ICE_SPAWN, BAAL_TAUNT, GHOST = 458, 545, 38
SECONDS = 2000


def swings(txt: int, seconds: int = SECONDS, seed: int = 3, at: float = 2.0, **given):
    """One monster of `txt` `at` units from a character standing still: the swings begun, the whole
    ones among them and the blows."""
    walker = Walker(1, txt, HERE[0] + at, HERE[1], **given)
    pack = Pack([walker], seed)
    begun = whole = 0
    blows, until = [], walker.until
    for frame in range(seconds * 25):
        blows += pack.step(frame, [HERE])
        if walker.doing == STRIKE and walker.until != until:
            begun += 1
            whole += walker.lands >= 0
        until = walker.until
    return begun, whole, blows


@pytest.mark.parametrize('txt', [DEVILKIN, BLOOD_CLAN, ICE_SPAWN, GHOST])
def test_a_monster_in_reach_swings_at_the_takes_rate_and_a_swing_is_not_a_hit(txt):
    found = swing_of(txt)
    assert found is fitted()['melee']['types'][str(txt)]
    begun, whole, blows = swings(txt)
    assert begun / SECONDS == pytest.approx(found['rate']['value'], rel=0.05)
    assert 1 - whole / begun == pytest.approx(found['cut']['value'], abs=0.03)
    assert len(blows) / whole == pytest.approx(found['takes_life']['value'], abs=0.03)
    assert 0.1 < found['takes_life']['value'] < 0.45  # before the fit: every swing landed
    assert all(blow.kind == MELEE and blow.target == 0 for blow in blows)


def test_a_type_without_a_row_of_its_own_swings_by_the_pooled_one():
    walker = Walker(1, DARK_ARCHER, HERE[0], HERE[1])
    assert swing_of(DARK_ARCHER) is fitted()['melee']['pooled']
    assert swing_of(DARK_ARCHER)['rate']['value'] == pytest.approx(1.085)  # 725 swings in 668 s within 3.5 units
    assert swing_of(DARK_ARCHER)['takes_life']['value'] == pytest.approx(0.161)  # 0.086 to 0.236 of 292 swings
    assert favour(DARK_ARCHER) == (pytest.approx(0.9184), pytest.approx(0.5145))
    assert walker.traits.strikes == 8  # its row's aip3 is read and no longer what decides a swing


def test_a_blow_on_a_companion_always_lands():
    walker = Walker(1, DEVILKIN, HERE[0] + 2.0, HERE[1])
    pack = Pack([walker], 3)
    walker.favour = 1.0  # it goes for the companion
    far = (HERE[0] - 40.0, HERE[1])
    begun = whole = 0
    blows, until = [], walker.until
    for frame in range(5000):
        blows += pack.step(frame, [far, HERE])
        if walker.doing == STRIKE and walker.until != until:
            begun, whole = begun + 1, whole + (walker.lands >= 0)
        until = walker.until
    assert whole > 50
    assert whole - 1 <= len(blows) <= whole  # the last swing may not have come to its middle yet
    assert all(blow.target == 1 for blow in blows)


def test_a_type_the_takes_show_standing_in_reach_never_strikes():
    assert idle(BAAL_TAUNT)
    assert not idle(DEVILKIN)
    begun, _whole, blows = swings(BAAL_TAUNT, 200)
    assert (begun, blows) == (0, [])


def test_the_reach_is_the_bodys_for_most_swings_and_further_for_the_share_the_takes_show():
    tail = fitted()['reach']['tail']
    assert [band['to'] for band in tail] == [4.0, 5.0, 6.0, 8.0, 12.0]
    shares = [band['share'] for band in tail]
    assert shares == sorted(shares, reverse=True)  # never more swings from further off
    assert reach_of(0.999) == REACH
    assert reach_of(shares[0] + 1e-6) == REACH
    assert reach_of(shares[0] - 1e-6) == 4.0
    assert reach_of(0.0) == 12.0
    # Held 4.5 units off (it cannot walk), a monster still begins a swing now and then, and some land.
    walker = Walker(1, GHOST, HERE[0] + 4.5, HERE[1])
    pack = Pack([walker], 5)
    walker.traits = dataclasses.replace(walker.traits, speed=0.0)
    blows = [blow for frame in range(40000) for blow in pack.step(frame, [HERE])]
    assert 0 < len(blows) < 40  # in reach it would land about 160 in this time
    assert away(walker) == 4.5


def test_the_spread_of_a_blow_is_drawn_through_the_takes_quantiles_and_keeps_the_mean():
    for kind, part in ((MELEE, 'melee'), (SHOT, 'shots')):
        found = fitted()[part]['spread']
        for share, factor in found['knots']:
            assert spread(kind, share) == pytest.approx(factor)
        points = found['points']
        assert spread(kind, 0.5) * found['mean_points'] == pytest.approx(points['p50'], rel=0.001)
        assert spread(kind, 0.9) * found['mean_points'] == pytest.approx(points['p90'], rel=0.001)
        assert spread(kind, 1.0) * found['mean_points'] == pytest.approx(points['max'], rel=0.001)
        assert statistics.fmean(spread(kind, (k + 0.5) / 20000) for k in range(20000)) == pytest.approx(1.0, abs=0.01)
    # A blow of the pack: the table's roll times that factor, and one in ten over 1.8 times the roll's most.
    _begun, _whole, blows = swings(BLOOD_CLAN, 4000)
    least, most = Traits.of(BLOOD_CLAN).damage
    assert least * spread(MELEE, 0.0) <= min(blow.damage for blow in blows)
    assert max(blow.damage for blow in blows) <= most * spread(MELEE, 1.0)
    assert 0.05 < sum(blow.damage > most * 1.5 for blow in blows) / len(blows) < 0.2
    assert statistics.fmean(blow.damage for blow in blows) == pytest.approx((least + most) / 2, rel=0.2)


def shooting(seed: int = 3, away_by: float = 15.0, companions=(), frames: int = SECONDS * 25, hero=lambda _frame: HERE):
    walker = Walker(1, DARK_ARCHER, HERE[0] + away_by, HERE[1])
    pack = Pack([walker], seed, {1: DARK_ARCHER_SHOT})
    sent, blows = [], []
    for frame in range(frames):
        before = len(pack.flying)
        landed = sum(1 for missile in pack.flying if missile.lands <= frame)
        blows += pack.step(frame, [hero(frame), *companions])
        if len(pack.flying) > before - landed:
            sent.append(pack.flying[-1])
    return walker, pack, sent, blows


def test_a_shooter_stands_and_shoots_at_the_takes_rate_and_few_missiles_take_life():
    found = shooter_of(DARK_ARCHER)
    assert found is fitted()['shots']['types'][str(DARK_ARCHER)]
    walker, _pack, sent, blows = shooting()
    assert away(walker) == 15.0
    assert len(sent) / SECONDS == pytest.approx(found['rate']['value'], rel=0.05)  # 0.43 a second, not one
    assert all(missile.target == 0 for missile in sent)  # nobody else to shoot at
    assert len(blows) / len(sent) == pytest.approx(found['takes_life']['value'], abs=0.01)
    assert all(blow.kind == SHOT and set(blow.parts) == {'physical', 'cold'} for blow in blows)
    # The missile flies at the speed of the type's missile: 18 units a second, 15 units in 21 frames.
    assert found['speed']['value'] == 18.0
    assert {missile.lands for missile in sent} <= {frame + 21 for frame in range(SECONDS * 25)}


def test_a_shooters_mark_is_the_character_with_the_takes_share_else_the_nearest_companion():
    mates = [(HERE[0] + 30.0, HERE[1] + 30.0), (HERE[0] + 8.0, HERE[1] + 6.0)]
    _walker, _pack, sent, _blows = shooting(companions=mates)
    share = sum(missile.target == 0 for missile in sent) / len(sent)
    assert share == pytest.approx(shooter_of(DARK_ARCHER)['aim']['value'], abs=0.04)
    assert {missile.target for missile in sent} == {0, 2}
    assert all(missile.at == (HERE if missile.target == 0 else mates[1]) for missile in sent)


def test_a_missile_ends_where_its_mark_stood_so_a_character_that_left_is_not_hit(monkeypatch):
    sure(monkeypatch)
    _walker, _pack, sent, blows = shooting(frames=2000)
    assert len(blows) == len([missile for missile in sent if missile.lands < 2000])  # standing: every one

    def hopping(frame: int):
        return HERE if frame // 40 % 2 == 0 else (HERE[0], HERE[1] + SHOT_CONTACT + 3.0)

    _walker, _pack, sent, blows = shooting(frames=4000, hero=hopping)
    assert 0 < len(blows) < len(sent)
    for blow in blows:
        assert math.dist(hopping(blow.frame), next(m.at for m in sent if m.lands == blow.frame)) <= SHOT_CONTACT
    stayed = [m for m in sent if m.lands < 4000 and math.dist(hopping(m.lands), m.at) <= SHOT_CONTACT]
    assert len(blows) == len(stayed)


def test_a_shooter_out_of_reach_stands_until_it_has_had_a_target_in_reach_and_then_follows():
    walker, _pack, sent, _blows = shooting(away_by=SHOT_REACH + 5.0, frames=500)
    assert (away(walker), sent) == (SHOT_REACH + 5.0, [])

    def leaving(frame: int):
        return HERE if frame < 100 else (HERE[0] - 30.0, HERE[1])

    walker, _pack, sent, _blows = shooting(frames=1500, hero=leaving)
    assert away(walker, leaving(1500)) <= SHOT_REACH
    assert any(missile.at == leaving(1500) for missile in sent)


def cold_death(distance: float, seed: int, **given):
    walker = Walker(1, GHOST, HERE[0] + distance, HERE[1], mods=(COLD,), **given)
    pack = Pack([walker], seed)
    spreads = pack.died(1, 100)
    return spreads, [blow for frame in range(101, 140) for blow in pack.step(frame, [HERE])]


def test_the_death_of_a_cold_enchanted_elite_lets_a_nova_go():
    found = fitted()['nova']
    assert nova_reach() == pytest.approx(14 * 24 / 25)  # missiles.txt coldunique: Range 14 frames at Vel 24
    assert nova_points(85) == pytest.approx(729)  # 182 through a cold resistance at the cap; the takes' median 174
    deaths = [cold_death(9.5, seed, flags=UNIQUE, level=85) for seed in range(400)]
    assert all(spreads for spreads, _blows in deaths)
    hits = [blows[0] for _spreads, blows in deaths if blows]
    assert all(len(blows) <= 1 for _spreads, blows in deaths)
    assert len(hits) / 400 == pytest.approx(found['takes_life']['value'], abs=0.06)  # 0.70 of 37 deaths
    assert all(blow.kind == NOVA and blow.target == 0 and set(blow.parts) == {'cold'} for blow in hits)
    assert {round(blow.damage) for blow in hits} == {729, 1458}
    twice = sum(blow.damage > 1000 for blow in hits) / len(hits)
    assert twice == pytest.approx(found['double']['value'], abs=0.06)  # 5 of the 26 nova drops were over 300
    # The ring spreads at 24 units a second: it passes a character 9.5 units off ten frames on.
    assert {blow.frame for blow in hits} == {110}


def test_no_nova_from_a_plain_monster_a_minion_or_beyond_the_rings_reach():
    assert cold_death(5.0, 1) == (False, [])  # 0 of 373 plain monsters and minions carrying it showed one
    assert cold_death(5.0, 1, flags=MINION) == (False, [])
    assert all(cold_death(nova_reach() + 0.5, seed, flags=UNIQUE)[1] == [] for seed in range(50))
    walker = Walker(1, GHOST, HERE[0] + 5.0, HERE[1], flags=UNIQUE)  # not Cold Enchanted
    assert Pack([walker]).died(1, 0) is False


def test_equal_seeds_give_equal_fights_and_other_seeds_others():
    def fight(seed: int):
        walkers = [
            Walker(1, DARK_ARCHER, HERE[0] + 14.0, HERE[1]),
            Walker(2, BLOOD_CLAN, HERE[0] + 9.0, HERE[1] + 4.0, flags=UNIQUE, mods=(COLD, LIGHTNING), tier=2),
            Walker(3, DEVILKIN, HERE[0] - 2.0, HERE[1]),
            Walker(4, GHOST, HERE[0], HERE[1] + 2.5),
        ]
        pack = Pack(walkers, seed, {1: DARK_ARCHER_SHOT})
        blows = []
        for frame in range(3000):
            if frame == 1500:
                pack.struck(2, frame)
                pack.died(2, frame)
            blows += pack.step(frame, [HERE, (HERE[0] + 4.0, HERE[1] - 4.0)])
        return blows, [walker.at for walker in walkers]

    assert fight(11) == fight(11)
    assert fight(11) != fight(12)


def test_the_fit_names_its_source_and_every_fitted_number_has_its_n():
    found = json.loads(FIT.read_text(encoding='utf-8'))
    assert found == fitted()
    assert 'train half' in found['about']
    assert found['train'] == {'takes': 330, 'seconds': 9730.2, 'drops': 810}
    rows = [found['melee']['pooled'], *found['melee']['types'].values()]
    for row in rows:
        assert row['rate']['n_swings'] > 0
        assert row['rate']['n_seconds'] > 0
        assert row['cut']['n'] > 0
        assert row['takes_life']['n'] > 0
    for row in (found['shots']['pooled'], *found['shots']['types'].values()):
        assert row['rate']['n_shots'] >= 20
        assert row['aim']['n'] > 0
        assert row['takes_life']['n'] > 0
    assert all(band['n'] > 0 for band in found['reach']['tail'])
    assert found['nova']['takes_life']['n'] == 37
    assert found['melee']['spread']['n'] == 49
    assert found['shots']['spread']['n'] == 28
