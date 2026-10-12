"""The Lightning Enchanted Herald of Tower Cellar 5: what the take holds of its sparks and of the blows
the character took, against what the simulator's monsters do (combat/sim/monsters.py).

The take's units carry their enchantments and its path heads who each monster was after (added to the
fixture on 2026-10-12 from the terror probe log of the same game; the recorder writes both since).
"""

import functools
import itertools
import math
import statistics

import pytest

from inventory_tracking.combat.hurts import ATTACK_MODES, hurts, missile_point, sole
from inventory_tracking.combat.sim.monsters import Pack, Traits, Walker, fitted
from inventory_tracking.combat.takes import Take
from tests.inventory_tracking.scenarios.battle import tower_cellar5 as battle


HERALD, BLOOD_CLAN = 2960229440, 55
SPARK, COLD_NOVA = 195, 194  # missiles.txt lightunique, coldunique
UNIQUE, MINION = 0x08, 0x10
AURA, STONE_SKIN, LIGHTNING = 30, 28, 17
TIER_STAT = '367'  # itemstatcost heraldtier
FAR = (0.0, 0.0)
# The model's sparks, fitted on the train half of all takes since 2026-10-12 (data/monsters_fit.json;
# this take is in the check half). Before, they were constants fitted to this take, of the same values.
SPARKS = fitted()['sparks']['count']['value']
SPARK_FRAMES = fitted()['sparks']['flight']['frames']['value']


@functools.cache
def take() -> Take:
    return Take.load(battle.FIXTURE)


def seconds(clock: float) -> float:
    return round(clock - take().frames[0]['t'], 2)


@functools.cache
def sparks() -> dict[int, list[tuple[int, tuple[float, float]]]]:
    """Each spark of the take: (frame number, place) while it flew."""
    found: dict[int, list[tuple[int, tuple[float, float]]]] = {}
    for frame in take().frames:
        for unit, txt, _mode, _x, _y, path in frame['x']:
            if txt == SPARK:
                found.setdefault(unit, []).append((frame['n'], missile_point(path)))
    return found


def test_the_take_names_the_herald_its_tier_and_what_its_pack_is_enchanted_with():
    units = {unit['unit']: unit for unit in take().units}
    herald = units[HERALD]
    assert (herald['txt'], herald['flags'], herald['mods']) == (BLOOD_CLAN, UNIQUE, [AURA, STONE_SKIN, LIGHTNING])
    assert herald['stats'][TIER_STAT] == 2
    minions = [unit for unit in units.values() if unit['stats'].get(TIER_STAT) and unit['unit'] != HERALD]
    assert len(minions) == 8  # the Terror Zone's config: eight at tier 2
    assert all((unit['flags'], unit['mods']) == (MINION, [STONE_SKIN, LIGHTNING]) for unit in minions)


def test_the_heralds_sparks_come_eight_at_a_time_and_fly_as_the_models_do():
    flown = sparks()
    born: dict[int, int] = {}
    for track in flown.values():
        born[track[0][0]] = born.get(track[0][0], 0) + 1
    assert set(born.values()) == {SPARKS}
    assert len(born) >= 9  # releases in the eight seconds the Herald was struck in
    releases = sorted(born)
    assert min(later - sooner for sooner, later in itertools.pairwise(releases)) >= 10

    pairs = [pair for track in flown.values() for pair in itertools.pairwise(track)]
    steps = [math.dist(a[1], b[1]) for a, b in pairs if b[0] == a[0] + 1]
    assert statistics.median(steps) == pytest.approx(12 / 25, abs=0.01)  # missiles.txt Vel 12
    assert max(len(track) for track in flown.values()) <= SPARK_FRAMES + 2

    def out(track, frames: int) -> float | None:
        return math.dist(track[0][1], track[frames][1]) if len(track) > frames else None

    pack = Pack([Walker(1, BLOOD_CLAN, 100.0, 100.0, flags=UNIQUE, mods=(LIGHTNING,))], seed=2)
    models: dict[int, list[tuple[int, tuple[float, float]]]] = {}
    for frame in range(1200):  # the fitted releases are fewer than the take's a second: played longer
        pack.struck(1, frame)
        pack.step(frame, [FAR])
        for spark in pack.sparks:
            models.setdefault(id(spark), [(spark.born, (100.0, 100.0))]).append((frame, (spark.x, spark.y)))
    for frames, slack in ((25, 1.0), (70, 2.5)):
        seen = [far for track in flown.values() if (far := out(track, frames)) is not None]
        model = [far for track in models.values() if (far := out(track, frames)) is not None]
        assert len(seen) >= 30
        assert len(model) >= 30
        assert statistics.median(model) == pytest.approx(statistics.median(seen), abs=slack)


def test_every_drop_of_the_characters_life_in_the_fight_is_found_with_its_suspects():
    rows = hurts(take())
    assert [(seconds(row['t']), row['lost']) for row in rows] == [
        (8.67, 239), (15.11, 110), (17.12, 5), (17.94, 137), (19.11, 19), (19.96, 210), (21.17, 57), (23.06, 1051),
    ]  # fmt: skip
    nova, minion, *_rest, last = rows
    # The first elite's death: a Cold Enchanted monster's nova, nobody striking.
    assert nova['by'] == []
    assert COLD_NOVA in {txt for txt, _away in nova['near']}
    # Two blows can be put on one monster each: a Lightning Enchanted minion's, 3.2 units off, and the
    # Herald's, swinging 7.7 units off with the character as its target and nothing else striking.
    put = [(row['lost'], found[0] == HERALD) for row in rows if (found := sole(row)) is not None]
    assert put == [(110, False), (210, True)]
    assert minion['by'][0][1:] == [BLOOD_CLAN, MINION, 4, 3.2, 1, [STONE_SKIN, LIGHTNING]]
    # The death: the Herald swinging 8.9 units off with the character as its target and a minion swinging
    # 3.2 off. No spark within three units: the sparks did not kill.
    assert last['dead']
    striking = [suspect for suspect in last['by'] if suspect[3] in ATTACK_MODES]
    assert [(suspect[0] == HERALD, suspect[2], suspect[4], suspect[5]) for suspect in striking] == [
        (False, MINION, 3.2, 1),
        (True, UNIQUE, 8.9, 1),
    ]
    assert last['near'] == []


def worst(flags: int, mods: tuple[int, ...]) -> float:
    """The most raw points a blow of the pack's Blood Clan can be by the tables."""
    traits = Traits.of(BLOOD_CLAN, level=75, flags=flags, mods=mods, tier=2)
    return traits.damage[1] * (1 + sum(most for _element, _least, most in traits.elements))


def test_the_blows_put_on_one_monster_are_within_what_the_models_monster_deals():
    minion, herald = worst(MINION, (STONE_SKIN, LIGHTNING)), worst(UNIQUE, (AURA, STONE_SKIN, LIGHTNING))
    assert 170 < minion < 200  # 122 physical and up to half of it again as lightning
    assert 550 < herald < 620  # 296 and as much again
    # What the character lost is the blow after its defences: never more than the raw blow.
    assert minion >= 110
    assert herald >= 210


@pytest.mark.xfail(
    strict=True,
    reason='the blow the character died of took 1051 points or more; the Herald and a minion striking in the '
    'same frame deal 776 at the most by the tables, before any resistance. What made it is not known '
    '(combat/plan.md, 2026-10-12)',
)
def test_the_blow_that_killed_is_within_what_the_pack_deals_by_the_tables():
    last = hurts(take())[-1]
    assert last['lost'] <= worst(UNIQUE, (AURA, STONE_SKIN, LIGHTNING)) + worst(MINION, (STONE_SKIN, LIGHTNING))
