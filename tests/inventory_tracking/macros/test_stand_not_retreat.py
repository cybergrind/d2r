"""The approach/retreat dance of rca/2026-10-25/approach-retreat-findings.md replayed on two looks cut from real takes:

- Maggot Lair Level 3, take 20261025T005528Z-64, 03:55:32.98 (fixture maggot-approach.json): an idle tier 5 Herald
  pack of txt 93 (15, the elite 1466204337) 20-45 off; the run's goal its fight ("full clear: the elite 93"). From the
  retreat spot a safe approach is admitted, from where it lands every progress act is barred by the pack's range
  (macros/safety.py PACK_RANGE_LANDED), and every retreat and standing still are priced harm 0;
- Radament, take 20261025T003729Z-49, 03:38:22.01 (fixture radament-approach.json): every progress act over the life
  budget, every retreat and standing still priced harm 0 behind the sewer's walls; the game retreated 12 units. The
  closed replay has no walls, and there a retreat saves harm: it is the check that such a retreat is still made.

Closed, as test_canyon_spin.py: the looks are priced as the game prices them, the character stands where the last
look's move landed, the pack where the take read it, LOOK s a look; the budgets of hunting/judging.py are asked each
look as the judge asks them (DANCE_BUDGET `danced`, STILL_BUDGET `knotted`), the first to give the goal up ends the
replay. pursuit.py STAND_NOT_RETREAT off: the retreat and the safe approach undo each other, never nearer the pack
than the approach's landing, until DANCE_BUDGET gives the fight up (in the game the next goal, the agenda's chest by
the same pack, danced on: 125 s); on: the character stands where the approach landed, WAIT_LIFT lifts the pack's
range bar WAIT_HORIZON later and the move goes in to the pack."""

import json
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat.harm import Harm
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Loot, Monster
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import NoWay, Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import FIGHT
from tests.inventory_tracking.macros.fakes import player, world
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, FULL_BELT
from tests.inventory_tracking.macros.test_hunt import game, hunter, me


def snap(name: str) -> tuple[dict, tuple[Monster, ...], list[Monster]]:
    found = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    monsters = tuple(
        Monster(
            m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
            life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
        )
        for m in found['monsters']
    )  # fmt: skip
    foes = [m for m in monsters if not m.ally and m.owner == NO_OWNER and m.mode not in (0, 12)]
    return found, monsters, foes


MAGGOT, MAGGOT_MONSTERS, MAGGOT_FOES = snap('maggot-approach')
ELITE = next(m for m in MAGGOT_FOES if m.unit_id == 1466204337)
MAGGOT_GOAL = Goal(
    'full clear: the elite 93 (1466204337)', (ELITE.x, ELITE.y), FIGHT, 22.1, PRESSED, unit=ELITE.unit_id,
    clearing=True,
)  # fmt: skip
RADAMENT, RADAMENT_MONSTERS, RADAMENT_FOES = snap('radament-approach')
RADAMENT_UNIT = next(m for m in RADAMENT_FOES if m.unit_id == 1136111001)
# The route's boss stage in the game; here a fight on the way (no route is played), priced the same
RADAMENT_GOAL = Goal(
    'Radament', (RADAMENT_UNIT.x, RADAMENT_UNIT.y), FIGHT, 22.1, PRESSED, unit=RADAMENT_UNIT.unit_id, clearing=True
)
HOP = 14.0  # units of the navigator's Teleport toward the goal
LOOK = 0.4  # seconds a look (the take: 0.35-0.6)
START = 10.0
IN_THE_PACK = 10.0  # units from a member: in reach and in the pack's way (the take's walls do not hide it there)


@pytest.fixture(autouse=True)
def switched(monkeypatch):
    monkeypatch.setattr(module, 'PACK_RANGE_LANDING', True)
    monkeypatch.setattr(module, 'WAIT_LIFT', True)


def toward(here: tuple[float, float], place: tuple[float, float]) -> Step:
    gap = math.dist(here, place)
    share = min(HOP / gap, 1.0) if gap else 0.0
    return Step((here[0] + (place[0] - here[0]) * share, here[1] + (place[1] - here[1]) * share), TELEPORT)


def look_at(safety: module.Safety, cut: dict, monsters, foes, goal: Goal, here, now: float) -> p.Act:
    """The act the safety and the arbiter choose for `goal` with the character at `here` at clock `now`."""
    me_ = player(cut['area'], x=here[0], y=here[1])
    alive = world(cut['area'], player=me_, monsters=monsters)
    companions = [m for m in monsters if m.ally or m.owner != NO_OWNER]
    build = ECHOING_STRIKE_BUILD
    attack, settings = build.attack, build.settings.safety
    assert attack is not None
    seen = attack.sees(observe(me_, foes, companions), companions)
    loot = Loot(
        life=cut['player']['life'], max_life=cut['player']['max_life'],
        stats=tuple((stat, value) for stat, value in cut['stats']), belt=FULL_BELT,
    )  # fmt: skip
    safety.draw_lands = cut['draw_lands']
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=now, draw=build.draw)
    near = any(math.dist(here, (m.x, m.y)) <= attack.reach for m in foes)
    facts = p.Facts(now, goal, False, False, True, lambda: toward(here, goal.place), cut['area'])
    facts = replace(facts, near=near, quiet=2.0 if near else 0.0)
    run = p.Pursuit('pickup', START - 60.0, advance=False, leash=p.FULL, area=cut['area'])
    found = safety.price(
        facts, run, look, loot, CALM, settings, seen, attack, lambda point: Step(point, TELEPORT),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return p.decide(found, run)


def nearest(here) -> float:
    return min(math.dist(here, (m.x, m.y)) for m in MAGGOT_FOES)


def replay(stand: bool, seconds: float = 15.0, until_in: bool = False):
    """The closed replay of the Maggot Lair look: (where the look stood, the act) a look, and why a budget gave the
    goal up (None: none did within `seconds`). `until_in`: ends at the first move landing IN_THE_PACK of a member."""
    keep = p.STAND_NOT_RETREAT
    setattr(p, 'STAND_NOT_RETREAT', stand)  # ruff: ignore[set-attr-with-constant] - both arms in one test
    try:
        play = game()
        chooser, _ = hunter(play), play.run()
        safety, here, now, played = module.Safety(), (MAGGOT['player']['x'], MAGGOT['player']['y']), START, []
        while now < START + seconds:
            play.clock.now = now
            play.world = replace(
                play.world, player=replace(me(play.world), x=here[0], y=here[1]), monsters=MAGGOT_MONSTERS
            )
            act = look_at(safety, MAGGOT, MAGGOT_MONSTERS, MAGGOT_FOES, MAGGOT_GOAL, here, now)
            played.append((here, act))
            given_up = judging.danced(chooser, play.world, MAGGOT_GOAL, act, now) or judging.knotted(
                chooser, play.world, MAGGOT_GOAL, act, now, False
            )
            if given_up:
                return played, given_up
            if isinstance(act, p.Move):
                here = act.step.spot
                if until_in and nearest(here) <= IN_THE_PACK:
                    break
            now += LOOK
        return played, None
    finally:
        setattr(p, 'STAND_NOT_RETREAT', keep)  # ruff: ignore[set-attr-with-constant]


def said(act: p.Act) -> str:
    return getattr(act, 'reason', '')


def landings(played) -> list[tuple[float, float]]:
    return [act.step.spot for _, act in played if isinstance(act, p.Move)]


def test_the_cut_look_admits_a_safe_approach_toward_the_idle_pack():
    played, _ = replay(False, seconds=0.1)
    here, act = played[0]
    assert isinstance(act, p.Move)
    assert said(act) == 'safe approach'
    assert sum(1 for m in MAGGOT_FOES if m.tier == 5) == 15
    assert 20.0 < nearest(here) < 22.1


def test_off_the_retreat_and_the_safe_approach_undo_each_other_until_the_dance_budget_gives_the_fight_up():
    played, given_up = replay(False)
    reasons = [said(act) for _, act in played]
    assert given_up is not None, reasons
    assert given_up.endswith('(DANCE_BUDGET)'), given_up
    assert sum(1 for r in reasons if r.startswith('retreating')) >= 4, reasons
    assert sum(1 for r in reasons if r == 'safe approach') >= 4, reasons
    assert not any(isinstance(act, NoWay) for _, act in played)  # never stood
    assert min(nearest(spot) for spot in landings(played)) > 13.0  # never in to the pack


def test_on_the_character_stands_where_the_approach_landed_and_goes_in_once_wait_lift_lifts_the_bar():
    played, given_up = replay(True, until_in=True)
    reasons = [said(act) for _, act in played]
    assert given_up is None, (given_up, reasons)
    assert reasons[0] == 'safe approach'
    stood = [i for i, (_, act) in enumerate(played) if isinstance(act, NoWay) and act.reason == module.WAITING]
    assert stood, reasons
    assert stood[0] == 1, reasons  # at the approach's landing, at once
    assert not any(r.startswith('retreating') for r in reasons[: stood[-1] + 1]), reasons
    assert len({played[i][0] for i in stood}) == 1  # in one place
    # In to the pack WAIT_HORIZON after the stand began (the off arm never came nearer than 13)
    _, last = played[-1]
    assert isinstance(last, p.Move)
    assert nearest(last.step.spot) <= IN_THE_PACK
    assert (len(played) - 1 - stood[0]) * LOOK <= module.WAIT_HORIZON + 2 * LOOK
    assert len(played) * LOOK < judging.DANCE_SECONDS + LOOK


def test_on_the_stand_lasts_stand_seconds_at_most_when_nothing_lifts_the_bar(monkeypatch):
    monkeypatch.setattr(module, 'WAIT_LIFT', False)
    played, _ = replay(True, seconds=p.STAND_SECONDS + 3.0)
    stood = [i for i, (_, act) in enumerate(played) if isinstance(act, NoWay)]
    assert stood
    assert (stood[-1] - stood[0]) * LOOK < p.STAND_SECONDS
    after = [said(act) for _, act in played[stood[-1] + 1 :]]
    assert after
    assert after[0].startswith('retreating'), after  # as before once the stand is spent


def test_radament_s_look_without_its_walls_keeps_the_retreat_that_saves_harm(monkeypatch):
    """The closed replay has no walls: Radament's way to the stand is open, the stand priced 298 (worst 1347) against
    152 (worst 1217) for the best retreat, so the retreat is made with the switch on too (in the game, behind the
    sewer's walls, both were 0 and it would stand)."""
    here = (RADAMENT['player']['x'], RADAMENT['player']['y'])
    for stand in (False, True):
        monkeypatch.setattr(p, 'STAND_NOT_RETREAT', stand)
        act = look_at(module.Safety(), RADAMENT, RADAMENT_MONSTERS, RADAMENT_FOES, RADAMENT_GOAL, here, START)
        assert isinstance(act, p.Move), (stand, act)
        assert said(act).startswith(f'retreating: {p.OVER_BUDGET}')


def test_a_retreat_that_saves_harm_is_still_made(monkeypatch):
    """Standing is chosen only when no retreat is less harmful: the stand priced over the least retreat keeps it."""
    monkeypatch.setattr(p, 'STAND_NOT_RETREAT', True)
    retreat = p.Candidate(p.Move(Step((1.0, 1.0), TELEPORT), MAGGOT_GOAL, 'retreat'), 1.0, harm(0.0, 0.0), True)
    still = p.Candidate(NoWay(module.WAITING), math.inf, harm(5.0, 40.0), True)
    facts = p.Facts(START, None, False, False, True, lambda: Step((0.0, 0.0)), 1, stand=True)
    assert p.standing(facts, [retreat, still], retreat) is None
    level = p.Candidate(NoWay(module.WAITING), math.inf, harm(0.0, 0.0), True)
    assert p.standing(facts, [retreat, level], retreat) is level
    assert p.standing(replace(facts, stand=False), [retreat, level], retreat) is None


def harm(mean: float, worst: float) -> Harm:
    return Harm(mean=mean, worst=worst, losses=(worst,))
