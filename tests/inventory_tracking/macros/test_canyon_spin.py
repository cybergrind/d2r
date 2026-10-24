"""The canyon spin (rca/2026-10-24/canyon-spin-findings.md; the player: "exp/hour, never die", "the loop must never
stand still"), replayed on the look of 15:43:21.70 cut from take 20261024T124212Z-68 (Tal Rasha's Tomb): the run's way
out, Canyon of the Magi 153 units north, lies past a room whose south wall an idle tier 5 Herald pack of 15 Steel
Weevils (scarab4) walks along, 16-26 off. Every landing toward the way out lay within PACK_BACK + LEAD_UNITS of a
member (macros/safety.py PACK_RANGE_LANDED); the retreat and the safe approach undid each other for 292 s, until the
runner's 300 s watchdog stopped the loop.

The looks are priced as the game prices them (test_herald_pricing.py), closed: the character stands where the last
look's move landed, the pack where the take read it (it never came), 0.4 s a look. RANGE_STALL_LIFT off: the spin, the
character kept south of the doorway; on: after RANGE_STALL_SECONDS the bar is lifted for the way and the move to the
way out is made."""

import json
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Loot, Monster
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.routes.model import ENTER
from tests.inventory_tracking.macros.fakes import player, world
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, FULL_BELT


EXIT = (22618.5, 8007.5)  # Canyon of the Magi: the route's way out
DOORWAY = 8145.5  # the room's south wall: past it, the character is out of the corridor (no missile flies through)
HOP = 31.2  # units of the take's way toward the exit (15:43:21.70: to (22616.4, 8129.3) from (22618.5, 8160.5))
LOOK = 0.4  # seconds a look (the take: 531 looks in 292 s, 0.55 s)
START = 10.0


SNAP = json.loads((FIXTURES / 'canyon-spin.json').read_text(encoding='utf-8'))
MONSTERS = tuple(
    Monster(
        m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
        life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
    )
    for m in SNAP['monsters']
)  # fmt: skip
GOAL = Goal('Canyon of the Magi', EXIT, ENTER, 2.0, STANDING, route='exit')


@pytest.fixture(autouse=True)
def switched(monkeypatch):
    monkeypatch.setattr(module, 'PACK_RANGE_LANDING', True)


def toward(here: tuple[float, float]) -> Step:
    """The navigator's next Teleport toward the way out: HOP units along the straight line."""
    gap = math.dist(here, EXIT)
    share = min(HOP / gap, 1.0)
    return Step((here[0] + (EXIT[0] - here[0]) * share, here[1] + (EXIT[1] - here[1]) * share), TELEPORT)


def look_at(safety: module.Safety, here: tuple[float, float], now: float) -> tuple[p.Act, dict]:
    """The act the safety and the arbiter choose with the character at `here` at clock `now`, and the record."""
    me = player(SNAP['area'], x=here[0], y=here[1])
    alive = world(SNAP['area'], player=me, monsters=MONSTERS)
    foes = [m for m in MONSTERS if not m.ally and m.owner == NO_OWNER]
    companions = [m for m in MONSTERS if m.ally or m.owner != NO_OWNER]
    build = ECHOING_STRIKE_BUILD
    attack, settings = build.attack, build.settings.safety
    assert attack is not None
    seen = attack.sees(observe(me, foes, companions), companions)
    loot = Loot(
        life=SNAP['player']['life'],
        max_life=SNAP['player']['max_life'],
        stats=tuple((stat, value) for stat, value in SNAP['stats']),
        belt=FULL_BELT,
    )
    safety.draw_lands = SNAP['draw_lands']
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=now, draw=build.draw)
    # No strike through the doorway (no line): nothing in reach, the members within the strike's reach (`near`)
    facts = replace(p.Facts(now, GOAL, False, False, True, lambda: toward(here), SNAP['area']), near=True, quiet=2.0)
    run = p.Pursuit('pickup', START - 60.0, advance=False, leash=p.FULL, area=SNAP['area'])
    found = safety.price(
        facts, run, look, loot, CALM, settings, seen, attack, lambda point: Step(point, TELEPORT),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return p.decide(found, run), safety.decision


def through(here: tuple[float, float]) -> bool:
    return here[1] < DOORWAY


def arrived(here: tuple[float, float]) -> bool:
    return math.dist(here, EXIT) <= HOP


def play(seconds: float, until=through) -> list[tuple[tuple[float, float], p.Act, dict]]:
    """The closed replay from the take's place: each look's move is where the next look stands, up to `seconds` or
    the first look whose move lands where `until` says (past the doorway by default)."""
    safety, here, now, played = module.Safety(), (SNAP['player']['x'], SNAP['player']['y']), START, []
    while now < START + seconds:
        act, decision = look_at(safety, here, now)
        played.append((here, act, decision))
        if isinstance(act, p.Move):
            here = act.step.spot
        if until(here):
            break
        now += LOOK
    return played


def test_the_take_s_look_bars_every_progress_landing_by_the_pack_s_range():
    _, act, decision = play(0.1)[0]
    assert isinstance(act, p.Move)
    assert act.reason.startswith('retreating'), decision['candidates']
    asked = [c for c in decision['candidates'] if c['act'] == 'Move' and not c['retreat'] and c['why'] == '']
    assert asked
    assert all(c['veto'] for c in asked)
    assert any(c['veto'] == module.PACK_RANGE_LANDED for c in decision['candidates'] if not c['retreat'])


def test_with_the_switch_off_the_retreat_and_the_safe_approach_spin_south_of_the_doorway(monkeypatch):
    monkeypatch.setattr(module, 'RANGE_STALL_LIFT', False)
    played = play(12.0)
    assert len(played) >= 25
    assert all(here[1] >= DOORWAY for here, _, _ in played)  # never through
    said = [act.reason for _, act, _ in played if isinstance(act, p.Move)]
    assert all(why.startswith(module.RANGE_STALL_MOVES) for why in said), said
    spread = max(math.dist(played[0][0], here) for here, _, _ in played)
    assert spread < 20.0  # the take: 396 jumps within 10 units


def test_with_the_switch_on_the_stall_lifts_the_bar_and_the_way_out_is_taken(monkeypatch):
    monkeypatch.setattr(module, 'RANGE_STALL_LIFT', True)
    played = play(12.0)
    _, act, decision = played[-1]
    assert isinstance(act, p.Move)
    # Past the doorway, toward the way out
    assert act.step.spot[1] < DOORWAY, [getattr(a, 'reason', '') for _, a, _ in played]
    assert len(played) * LOOK >= module.RANGE_STALL_SECONDS  # not before the stall's seconds
    assert len(played) * LOOK <= module.RANGE_STALL_SECONDS + 3.0
    chosen = next(c for c in decision['candidates'] if c['place'] == list(act.step.spot) or c['place'] == act.step.spot)
    assert chosen['veto'] is None


def test_with_the_switch_on_a_pack_that_never_comes_still_lets_the_way_out_go_by(monkeypatch):
    """The worst case: the pack stays where the take read it whatever is done (in the game it came on once the
    character landed among it, and the fight began: 15:47:15). Each lifted landing among it brings the pack's hop
    back, the stall begins again, and after combat/pack.py PACK_HOPS hops the way goes on through to the way out."""
    monkeypatch.setattr(module, 'RANGE_STALL_LIFT', True)
    played = play(60.0, arrived)
    _, act, _ = played[-1]
    assert isinstance(act, p.Move)
    assert arrived(act.step.spot), [(h, getattr(a, 'reason', '')) for h, a, _ in played if h[1] < DOORWAY]
    assert len(played) * LOOK < 45.0  # the take: 292 s and a stop
    hops = [a for _, a, _ in played if isinstance(a, p.Move) and a.reason.startswith('pack: keeping range')]
    assert len(hops) <= herald_pack.PACK_HOPS


def test_the_lift_ends_when_the_pack_comes_on_or_life_is_lost(monkeypatch):
    monkeypatch.setattr(module, 'RANGE_STALL_LIFT', True)
    safety, here = module.Safety(), (SNAP['player']['x'], SNAP['player']['y'])
    key = (GOAL.do, GOAL.unit, GOAL.route, GOAL.stage, GOAL.place)
    safety.range_stall = (key, START - module.RANGE_STALL_SECONDS - 1.0, float(SNAP['player']['life']))
    _, decision = look_at(safety, here, START)
    assert not any(c['veto'] == module.PACK_RANGE_LANDED for c in decision['candidates'])  # lifted
    assert safety.range_stall is not None
    # The life fell by more than WAIT_LOST since the stall began: the bar is back at the next look
    safety.range_stall = (key, START - module.RANGE_STALL_SECONDS - 1.0, SNAP['player']['life'] + 200.0)
    look_at(safety, here, START + LOOK)
    assert safety.range_stall is None
    _, decision = look_at(safety, here, START + 2 * LOOK)
    assert any(c['veto'] == module.PACK_RANGE_LANDED for c in decision['candidates'])


def test_a_clearing_goal_is_left_to_the_budgets(monkeypatch):
    monkeypatch.setattr(module, 'RANGE_STALL_LIFT', True)
    clearing = replace(GOAL, clearing=True)
    key = (clearing.do, clearing.unit, clearing.route, clearing.stage, clearing.place)
    safety = module.Safety()
    safety.range_stall = (key, START - 60.0, 0.0)
    facts = p.Facts(START, clearing, False, False, True, lambda: toward(EXIT), SNAP['area'])
    assert not safety.range_stalled(clearing, key, facts)
    assert safety.range_stalled(GOAL, key, replace(facts, goal=GOAL))  # the same stall on the route's own goal
