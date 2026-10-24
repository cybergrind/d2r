"""The approach that the keep range undoes (the player, 2026-10-23: "try to push exp/hour more";
rca/2026-10-23/approach-veto-findings.md): no landing the pack's hop would leave at once (macros/safety.py
PACK_RANGE_LANDING), none at a burner's keep-range edge (BURN_LANDING_MARGIN), and a dance or knot on a Herald pack
passes the whole pack (macros/hunting/judging.py DANCE_PASSES_PACK). Each switch off: as before."""

import math
from types import SimpleNamespace

import pytest

from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.harm import Hostile
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import safety as module
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import choice, judging
from inventory_tracking.macros.travel import STANDING
from tests.inventory_tracking.macros.fakes import player, world


NOBODY = 0xFFFFFFFF
REACH = 22.08  # the strike's (builds/warlock/echoing_strike/attack.py REACH)


@pytest.fixture(autouse=True)
def switched_on(monkeypatch):
    monkeypatch.setattr(module, 'PACK_RANGE_LANDING', True)
    monkeypatch.setattr(module, 'BURN_LANDING_MARGIN', True)
    monkeypatch.setattr(judging, 'DANCE_PASSES_PACK', True)
    monkeypatch.setattr(judging, 'KNOT_PASSES_PLACE', True)


# --- BURN_LANDING_MARGIN: the take 20261022T235916Z-49's approach landed 18-21 off a burner of keep 18 ---


def pricing(here, burning=(), hostiles=(), demons=()):
    """What the two bars read of a look: here, the burners, the hostiles and the demons (None: not attacking)."""
    return SimpleNamespace(here=here, burning=tuple(burning), hostiles=list(hostiles), demons=tuple(demons))


def burns(p, spot) -> bool:
    return module.burns_close(p.here, spot, p.burning, REACH)


def lands(p, spot) -> bool:
    """`Pricing.breaks_range`: never while not attacking (`demons` None)."""
    return p.demons is not None and module.lands_in_range(p.here, spot, p.hostiles, p.demons)


BURNER = manaburn.Burner(1, (5000.0, 5000.0), 18.0)


def test_a_landing_at_the_burner_s_keep_edge_is_barred_one_in_reach_beyond_it_is_not():
    p = pricing((5000.0, 5035.0), [BURNER])
    assert burns(p, (5000.0, 5019.5))  # 1.5 past the keep range: the next look's hop
    assert not burns(p, (5000.0, 5020.5))  # REACH - BURN_SHORT: still a strike from there
    assert math.dist((5000.0, 5020.5), BURNER.at) <= REACH


def test_a_short_keep_range_gets_the_whole_hop_clearance():
    near = manaburn.Burner(1, (5000.0, 5000.0), 10.0)
    p = pricing((5000.0, 5035.0), [near])
    assert burns(p, (5000.0, 5013.0))  # under 10 + HOP_CLEAR
    assert not burns(p, (5000.0, 5014.5))


def test_a_landing_no_nearer_than_here_or_with_the_switch_off_is_not_barred(monkeypatch):
    p = pricing((5000.0, 5019.0), [BURNER])
    assert not burns(p, (5019.0, 5000.0))  # as far as here: sideways, no deeper
    monkeypatch.setattr(module, 'BURN_LANDING_MARGIN', False)
    assert not burns(pricing((5000.0, 5035.0), [BURNER]), (5000.0, 5019.5))


# --- PACK_RANGE_LANDING: the hop's own `why_back` at the landing ---

ARCHERS = [Hostile(10 + k, 174, (5000.0 + dx, 5000.0), tier=5) for k, dx in enumerate((0.0, 2.0, 4.0))]


def test_a_landing_within_the_pack_s_back_range_is_barred_from_one_outside_it(monkeypatch):
    p = pricing((5000.0, 5025.0), hostiles=ARCHERS)
    assert lands(p, (5002.0, 5007.0))
    assert lands(p, (5002.0, 5012.0))  # within PACK_BACK + LEAD_UNITS (combat/pack.py RANGE_LEAD)
    assert not lands(p, (5002.0, 5014.5))
    monkeypatch.setattr(herald_pack, 'RANGE_LEAD', False)
    assert not lands(p, (5002.0, 5012.0))


def test_from_inside_the_range_a_landing_farther_from_the_pack_is_allowed():
    p = pricing((5002.0, 5004.0), hostiles=ARCHERS)
    assert not lands(p, (5002.0, 5008.0))  # out, though still within 10
    assert lands(p, (5002.0, 5003.0))  # deeper


def test_a_pack_held_by_a_demon_does_not_bar_and_not_attacking_or_the_switch_off_neither(monkeypatch):
    held = pricing((5000.0, 5025.0), hostiles=ARCHERS, demons=[(5002.0, 5003.0)])
    assert not lands(held, (5002.0, 5007.0))
    idle = pricing((5000.0, 5025.0), hostiles=ARCHERS)
    idle.demons = None  # not attacking: no keep range
    assert not lands(idle, (5002.0, 5007.0))
    monkeypatch.setattr(module, 'PACK_RANGE_LANDING', False)
    assert not lands(pricing((5000.0, 5025.0), hostiles=ARCHERS), (5002.0, 5007.0))


# --- DANCE_PASSES_PACK: Claw Viper Temple 1, 03:26-03:31: a row of 15 vipers 22 wide behind a closed door ---

ROW = tuple(
    Monster(100 + k, 74, 1, 15117.5 + 3.0 * k, 9587.5, NOBODY, 0x10, life=128, max_life=128, tier=5) for k in range(8)
)
TRAP = Monster(200, 327, 1, 15134.5, 9553.5, NOBODY, 0)  # a trap 34 off: no member


def hunter():
    return SimpleNamespace(knots={}, passed={})


def knot(self, seen, goal: Goal) -> None:
    """A knot's pass of `goal` at clock 100 (`pass_the_knot`) on a stand-in hunter."""
    judging.pass_the_knot(self, seen, goal, 100.0)  # pyrefly: ignore[bad-argument-type] the two ledgers it writes


def viper_goal(unit: Monster) -> Goal:
    return Goal(
        f'the monster 74 ({unit.unit_id})', (unit.x, unit.y), 'fight', 2.0, STANDING, unit.unit_id, clearing=True
    )


def test_a_pass_of_one_viper_passes_its_whole_pack():
    self, seen = hunter(), world(46, player=player(46, x=15120.5, y=9562.5), monsters=(*ROW, TRAP))
    knot(self, seen, viper_goal(ROW[0]))
    assert set(self.passed) == {m.unit_id for m in ROW}  # 21 wide: past KNOT_RADIUS
    assert all(until == 100.0 + choice.PASS_SECONDS for until in self.passed.values())


def test_without_the_switch_the_knot_passes_its_radius_alone(monkeypatch):
    monkeypatch.setattr(judging, 'DANCE_PASSES_PACK', False)
    self, seen = hunter(), world(46, player=player(46, x=15120.5, y=9562.5), monsters=(*ROW, TRAP))
    knot(self, seen, viper_goal(ROW[0]))
    assert set(self.passed) == {m.unit_id for m in ROW if m.x - ROW[0].x <= judging.KNOT_RADIUS}


def test_a_goal_of_no_herald_pack_passes_the_knot_s_radius_alone():
    plain = tuple(Monster(m.unit_id, 74, 1, m.x, m.y, NOBODY, 0x10, life=128, max_life=128) for m in ROW)
    self, seen = hunter(), world(46, player=player(46, x=15120.5, y=9562.5), monsters=plain)
    knot(self, seen, viper_goal(plain[0]))
    assert set(self.passed) == {m.unit_id for m in plain if m.x - plain[0].x <= judging.KNOT_RADIUS}


def test_a_dance_passes_the_pack_only_for_a_herald_pack_s_goal(monkeypatch):
    seen = world(46, player=player(46, x=15120.5, y=9562.5), monsters=(*ROW, TRAP))
    assert set(judging.pack_of(seen, viper_goal(ROW[3]))) == {m.unit_id for m in ROW}  # `no_progress` passes it
    assert judging.pack_of(seen, viper_goal(TRAP)) == []
    monkeypatch.setattr(judging, 'DANCE_PASSES_PACK', False)
    assert judging.pack_of(seen, viper_goal(ROW[3])) == []
