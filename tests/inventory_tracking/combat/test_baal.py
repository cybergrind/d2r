"""sim/baal.py and combat/threats/baal.py: Baal by his think as read in the client (rca/2026-10-14/re/baal-ai.md),
his tables, and his inferno, nova and cold missiles priced for a place (rca/2026-10-14/baal-sim.md)."""

import math
import random

import pytest

from inventory_tracking.combat import threats
from inventory_tracking.combat.sim import baal as rules, casters
from inventory_tracking.combat.sim.monsters import Pack, Walker
from inventory_tracking.combat.threats import baal as threat
from inventory_tracking.combat.threats.diablo import Way
from inventory_tracking.macros.game.records import Monster
from inventory_tracking.macros.safety import in_flight


BAAL, CLONE, UBER = 544, 570, 709
CHARACTER = (16.0, 0.0)


def test_his_rows_skills_and_missiles_are_the_tables():
    assert rules.is_baal(BAAL)
    assert rules.is_baal(CLONE)
    assert not rules.is_baal(UBER)  # another AI: priced by the model (his skills), not played here
    assert all(rules.casts_baals(txt) for txt in (BAAL, CLONE, UBER))
    assert not rules.casts_baals(564)  # a tentacle
    row = rules.row(BAAL)
    assert row is not None
    assert [row[f'Skill{n}'] for n in range(1, 8)] == [
        'Baal Nova', 'Baal Inferno', 'Baal Tentacle', 'Baal Cold Missiles', 'Baal Teleport', 'Defense Curse',
        'Blood Mana',
    ]  # fmt: skip
    kept = (rules.NOVA_MISSILE, rules.INFERNO_MISSILE, rules.COLD_MAKER, rules.COLD_TRAIL)
    names = {i: rules.missile(i)['Missile'] for i in kept}
    assert names == {555: 'baal nova', 554: 'baal inferno', 589: 'baal cold maker', 590: 'baal cold trail'}
    assert rules.level_of(rules.NOVA) == 8  # Sk1lvl 1 + Hell's 7
    assert rules.skill_points(rules.NOVA, 8) == {'fire': (218.0, 243.0)}
    assert rules.skill_points(rules.INFERNO, 8) == {'magic': (50.0, 54.0)}  # HitShift 5
    assert rules.skill_points(rules.COLD, 8) == {'cold': (83.0, 103.0)}
    assert rules.inferno_life(8) == 19  # Param2 12 + level - 1, the Venom Lord's rule (take)
    assert rules.inferno_births(0) == list(range(11, 21))  # the do event at frame 11, the stream's end at Param1 20
    assert rules.inferno_reach() == pytest.approx(21.0)
    assert rules.nova_reach() == pytest.approx(38.4)
    assert len(rules.ring_headings()) == 64  # [code] ai_d2_missile_nova_ring
    assert rules.curse_reach_and_frames(10) == (12.0, 875)
    assert row['A2MaxD(H)'] == '240'  # his smash in melee


def sight(**more) -> rules.Sight:
    found = {'melee': False, 'seen': True, 'away': 15.0, 'life': 1.0, 'candidates': 4, 'best': 61.0}
    found.update(more)
    return rules.Sight(**found)


def test_his_weights_are_the_codes():
    """[code] ai_d2_ai_baal_decide_in_sight: Hell, in sight, out of melee; 0..15 = none, idle, walk in 12, round the
    target, roam 16, home, walk in 12, -, curse, tentacles, smash, nova, inferno, cold, teleport, clone."""
    assert rules.weights(sight()) == [0, 100, 5, 5, 5, 0, 5, 0, 70, 40, 0, 70, 80, 85, 20, 20]
    half = rules.weights(sight(life=0.4, best=10.0, clones=1, candidates=2))
    assert half == [0, 160, 5, 5, 5, 0, 5, 0, 40, 40, 0, 70, 80, 60, 20, 10]
    assert rules.weights(sight(clones=2))[15] == 0
    far = rules.weights(sight(away=30.0))
    assert (far[11], far[13], far[14]) == (0, 85, 30)  # no nova beyond 25, teleport 30
    farther = rules.weights(sight(away=40.0))
    assert (farther[6], farther[11], farther[13], farther[14]) == (15, 0, 25, 30)  # cold 0 beyond 35, then + 25
    alone = rules.weights(sight(candidates=1))
    assert (alone[8], alone[11]) == (0, 60)
    melee = rules.weights(sight(melee=True, life=0.5))
    assert melee == [0, 100, 0, 0, 0, 0, 0, 0, 20, 30, 150, 10, 10, 70, 40, 0]
    assert rules.weights(sight(melee=True, target_life=0.2))[10] == 200
    chilled = rules.weights(sight(melee=True, chilled=True))
    assert (chilled[8], chilled[11], chilled[13]) == (0, 0, 0)
    assert rules.weights(sight(seen=False))[:10] == [0, 100, 20, 20, 20, 0, 20, 0, 80, 70]


def test_the_draw_follows_the_weights_and_falls_back_on_the_idle():
    roll = random.Random(3)
    found = [rules.choose(rules.weights(sight()), roll) for _ in range(20000)]
    total = sum(rules.weights(sight()))
    assert found.count(12) / len(found) == pytest.approx(80 / total, abs=0.01)
    assert found.count(15) / len(found) == pytest.approx(20 / total, abs=0.01)
    assert rules.choose([0] * 16, roll) == 1  # an empty sum: no index passes the roll, the idle
    assert rules.choose([-5] + [0] * 15, roll) == 1


def test_his_acts_a_second_come_from_the_weights():
    rates = rules.rates(16.0, 4, 1.0)
    assert sum(rates.values()) == pytest.approx(1.0)  # one think a second
    assert rates['inferno'] == pytest.approx(80 / sum(rules.weights(sight())))
    assert 'nova' not in rules.rates(30.0, 4, 1.0)


def test_he_thinks_by_this_module_and_harm_still_takes_him_for_unread():
    mind = casters.mind_for(BAAL)
    assert mind is not None
    assert mind.ai == casters.BAAL
    assert not mind.staggers
    assert mind.delay == 12
    assert mind.radius == 1020  # [code] his target search: the act within 1020
    assert casters.mind_of(BAAL) is None
    assert casters.mind_for(564) is None  # a tentacle fights as any melee type


def test_he_aims_at_the_character_once_it_hits_him_and_else_by_the_score():
    walker = Walker(1, BAAL, 0.0, 0.0)
    assert walker.mind is not None

    def sees(_walker, _at):
        return True

    near = [CHARACTER, (3.0, 0.0)]  # a companion in his melee
    assert rules.aim(walker, near, 100, sees)[0] == 1  # 500 against 375: the companion
    assert rules.aim(walker, [CHARACTER, (14.0, 2.0)], 100, sees)[0] == 0  # a tie keeps the character
    walker.struck, walker.health = 90, 0.99
    rules._threat(walker, 100)
    index, best = rules.aim(walker, near, 100, sees)
    assert (index, best > rules.CURSE_BEST) == (0, True)
    rules._threat(walker, 90 + rules.THREAT_FRAMES + 1)  # ten seconds without a hit: the threat lapses
    assert rules.aim(walker, near, 400, sees)[0] == 1
    assert rules.distance_factor(0.0) == 100
    assert rules.distance_factor(25.0) == pytest.approx(25.6, abs=0.1)
    assert rules.distance_factor(50.0) == 0


def test_his_teleport_lands_in_his_own_room():
    home = (100.0, 100.0)
    assert rules.room_of(home, home) == (85.0, 100.0)  # his place at (135, 160) of the Chamber: room x 120..160
    roll = random.Random(1)
    spots = [rules.teleport_spot(home, home, roll, lambda spot: True) for _ in range(200)]
    assert all(s is not None and 86 <= s[0] <= 124 and 101 <= s[1] <= 139 for s in spots)
    assert rules.teleport_spot(home, home, roll, lambda spot: False) is None


def test_the_cold_cast_is_one_maker_shedding_trails_across_its_line():
    found = rules.cold_missiles((0.0, 0.0), 0.0)
    maker = found[0]
    assert (maker[0], maker[2]) == (0, (1.0, 0.0))
    trails = found[1:]
    assert len(trails) % 2 == 0
    assert 60 <= len(trails) <= 100
    assert {t[2] for t in trails} == {(-0.0, 1.0), (0.0, -1.0)}
    assert max(t[0] for t in trails) < rules.cold_life()


def _pack(seed: int, monkeypatch, walks: bool = False) -> Pack:
    if not walks:
        monkeypatch.setattr(rules, 'teleport_spot', lambda *_: None)
        monkeypatch.setattr(casters.Minds, '_set_walk', lambda self, walker, frame, **_: self._idle(walker, frame, 12))
    pack = Pack([Walker(1, BAAL, 0.0, 0.0)], seed=seed)
    return pack


def _struck(pack: Pack, frame: int) -> None:
    """The character hits him every half second (his threat state on it holds)."""
    if frame % 12 == 0:
        walker = pack.walkers[1]
        walker.struck, walker.health = frame, max(walker.health - 0.002, 0.05)


def test_a_minute_of_him_thinks_once_a_second_and_raises_tentacles_round_his_target(monkeypatch):
    pack = _pack(1, monkeypatch)
    raised = []
    for frame in range(60 * 25):
        _struck(pack, frame)
        pack.step(frame, [CHARACTER])
        raised += pack.minds.summons
        pack.minds.summons = []
    assert len(pack.minds.thoughts) == 60
    skills = {cast[3] for cast in pack.minds.casts}
    assert {rules.NOVA, rules.INFERNO, rules.COLD, rules.TENTACLES} <= skills
    tentacles = [s for s in raised if s.txt != CLONE]
    casts = sum(1 for cast in pack.minds.casts if cast[3] == rules.TENTACLES)
    assert 4 * casts <= len(tentacles) <= 6 * casts
    assert all(summon.txt in (564, 565) for summon in tentacles)
    assert all(abs(s.at[0] - 16.0) <= 9 and abs(s.at[1]) <= 9 for s in tentacles)
    assert all(summon.lasts == 15 * 25 for summon in tentacles)


def test_a_standing_character_takes_the_probes_fall_of_an_inferno(monkeypatch):
    """[probe] 87 to 121 (median 94) in the 1.5 s after a look saw him in his inferno, 14 to 19 units off."""
    taken, streams = 0.0, 0
    for seed in range(1, 6):
        pack = _pack(seed, monkeypatch)
        for frame in range(60 * 25):
            _struck(pack, frame)
            taken += sum(b.damage for b in pack.step(frame, [CHARACTER]) if b.missile == rules.INFERNO_MISSILE)
            pack.minds.summons = []
        streams += sum(1 for cast in pack.minds.casts if cast[3] == rules.INFERNO)
    assert streams
    assert 80 <= taken / streams <= 110
    assert threat.standing(16.0)['inferno'] == pytest.approx(taken / streams, rel=0.1)


def test_the_clone_comes_by_the_draw_one_at_a_time_with_a_third_of_his_life(monkeypatch):
    monkeypatch.setattr(rules, 'choose', lambda weights, roll: 15)
    pack = _pack(2, monkeypatch)
    walker = pack.walkers[1]
    walker.health = 0.9  # no threshold: any life
    clones = []
    for frame in range(5 * 25):
        pack.step(frame, [CHARACTER])
        clones += [s for s in pack.minds.summons if s.txt == rules.CLONE]
        pack.minds.summons = []
        if clones and len(pack.walkers) == 1:
            pack.walkers[2] = Walker(2, CLONE, *clones[0].at)  # the holder of the pack puts it in
            pack.rolls[2] = random.Random(clones[0].seed)
    assert len(clones) == 1  # not while it lives
    (clone,) = clones
    assert clone.lasts is None  # gone with him
    assert (clone.share, clone.most) == pytest.approx((0.3, 1 / 3))
    assert abs(clone.at[0] - 16.0) <= 12
    assert abs(clone.at[1]) <= 12
    assert walker.mind is not None
    assert walker.mind.clones == 1
    assert casters.mind_for(CLONE) is not None


def test_the_clone_walks_where_he_would_raise_tentacles_teleport_or_clone(monkeypatch):
    monkeypatch.setattr(rules, 'choose', lambda weights, roll: 9)
    pack = Pack([Walker(1, CLONE, 0.0, 0.0)], seed=1)
    for frame in range(3 * 25):
        pack.step(frame, [CHARACTER])
    assert {t[2] for t in pack.minds.thoughts} == {'approach'}
    assert not pack.minds.summons


# -- the threat model ---------------------------------------------------------------------------------------------


def test_the_model_is_keyed_on_his_skills():
    assert threats.of(BAAL) is threat.THREAT
    assert threats.of(CLONE) is threat.THREAT
    assert threats.of(UBER) is threat.THREAT
    assert threats.of(564) is None
    assert threats.missiles({BAAL}) == {554, 555, 589, 590}  # the cold maker and its trails


def test_his_inferno_reaches_21_units_and_nothing_beyond():
    assert threat.standing(16.0)['inferno'] > 50
    assert threat.standing(23.0)['inferno'] > 0  # the missile's end, within contact
    assert threat.standing(24.0)['inferno'] == 0
    assert threat.standing(40.0)['nova'] > 0
    assert threat.standing(42.0)['nova'] == 0


def test_an_inferno_under_way_is_priced_and_a_step_out_of_its_reach_takes_less():
    acting = threats.Acting((0.0, 0.0), threat.SQ, 0)
    hold = threat.exposure(acting, (((16.0, 0.0), 2.0),))
    out = threat.exposure(acting, (((16.0, 0.0), 0.0), ((24.5, 0.0), 0.45), ((24.5, 0.0), 1.55)))

    def stream(parts):
        return sum(sum(v for _, v in p.points) * p.casts * p.chance for p in parts if p.begins == 0.0)

    assert stream(hold) > 80
    assert stream(out) < stream(hold) / 2
    assert all(kind == 'magic' for p in hold if p.begins == 0.0 for kind, _ in p.points)


def test_out_of_his_inferno_is_offered_beyond_its_reach_and_across_only_while_it_flies_at_the_character():
    here = (16.0, 0.0)
    assert threat.offered(threats.Acting((0.0, 0.0), 1, 0), here) == ()  # neutral, nothing in flight
    places = threat.offered(threats.Acting((0.0, 0.0), threat.SQ, 3), here)
    assert len(places) == 1
    ((place, why),) = places
    assert why == "out of Baal's inferno"
    assert math.dist(place, (0.0, 0.0)) > rules.inferno_reach() + threat.CONTACT
    at = threats.Acting((0.0, 0.0), threat.SQ, 8, (((5.0, 0.0), 0.0),), (rules.INFERNO_MISSILE,))
    found = threat.offered(at, here)
    assert sum(1 for _, why in found if why == "across Baal's inferno") == 4
    elsewhere = threats.Acting((0.0, 0.0), threat.SQ, 8, (((0.0, 5.0), math.pi / 2),), (rules.INFERNO_MISSILE,))
    assert threat.offered(elsewhere, here) == ()
    assert threat.offered(threats.Acting((0.0, 0.0), threat.SQ, 3), (30.0, 0.0)) == ()  # beyond its reach


def test_a_nova_ring_in_flight_is_priced_once_when_it_passes():
    ring = tuple(
        ((10.0 * math.cos(h), 10.0 * math.sin(h)), h) for h in rules.ring_headings()[::8]
    )  # eight of its missiles
    kinds = (rules.NOVA_MISSILE,) * len(ring)
    parts = threat.exposure(threats.Acting((0.0, 0.0), threat.S3, 15, ring, kinds), (((16.0, 0.0), 1.0),))
    now = [p for p in parts if p.begins == 0.0]
    assert len(now) == 1
    assert sum(v for _, v in now[0].points) == pytest.approx(230.5)
    assert threat.ring_points((0.0, 0.0), 10.0, Way.stand((60.0, 0.0), 2.0)) == 0.0


def test_a_cold_cast_takes_once_from_a_body_in_its_band_and_none_beyond():
    hit = rules.mean_points(rules.COLD, rules.level_of(rules.COLD))['cold']
    assert threat.standing(16.0)['cold'] == pytest.approx(hit)  # maker and trails: once a cast
    maker = (((5.0, 0.0), 0.0),)  # flying along +x, 5 units out
    assert threat.cold_points((0.0, 0.0), maker, Way.stand((16.0, 8.0), 2.0)) == pytest.approx(hit)  # a trail
    assert threat.cold_points((0.0, 0.0), maker, Way.stand((16.0, 17.0), 2.0)) == 0.0  # beyond the band
    assert threat.cold_points((0.0, 0.0), maker, Way.stand((-8.0, 0.0), 2.0)) == 0.0  # behind him


def test_the_look_carries_each_missiles_class_and_old_three_part_ones_still_read():
    baal = Monster(7, BAAL, 1, 0.0, 0.0, 0xFFFFFFFF, 8, False, 100, 100)
    read = ((7, 554, 5.0, 0.0), (7, 555, 0.0, 9.0), (7, 172, 1.0, 1.0))
    found = in_flight([baal], None, read)
    assert [(owner, kind) for owner, _, _, kind in found] == [(7, 554), (7, 555)]
    flying, kinds = threats.flying_of(found, 7)
    assert kinds == (554, 555)
    assert flying[0] == ((5.0, 0.0), 0.0)
    assert threats.flying_of(((7, (1.0, 0.0), 0.0),), 7) == ((((1.0, 0.0), 0.0),), (None,))
