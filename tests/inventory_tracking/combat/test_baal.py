"""sim/baal.py and combat/threats/baal.py: Baal by his tables and the probe's shares (his think is not read), and his
inferno, nova and cold missiles priced for a place (rca/2026-10-14/baal-sim.md)."""

import math

import pytest

from inventory_tracking.combat import threats
from inventory_tracking.combat.sim import baal as rules, casters
from inventory_tracking.combat.sim.monsters import Pack, Walker
from inventory_tracking.combat.threats import baal as threat
from inventory_tracking.combat.threats.diablo import Way
from inventory_tracking.macros.safety import in_flight
from inventory_tracking.macros.world import Monster


BAAL, CLONE, UBER = 544, 570, 709


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
    names = {i: rules.missile(i)['Missile'] for i in (rules.NOVA_MISSILE, rules.INFERNO_MISSILE, rules.COLD_MAKER)}
    assert names == {555: 'baal nova', 554: 'baal inferno', 589: 'baal cold maker'}
    assert rules.level_of(rules.NOVA) == 8  # Sk1lvl 1 + Hell's 7
    assert rules.skill_points(rules.NOVA, 8) == {'fire': (218.0, 243.0)}
    assert rules.skill_points(rules.INFERNO, 8) == {'magic': (50.0, 54.0)}  # HitShift 5
    assert rules.skill_points(rules.COLD, 8) == {'cold': (83.0, 103.0)}
    assert rules.inferno_life(8) == 19  # Param2 12 + level - 1, the Venom Lord's rule (take)
    assert rules.inferno_births(0) == list(range(2, 22, 2))  # 20 frames, one every 2
    assert rules.inferno_reach() == pytest.approx(21.0)
    assert rules.nova_reach() == pytest.approx(38.4)
    assert rules.curse_reach_and_frames(10) == (12.0, 875)


def test_his_acts_come_as_often_as_the_probe_saw_his_modes():
    rates = rules.rates()
    share = {mode: count / sum(rules.LOOKS.values()) for mode, count in rules.LOOKS.items()}
    s3 = (rates['nova'] + rates['curse']) * rules.MODE_FRAMES['S3'] / 25
    a1 = (rates['cold'] + rates['teleport']) * rules.MODE_FRAMES['A1'] / 25
    assert s3 == pytest.approx(share['S3'])
    assert a1 == pytest.approx(share['A1'])
    assert rates['tentacles'] * rules.MODE_FRAMES['S2'] / 25 == pytest.approx(share['S2'])
    assert rates['inferno'] * rules.MODE_FRAMES['SQ'] / 25 == pytest.approx(share['SQ'])
    casting = sum(rate for name, rate in rates.items() if name not in (rules.WALK, rules.IDLE))
    standing = casting * rules.DELAY / 25 + rates[rules.IDLE] * rules.IDLE_FRAMES / 25
    assert standing == pytest.approx(share['NU'])
    assert sum(rules.weights()) == pytest.approx(1.0)


def test_he_thinks_by_this_module_and_harm_still_takes_him_for_unread():
    mind = casters.mind_for(BAAL)
    assert mind is not None
    assert mind.ai == casters.BAAL
    assert not mind.staggers
    assert mind.delay == 12
    assert casters.mind_of(BAAL) is None
    assert casters.mind_for(564) is None  # a tentacle fights as any melee type


def _pack(seed: int, monkeypatch, walks: bool = False) -> Pack:
    if not walks:
        monkeypatch.setattr(rules, 'TELEPORT_NEAR', 1e9)
        monkeypatch.setattr(casters.Minds, '_set_walk', lambda self, walker, frame, **_: self._idle(walker, frame, 12))
    return Pack([Walker(1, BAAL, 0.0, 0.0)], seed=seed)


def test_a_minute_of_him_casts_every_act_and_raises_tentacles_by_his_target(monkeypatch):
    pack = _pack(1, monkeypatch)
    raised = []
    for frame in range(60 * 25):
        pack.step(frame, [(16.0, 0.0)])
        raised += pack.minds.summons
        pack.minds.summons = []
    skills = {cast[3] for cast in pack.minds.casts}
    assert {rules.NOVA, rules.INFERNO, rules.COLD, rules.TENTACLES} <= skills
    assert raised
    assert all(summon.txt in (564, 565) for summon in raised)
    assert all(4.0 - 1e-6 <= math.dist(summon.at, (16.0, 0.0)) <= 11.0 + 1e-6 for summon in raised)
    assert all(summon.lasts == 15 * 25 for summon in raised)


def test_a_standing_character_takes_the_probes_fall_of_an_inferno(monkeypatch):
    """[probe] 87 to 121 (median 94) in the 1.5 s after a look saw him in his inferno, 14 to 19 units off."""
    taken, streams = 0.0, 0
    for seed in range(1, 6):
        pack = _pack(seed, monkeypatch)
        for frame in range(60 * 25):
            taken += sum(b.damage for b in pack.step(frame, [(16.0, 0.0)]) if b.missile == rules.INFERNO_MISSILE)
            pack.minds.summons = []
        streams += sum(1 for cast in pack.minds.casts if cast[3] == rules.INFERNO)
    assert streams
    assert 80 <= taken / streams <= 110
    assert threat.standing(16.0)['inferno'] == pytest.approx(taken / streams, rel=0.1)


def test_the_clone_splits_off_once_under_the_life_it_came_at(monkeypatch):
    monkeypatch.setattr(rules, 'CLONE_CHANCE', 1.0)
    pack = _pack(2, monkeypatch)
    walker = pack.walkers[1]
    walker.health = rules.CLONE_BELOW - 0.01
    clones = []
    for frame in range(10 * 25):
        pack.step(frame, [(16.0, 0.0)])
        clones += [s for s in pack.minds.summons if s.txt == rules.CLONE]
        pack.minds.summons = []
    assert len(clones) == 1
    assert clones[0].lasts is None  # gone with him
    assert casters.mind_for(CLONE) is not None


# -- the threat model ---------------------------------------------------------------------------------------------


def test_the_model_is_keyed_on_his_skills():
    assert threats.of(BAAL) is threat.THREAT
    assert threats.of(CLONE) is threat.THREAT
    assert threats.of(UBER) is threat.THREAT
    assert threats.of(564) is None
    assert threats.missiles({BAAL}) == {554, 555, 589}


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


def test_the_look_carries_each_missiles_class_and_old_three_part_ones_still_read():
    baal = Monster(7, BAAL, 1, 0.0, 0.0, 0xFFFFFFFF, 8, False, 100, 100)
    read = ((7, 554, 5.0, 0.0), (7, 555, 0.0, 9.0), (7, 172, 1.0, 1.0))
    found = in_flight([baal], None, read)
    assert [(owner, kind) for owner, _, _, kind in found] == [(7, 554), (7, 555)]
    flying, kinds = threats.flying_of(found, 7)
    assert kinds == (554, 555)
    assert flying[0] == ((5.0, 0.0), 0.0)
    assert threats.flying_of(((7, (1.0, 0.0), 0.0),), 7) == ((((1.0, 0.0), 0.0),), (None,))
