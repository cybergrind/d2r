"""sim/diablo.py and combat/threats/diablo.py: Diablo by the client's rules (rca/2026-10-13/re/notes-ai-diablo.md) and
his red lightning priced for a place (rca/2026-10-13/diablo.md)."""

import math
import random

import pytest

from inventory_tracking.combat.sim import casters, diablo as rules
from inventory_tracking.combat.sim.monsters import Pack, Walker
from inventory_tracking.combat.threats import diablo as threat


DIABLO = 243
STOPPED = {'physical': 0.10, 'lightning': 0.75, 'fire': 0.75, 'cold': 0.75, 'magic': 0.0}


def test_his_rows_and_levels_are_the_tables():
    assert rules.is_diablo(DIABLO)
    assert rules.is_diablo(333)
    row = rules.row(DIABLO)
    assert row is not None
    assert [row[f'Skill{n}'] for n in range(1, 8)] == [
        'DiabLight', 'DiabCold', 'DiabFire', 'DiabWall', 'DiabRun', 'PrimeFirewall', 'DiabPrison',
    ]  # fmt: skip
    assert rules.skill_level(DIABLO, 1) == 10  # Sk1lvl 3 + Hell's 7
    assert rules.missile_life(10) == 39  # Param2 30 + level - 1 (the takes: 39)
    hit = rules.points(rules.LIGHTNING_MISSILE, 10)
    assert hit['physical'] == pytest.approx((24.25, 26.25))
    assert hit['lightning'] == pytest.approx((42.25, 52.5))
    assert rules.rate(rules.LIGHTNING_MISSILE) == pytest.approx(82 / 1024)
    assert rules.every(rules.LIGHTNING_MISSILE) == 3


def test_he_thinks_by_his_own_rules_and_harm_still_takes_him_for_unread():
    mind = casters.mind_for(DIABLO)
    assert mind is not None
    assert mind.ai == casters.DIABLO
    assert mind.woke
    assert not mind.staggers
    assert mind.delay == 12
    assert mind.radius == rules.AWARE
    assert casters.mind_of(DIABLO) is None
    assert casters.row_of(DIABLO) is None  # combat/harm.py unchanged


def test_the_weights_are_the_clients_tables():
    melee = rules.weights(rules.Sight(melee=True, seen=True, away=2))
    assert melee[rules.SWING] == 40
    assert melee[rules.SMASH] == 70
    assert melee[rules.LIGHTNING] == 40
    assert melee[rules.FIRE] == 14  # fire resisted more than lightning: his fire weighs less
    assert melee[rules.COLD] == 40
    assert melee[rules.WALL] == 15
    assert melee[rules.PRISON] == 0
    seen = rules.weights(rules.Sight(melee=False, seen=True, away=15))
    assert [seen[i] for i in (rules.LIGHTNING, rules.FIRE, rules.WALL, rules.PRISON, rules.RUN, rules.CIRCLE)] == [
        25, 15, 5, 20, 10, 20,
    ]  # fmt: skip
    far = rules.weights(rules.Sight(melee=False, seen=True, away=26))
    assert far[rules.LIGHTNING] == 0
    assert far[rules.RUN] == 20
    assert far[rules.WALL] == 0
    hidden = rules.weights(rules.Sight(melee=False, seen=False, away=10))
    assert hidden[rules.LIGHTNING] == 0
    assert hidden[rules.PRISON] == 40
    assert hidden[rules.POSE] == 5
    # A target that resists lightning more than fire: his fire and wall weigh more.
    turned = rules.weights(rules.Sight(melee=False, seen=True, away=15, fire=70, lightning=80))
    assert turned[rules.FIRE] == 35
    assert turned[rules.WALL] == 25


def test_a_think_draws_over_the_weights():
    roll = random.Random(5)
    found = [rules.choose(rules.weights(rules.Sight(False, True, 15)), roll) for _ in range(20000)]
    assert found.count(rules.LIGHTNING) / len(found) == pytest.approx(25 / 95, abs=0.015)
    assert rules.choose([0] * 17, roll) == rules.IDLE


def duel(distance: float, frames: int, seed: int = 1, move=None):
    walker = Walker(1, DIABLO, 0.0, 0.0)
    pack = Pack([walker], seed=seed)
    taken: dict[int | str, float] = {}
    for frame in range(frames):
        walker.x, walker.y = 0.0, 0.0  # held where he stands: the distance is the test's
        hero = (distance, 0.0) if move is None else move(frame)
        for blow in pack.step(frame, [hero]):
            key = blow.missile or blow.kind
            taken[key] = taken.get(key, 0.0) + sum(v * (1 - STOPPED.get(k, 0.0)) for k, v in blow.parts.items())
    return pack, taken


def test_the_stream_is_one_missile_a_frame_from_its_tenth_frame_each_at_where_the_target_stands():
    pack, _ = duel(15.0, 60 * 25, move=lambda frame: (15.0 * math.cos(frame / 40), 15.0 * math.sin(frame / 40)))
    minds = pack.minds
    starts = [cast[0] for cast in minds.casts if cast[3] == 'DiabLight']
    assert starts
    start = starts[0]
    births = [b for b in minds.births if b[3] == rules.LIGHTNING_MISSILE and start <= b[0] < start + 60]
    assert [b[0] - start for b in births] == list(range(10, 10 + rules.STREAM_MISSILES))
    # Each aimed at the target of its own frame: the target circles, so do the aims.
    for frame, _unit, _txt, _missile, _origin, toward, ends in births:
        assert toward == pytest.approx((15.0 * math.cos(frame / 40), 15.0 * math.sin(frame / 40)))
        assert ends - frame == 39


def test_a_standing_character_loses_what_the_takes_lost_to_a_cast():
    pack, taken = duel(15.0, 120 * 25)
    casts = sum(1 for cast in pack.minds.casts if cast[3] == 'DiabLight')
    assert casts >= 10
    # The takes: 170 to 312 points a cast at a character standing in it (diablo.md section 2).
    assert 150 <= taken[rules.LIGHTNING_MISSILE] / casts <= 320


def test_no_lightning_beyond_his_range():
    pack, taken = duel(28.0, 60 * 25)
    assert not any(cast[3] == 'DiabLight' for cast in pack.minds.casts)
    assert rules.LIGHTNING_MISSILE not in taken


def test_the_price_of_a_stand_and_of_a_step_across():
    protection = threat.Protection(STOPPED)
    assert 180 <= threat.standing_cast(15.0, protection) <= 240
    stream = threat.Stream((0.0, 0.0), age=20)
    hold = threat.stream_points(stream, threat.Way.stand((15.0, 0.0), 0.72), protection)
    across = threat.escapes((0.0, 0.0), (15.0, 0.0), (4.0,))[0]
    step = threat.stream_points(stream, threat.Way((((15.0, 0.0), 0.0, 0.0), (across, 0.2, 0.52))), protection)
    assert hold > 50
    assert step < hold / 3
    # Out of his range or his sight no cast is to come.
    assert threat.future_points((0.0, 0.0), (28.0, 0.0), 2.0, protection) == 0.0
    assert threat.future_points((0.0, 0.0), (15.0, 0.0), 2.0, protection, seen=False) == 0.0
    assert threat.future_points((0.0, 0.0), (15.0, 0.0), 2.0, protection) > 0.0


def test_the_dear_classes_are_the_five_bosses_by_the_clients_class_ids():
    # The player, 2026-10-13: the dearer life price for diablo, baal, nihlathak, mephisto, duriel. Ids are monstats
    # `*hcIdx` (the tables' keys), not row places: nihlathakboss is 526, baalcrab 544.
    from inventory_tracking.combat.harm import DEAR
    from inventory_tracking.combat.mechanics.tables import tables

    names = {txt: tables()['monsters'][str(txt)]['Id'] for txt, _ in DEAR}
    assert set(names.values()) == {
        'duriel', 'uberduriel', 'mephisto', 'ubermephisto', 'diablo', 'diabloclone', 'uberdiablo', 'nihlathakboss',
        'baalcrab', 'baalclone', 'uberbaal',
    }  # fmt: skip
    assert all(factor == 10.0 for _, factor in DEAR)


def test_the_guards_bosses_are_the_boss_rows_by_class_id():
    from inventory_tracking.combat.mechanics.tables import tables
    from inventory_tracking.combat.sim.guard import BOSSES

    rows = tables()['monsters']
    assert {int(txt) for txt, row in rows.items() if row.get('boss') == '1'} <= BOSSES
    assert rows['526']['Id'] == 'nihlathakboss'
    assert 526 in BOSSES
    assert rows['544']['Id'] == 'baalcrab'
    assert 544 in BOSSES
    assert 545 not in BOSSES  # baaltaunt


def test_life_is_dearer_only_while_a_dear_boss_is_in_the_fight():
    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings, life_factor

    settings = SafetySettings()
    assert life_factor(Look((Hostile(1, DIABLO, (10.0, 0.0)),)), (0.0, 0.0), settings) == 10.0
    assert life_factor(Look((Hostile(1, DIABLO, (60.0, 0.0)),)), (0.0, 0.0), settings) == 1.0  # beyond awareness
    assert life_factor(Look((Hostile(1, 310, (10.0, 0.0)),)), (0.0, 0.0), settings) == 1.0
    assert life_factor(Look((Hostile(1, DIABLO, (10.0, 0.0)),)), (0.0, 0.0), SafetySettings(dear=())) == 1.0


def test_harm_prices_his_stream_under_way_and_a_step_across_takes_less():
    from inventory_tracking.combat.harm import Hostile, Look, harm, harm_path

    missiles = tuple((1, (0.88 * k, 0.0), 0.0) for k in range(1, 11))
    casting = Look((Hostile(1, DIABLO, (0.0, 0.0), active=True, mode=threat.MODE, mode_frames=20),), missiles=missiles)
    idle = Look((Hostile(1, DIABLO, (0.0, 0.0), active=True),))
    hold = harm(casting, (15.0, 0.0), 0.72, 'battle')
    assert hold.mean > 100  # raw points, no resistances: most of a stream
    assert DIABLO in hold.stand_ins  # his melee is still the stand-in
    assert harm(idle, (15.0, 0.0), 0.72, 'battle').mean < hold.mean / 4
    across = threat.escapes((0.0, 0.0), (15.0, 0.0), (4.0,))[0]
    step = harm_path(casting, (((15.0, 0.0), 0.2, 'battle'), (across, 0.2, 'battle'), (across, 0.36, 'battle')))
    assert step.mean < hold.mean * 0.7  # 204 against 366 over the common span


def test_his_target_is_read_off_the_newest_missile():
    from inventory_tracking.combat.threats import Acting

    at_it = tuple(((0.88 * k, 0.0), 0.0) for k in range(1, 6))
    elsewhere = tuple(((0.0, 0.88 * k), math.pi / 2) for k in range(1, 6))
    stream, chance = threat._stream(Acting((0.0, 0.0), threat.MODE, 0, at_it), (15.0, 0.0))
    assert stream.age is not None
    assert stream.age >= rules.RELEASE['SC'] + 4  # the farthest has flown 5 frames
    assert chance == 1.0
    stream, _ = threat._stream(Acting((0.0, 0.0), threat.MODE, 0, elsewhere), (15.0, 0.0))
    assert stream.age is None  # aimed at a companion: only the missiles in flight are his price
    _, chance = threat._stream(Acting((0.0, 0.0), threat.MODE, 3), (15.0, 0.0))
    assert chance == rules.CHARACTER_SHARE


def test_a_way_of_a_path_walks_a_walk_and_jumps_a_hop():
    way = threat.Way.along((((0.0, 0.0), 0.3), ((4.0, 0.0), 0.3), ((30.0, 0.0), 0.3)))
    assert way.legs[1] == ((4.0, 0.0), 0.3, 0.0)  # 4 units in 0.3 s: walked
    assert way.legs[2] == ((30.0, 0.0), 0.0, 0.3)  # 26 units in 0.3 s: a jump
    assert all(abs(math.dist(p, (0.0, 0.0)) - 15.0) < 1e-9 for p in threat.escapes((0.0, 0.0), (15.0, 0.0)))
