"""The fight's one-cast yields (rca/2026-10-23/fight-yield-findings.md): the landing judged with the pack's lead
(combat/pack.py RANGE_LEAD), the better place priced with the strike gap it costs (moves.py STAND_PAYS_GAP), and no
move for a goal that is no fight while a Herald pack is in reach (judging.py PACK_FIGHT_FIRST)."""

from types import SimpleNamespace

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.combat.stance import Camp
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import judging, moves
from inventory_tracking.macros.hunting.base import Judged
from inventory_tracking.macros.pursuit import Move, Operate
from inventory_tracking.macros.travel import PRESSED, Step
from inventory_tracking.routes.model import USE
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter


# --- RANGE_LEAD: take 20261023T063700Z-19, 09:37:15.7: the place 11.0 off the nearest Hungry Dead, landed 8.0 off ---

PLACE = (10053.5, 6599.5)
HUNGRY = [foe(31 + k, x, y, txt_id=436, tier=5) for k, (x, y) in enumerate(((10053.5, 6610.5), (10060.0, 6612.0)))]


def test_a_place_just_outside_the_back_range_breaks_the_led_range_and_not_without_the_lead(monkeypatch):
    why = pack.breaks_range(PLACE, HUNGRY, [])
    assert why is not None
    assert 'within 14' in why
    assert not pack.range_kept(HUNGRY, [])(PLACE)
    monkeypatch.setattr(pack, 'RANGE_LEAD', False)
    assert pack.breaks_range(PLACE, HUNGRY, []) is None
    assert pack.range_kept(HUNGRY, [])(PLACE)


def test_the_hop_itself_still_fires_at_the_back_range():
    members = pack.members(HUNGRY)
    assert pack.why_back(PLACE, members, []) is None  # 11.0 off: no hop from there
    assert pack.why_back((10053.5, 6602.5), members, []) is not None  # 8.0 off: the hop


def test_a_pack_a_demon_holds_does_not_come_on():
    demon = (10054.0, 6607.0)  # nearer the members than the place is
    assert pack.breaks_range(PLACE, HUNGRY, [demon]) is None


def test_the_hop_lands_first_where_the_members_do_not_reach_by_the_next_look(monkeypatch):
    members = pack.members(HUNGRY)
    here = (10053.5, 6604.0)
    spots = pack.hop_spots(here, members, [])
    clear = [s for s in spots if all(pack.math.dist(s, m.at) >= pack.PACK_BACK + pack.LEAD_UNITS for m in members)]
    assert clear
    assert spots[: len(clear)] == clear
    monkeypatch.setattr(pack, 'RANGE_LEAD', False)
    assert sorted(pack.hop_spots(here, members, [])) == sorted(spots)  # the same spots, in their old order


# --- STAND_PAYS_GAP: a Teleport's 0.30 s priced, 0.84 s without a strike at the median ---


def place(worth: float, here: float, seconds: float = 0.3) -> Camp:
    return Camp((0.0, 0.0), worth, here, seconds, 18.0, hop=True, skill=54)


@pytest.mark.parametrize(
    ('worth', 'seconds', 'pays'),
    [
        (140.0, 0.3, False),  # 1.4 times here: the gap eats the gain
        (170.0, 0.3, True),  # 1.7 times: still worth it
        (169197.0 / 38359.0 * 100.0, 0.3, True),  # 09:37:15.7's 4.4 times
        (150.0, 0.7, False),  # a walk of 0.7 s at 1.5 times
        (80.0, 0.3, True),  # under the gain: a crowd escape, not judged so
        (140.0, 3.5, True),  # past the horizon: as priced
    ],
)
def test_a_better_place_pays_the_strike_gap_or_is_not_offered(monkeypatch, worth, seconds, pays):
    monkeypatch.setattr(moves, 'STAND_PAYS_GAP', True)
    assert moves.pays_the_gap(place(worth, 100.0, seconds), 1.25) is pays


def test_the_gap_switch_off_takes_every_place(monkeypatch):
    monkeypatch.setattr(moves, 'STAND_PAYS_GAP', False)
    assert moves.pays_the_gap(place(140.0, 100.0), 1.25)


# --- PACK_FIGHT_FIRST: 09:37:43.3, "agenda: Super chest" 74 away with the pack in reach ---


@pytest.mark.parametrize(
    ('do', 'reason', 'tier', 'near', 'switch', 'yields'),
    [
        (USE, '', 5, True, True, False),  # the chest waits: the pack in reach
        (USE, 'firing spot', 5, True, True, True),  # a firing spot still goes
        (USE, 'pack: keeping range', 5, True, True, True),  # the safety's hop still goes
        (USE, '', 3, True, True, True),  # a tier 3 pack: as before
        (USE, '', 5, False, True, True),  # the pack out of reach: the chest
        ('fight', '', 5, True, True, True),  # a fight goal's move: as before
        (USE, '', 5, True, False, True),  # the switch off: as before
    ],
)
def test_a_herald_pack_in_reach_keeps_the_fight_from_a_goal_that_is_no_fight(
    monkeypatch, caplog, do, reason, tier, near, switch, yields
):
    monkeypatch.setattr(judging, 'PACK_FIGHT_FIRST', switch)
    monkeypatch.setattr(judging, 'HELD_STRIKES_ON', False)
    judging.PACK_FIRST_SAID.clear()
    member = foe(41, 5012.0 if near else 5040.0, 5000.0, txt_id=436, tier=tier)
    play = game(member)
    hunted = hunter(play)
    monkeypatch.setattr(type(hunted), 'pursuing', property(lambda _self: True))
    run = play.run()
    goal = Goal('agenda: Super chest', (5000.0, 5074.0), do, 4.0, PRESSED)
    found = Judged(Move(Step((5000.0, 5030.0)), goal, reason), goal, goal.place)
    monkeypatch.setattr(hunted, 'judge', lambda *_a, **_k: found)
    monkeypatch.setattr(hunted, 'pursuit', SimpleNamespace(pressed_at=1.0))
    hunted.judged = (1.0, -10.0, False)
    with caplog.at_level('INFO'):
        asks = hunted.key_asks(run, play.world, [member], Ground(()))
    assert asks is yields
    assert ('the fight first (PACK_FIRST)' in caplog.text) is not yields


def test_a_use_waits_too_and_a_passed_pack_does_not_hold_it(monkeypatch):
    monkeypatch.setattr(judging, 'PACK_FIGHT_FIRST', True)
    member = foe(42, 5012.0, 5000.0, txt_id=436, tier=5)
    play = game(member)
    hunted = hunter(play)
    monkeypatch.setattr(type(hunted), 'pursuing', property(lambda _self: True))
    run = play.run()
    goal = Goal('agenda: Super chest', (5003.0, 5000.0), USE, 4.0, PRESSED)
    monkeypatch.setattr(hunted, 'judge', lambda *_a, **_k: Judged(Operate(goal), goal, goal.place))
    monkeypatch.setattr(hunted, 'pursuit', SimpleNamespace(pressed_at=1.0))
    hunted.judged = (1.0, -10.0, False)
    assert not hunted.key_asks(run, play.world, [member], Ground(()))
    hunted.passed[member.unit_id] = run.clock() + 30.0
    hunted.judged = (1.0, -10.0, False)
    assert hunted.key_asks(run, play.world, [member], Ground(()))
