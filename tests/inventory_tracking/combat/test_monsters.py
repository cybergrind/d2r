"""The monsters of the simulator that walk and strike by themselves (combat/sim/monsters.py)."""

import itertools
import math

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import (
    AWARE,
    HOLD,
    MELEE,
    PACE,
    REACH,
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
    spark_points,
)


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


def test_a_blood_clan_walks_up_at_its_pace_and_holds_seven_units_off_before_it_goes_in():
    walker = Walker(1, BLOOD_CLAN, HERE[0] + 18.0, HERE[1])
    pack = Pack([walker])
    played(pack, 25)
    # A second: its Velocity of 7 times PACE at the most, less the frames it stood thinking.
    assert 18.0 - 7 * PACE - 0.01 <= away(walker) < 18.0
    played(pack, 50)
    assert away(walker) <= HOLD['Goatman'] + 0.01  # at its hold or already past it
    blows = played(pack, 500)
    assert away(walker) <= REACH  # it went in
    assert blows  # and struck
    # monstats A1MinD(H) to A1MaxD(H), percent of its level's monlvl DM(H)
    base = float(tables()['monlvl'][str(walker.traits.level)]['DM(H)']) / 100
    assert all(65 * base <= blow.damage <= 120 * base for blow in blows)
    assert all(blow.kind == MELEE and set(blow.parts) == {'physical'} for blow in blows)
    assert all(blow.target == 0 for blow in blows)


def test_a_blood_clan_goes_for_the_character_and_a_devilkin_for_whatever_is_nearest():
    demon = (HERE[0] + 10.0, HERE[1])
    clan, devilkin = Walker(1, BLOOD_CLAN, HERE[0] + 15.0, HERE[1]), Walker(2, DEVILKIN, HERE[0] + 15.0, HERE[1] + 1)
    pack = Pack([clan, devilkin])
    played(pack, 400, (HERE, demon))
    assert away(clan) < away(clan, demon)
    assert away(devilkin, demon) < away(devilkin)


def test_a_blow_lands_only_on_a_target_still_in_reach():
    walker = Walker(1, DEVILKIN, HERE[0] + 2.0, HERE[1])
    pack = Pack([walker])
    frame, target = 0, HERE
    while walker.doing != STRIKE and frame < 200:
        frame += 1
        pack.step(frame, [target])
    assert walker.doing == STRIKE
    gone = (HERE[0] - 30.0, HERE[1])  # the character teleports away under the blow
    assert [blow for step in range(frame + 1, frame + 20) for blow in pack.step(step, [gone])] == []


def test_a_ranged_monster_stands_and_strikes_nothing():
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


def test_a_lightning_enchanted_blow_carries_a_share_of_itself_as_lightning_by_rank():
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
