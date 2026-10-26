"""The T5 Herald pack's engagement plan (combat/engage.py ENGAGE_PLAN; rca/2026-10-26/herald-engage-findings.md). The
player, 2026-10-26 ~09:10: "teleport to safe spot, once; move daemons to get aggro with DM between char and pack; walk
closer, behind the daemons that gets aggro; put sigil of lethargy where the main battle will occur; deliver damage".

The flip-flop of take 20261025T000028Z-117 at 03:01:04-09 (findings §1.3): a firing-spot Teleport toward the pack,
0.4 s later the keep range's hop back, 2 s later the firing spot again, then the keep range again: the plan holds both
once the demons hold the pack."""

import math
from types import SimpleNamespace

import pytest

from inventory_tracking.combat import engage, pack


HERE = (5000.0, 5000.0)
HERALD = SimpleNamespace(unit=1, at=(5020.0, 5000.0), tier=5, flags=0x08)
MINIONS = [SimpleNamespace(unit=2 + i, at=(5021.0 + i, 5002.0 - i), tier=5, flags=0x10) for i in range(4)]
PACK = [HERALD, *MINIONS]
BY_US = [(5000.8, 5000.0), (5000.0, 5001.0)]  # the demons at the character's feet (a jump brought them)
ON_THE_PACK = [(5018.5, 5001.0), (5019.0, 4999.0)]  # 1-2 off the near members, 18-19 off the character


@pytest.fixture(autouse=True)
def plan_on(monkeypatch):
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', True)
    pack.FIRST.add(-1)
    yield
    pack.FIRST.discard(-1)


def look(now, here=HERE, members=PACK, companions=BY_US, demons=True) -> engage.Plan:
    """The live plan after one look (asserted live)."""
    pack.engage_look(now, here, members, companions, demons)
    plan = engage.active()
    assert plan is not None
    return plan


def look_none(now, members=PACK) -> engage.Plan | None:
    pack.engage_look(now, HERE, members, BY_US, True)
    return engage.active()


def test_off_there_is_no_plan(monkeypatch):
    monkeypatch.setattr(engage, 'ENGAGE_PLAN', False)
    assert look_none(1.0) is None
    assert engage.holds_jump(pack.PLACE) is None
    assert engage.remark() is None
    assert not engage.lifts_range()


def test_a_pack_at_range_begins_at_the_mark_and_no_voluntary_jump_is_made():
    plan = look(10.0)
    assert plan is not None
    assert plan.phase is engage.Phase.MARK
    assert engage.remark() is True
    assert engage.holds_jump(pack.PLACE) is not None  # the firing spot's Teleport
    assert engage.holds_jump(pack.KEEP) is not None  # the keep range's hop
    assert engage.holds_jump(pack.RETREAT) is None  # the safety's danger moves are its own


def test_the_mark_landed_the_walk_in_holds_the_jumps_and_the_re_marks():
    look(10.0)
    pack.keyed(-1, 10.2)
    look(10.4, companions=ON_THE_PACK)  # under MARK_LANDS: still MARK
    assert engage.PLAN.phase is engage.Phase.MARK
    assert engage.remark() is True  # the plan's own key is out: mark.py waits for it (`plan_mark`)
    plan = look(10.2 + engage.MARK_LANDS + 0.05, companions=ON_THE_PACK)
    assert plan.phase is engage.Phase.CLOSE_IN
    assert engage.remark() is False  # no re-mark while the demons hold the pack
    assert engage.lifts_range()
    assert engage.walks()
    assert engage.holds_jump(pack.PLACE) is not None
    assert engage.holds_jump(pack.KEEP) is not None


def test_the_pack_on_the_character_lets_one_jump_out_then_the_mark():
    close = [SimpleNamespace(unit=m.unit, at=(m.at[0] - 14.0, m.at[1]), tier=5, flags=m.flags) for m in PACK]
    plan = look(20.0, members=close)  # the nearest 6 off, on the character
    assert plan.phase is engage.Phase.STANDOFF
    assert engage.holds_jump(pack.KEEP) is None  # the one jump out
    assert engage.holds_jump(pack.PLACE) is None
    pack.hopped(20.5, 16.0)
    plan = look(20.6, here=(4985.0, 5000.0), members=close)
    assert plan.phase is engage.Phase.MARK
    assert plan.jumps == 1
    assert plan.danger == 0
    assert engage.holds_jump(pack.PLACE) is not None  # once


def test_a_danger_jump_takes_the_demons_along_and_the_plan_resumes_at_the_mark():
    look(30.0)
    pack.keyed(-1, 30.1)
    look(30.6, companions=ON_THE_PACK)
    assert engage.PLAN.phase is engage.Phase.CLOSE_IN
    pack.hopped(31.0, 20.0)  # the safety's retreat (a real threat)
    plan = look(31.1, here=(4980.0, 5000.0))
    assert plan.phase is engage.Phase.MARK
    assert plan.danger == 1
    assert engage.remark() is True
    assert 'took the demons along' in plan.remarks[-1]


def test_a_short_jump_takes_nobody_along():
    look(30.0)
    pack.keyed(-1, 30.1)
    look(30.6, companions=ON_THE_PACK)
    pack.hopped(31.0, 2.5)
    assert look(31.1, companions=ON_THE_PACK).phase is engage.Phase.CLOSE_IN


def test_the_mark_again_only_when_the_demons_lost_the_pack():
    look(40.0)
    pack.keyed(-1, 40.1)
    look(40.6, companions=ON_THE_PACK)
    look(41.0, companions=ON_THE_PACK)
    assert engage.remark() is False
    apart = [(5005.0, 4990.0), (5006.0, 4991.0)]  # 11 off the character, none near a member: holding nobody
    look(41.2, companions=apart)
    assert engage.PLAN.phase is engage.Phase.CLOSE_IN  # not at the first look
    plan = look(41.2 + engage.LOST_SECONDS + 0.05, companions=apart)
    assert plan.phase is engage.Phase.MARK
    assert 'no demon on the pack' in plan.remarks[-1]


def test_the_pack_on_the_character_brings_the_mark_back():
    look(50.0)
    pack.keyed(-1, 50.1)
    look(50.6, companions=ON_THE_PACK)
    on_us = [*PACK, SimpleNamespace(unit=9, at=(5004.0, 5000.0), tier=5, flags=0x10),
             SimpleNamespace(unit=10, at=(5003.0, 5003.0), tier=5, flags=0x10)]  # fmt: skip
    look(50.8, members=on_us, companions=ON_THE_PACK)
    plan = look(50.8 + engage.PRESS_SECONDS + 0.05, members=on_us, companions=ON_THE_PACK)
    assert plan.phase is engage.Phase.MARK
    assert 'on the character' in plan.remarks[-1]


def test_close_enough_to_the_melee_is_the_strike():
    look(60.0)
    pack.keyed(-1, 60.1)
    look(60.6, companions=ON_THE_PACK)
    plan = look(61.0, here=(5008.0, 5000.0), companions=ON_THE_PACK)
    assert plan.phase is engage.Phase.STRIKE
    assert engage.holds_jump(pack.PLACE) is not None


def test_the_sigil_goes_where_the_demons_meet_the_pack():
    look(70.0)
    assert engage.sigil_waits()  # MARK: the melee is not there yet
    pack.keyed(-1, 70.1)
    look(70.6, companions=ON_THE_PACK)
    points = [m.at for m in PACK]
    spot = engage.sigil_at(points, HERE, ON_THE_PACK)
    assert spot is not None
    held = [p for p in points if any(math.dist(p, c) <= engage.HOLDS for c in ON_THE_PACK)]
    middle = (sum(p[0] for p in held) / len(held), sum(p[1] for p in held) / len(held))
    assert spot == pytest.approx(middle)
    assert not engage.sigil_waits()
    assert engage.sigil_kept((spot[0] + 1.0, spot[1]), points, HERE, ON_THE_PACK) is True
    assert engage.sigil_kept((5010.0, 4990.0), points, HERE, ON_THE_PACK) is False  # a random place: laid again
    found, why = pack.sigil_spot(HERE, pack.members(PACK), ON_THE_PACK, 5.5)
    assert found == pytest.approx(middle)
    assert 'demons hold' in why


def test_a_walk_that_does_not_get_on_is_let_one_jump():
    far = [SimpleNamespace(unit=m.unit, at=(m.at[0] + 10.0, m.at[1]), tier=5, flags=m.flags) for m in PACK]
    holding = [(c[0] + 10.0, c[1]) for c in ON_THE_PACK]
    look(80.0, members=far)
    pack.keyed(-1, 80.1)
    look(80.6, members=far, companions=holding)
    for t in (81.0, 81.6, 82.2, 82.8, 83.2):
        plan = look(t, members=far, companions=holding)
    assert plan.stuck_jump
    assert engage.holds_jump(pack.PLACE) is None
    assert engage.holds_jump(pack.KEEP) is not None


def test_the_plan_ends_when_the_pack_is_gone():
    look(90.0)
    look(91.0, members=[])
    assert engage.active() is not None
    assert look_none(91.0 + engage.PLAN_GONE, members=[]) is None


def test_the_pack_held_lifts_the_keep_range_off_a_walk_behind_the_demons():
    look(100.0)
    pack.keyed(-1, 100.1)
    look(100.6, companions=ON_THE_PACK)
    assert pack.walk_free((5006.0, 5000.0), HERE, PACK, ON_THE_PACK)  # 12 off the melee, behind the demons
    assert not pack.walk_free((5016.0, 5000.0), HERE, PACK, ON_THE_PACK)  # into the melee
    kept = pack.range_kept(PACK, ON_THE_PACK, HERE, math.inf)
    assert kept((5006.0, 5000.0))
    assert not kept((5017.0, 5000.0))


def test_the_safety_hold_says_the_plan_and_a_real_threat_lifts_it():
    look(110.0)
    hold = pack.jump_hold(110.1, HERE, PACK, BY_US)
    said = pack.held(hold, (5010.0, 5000.0), pack.PLACE)
    assert said is not None
    assert 'ENGAGE_PLAN' in said
    threat = pack.jump_hold(110.2, HERE, PACK, BY_US, exempt='surrounded: 3 within 5')
    assert pack.held(threat, (5010.0, 5000.0), pack.PLACE) is None
    assert pack.held(threat, (4985.0, 5000.0), pack.KEEP) is None


def test_a_real_threat_sets_the_plan_aside_for_a_while():
    # The canyon gate, 2026-10-26: under the Slingers' javelins the plan's mark after every danger jump raised the
    # deaths 6 -> 14 of 80; with a real threat seen the mark, the sigil and the walks are the rules' as before
    look(120.0)
    assert engage.remark() is True
    pack.jump_hold(120.1, HERE, PACK, BY_US, exempt='shooters')
    assert engage.stands_aside()
    assert engage.remark() is None
    assert not engage.sigil_waits()
    look(120.1 + engage.THREAT_SECONDS + 0.2)
    assert not engage.stands_aside()
    assert engage.remark() is True
