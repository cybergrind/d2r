"""The 03:35:24 flip of rca/2026-10-25/pickup-veto-pingpong-findings.md replayed on the look cut from take
20261025T003442Z-51 (Harem Level 2, fixture harem-helm.json): an idle tier 5 Herald pack of 14 (txt 31, Extra Fast)
15-30 off the character, the Magic Alpha Helm the run took on its way at (10091, 5635), 18 from the Herald.

Closed, as test_canyon_spin.py: the looks are priced as the game prices them, the character stands where the last
look's move landed, the pack where the take read it, LOOK s a look. Each look's goal is the run's: the helm while the
hunt's side drop (macros/hunt.py `side_drop`: buffs.py QUIET_BY_THE_BOSS, QUIET_HOLD) names it, else the Herald's
fight (the agenda's "full clear: the elite 31 (2412395574)"). The budgets of hunting/judging.py are asked at each
look as the judge asks them (DANCE_BUDGET `danced`, STILL_BUDGET `knotted`): the first to give the goal up ends the
replay (the run then passes the pack and goes on). QUIET_HOLD off: the helm and the fight by turns for as long as the
replay lasts, the moves undoing each other, no budget ever counting (the goal changes at every look, and the helm is a
kept goal); on: the third deferral holds the helm, the goal is the fight's from then on, and a budget (the dance's, or
the knot's) gives it up DANCE_SECONDS later."""

import itertools
import json
import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import VALUABLE, Drop, Loot, Monster
from inventory_tracking.macros import buffs, hunt, pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import PICK_REACH, PICK_UP, Goal
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import FIGHT
from tests.inventory_tracking.macros.fakes import player, world
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, FULL_BELT
from tests.inventory_tracking.macros.test_hunt import game, hunter, me


SNAP = json.loads((FIXTURES / 'harem-helm.json').read_text(encoding='utf-8'))
MONSTERS = tuple(
    Monster(
        m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
        life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
    )
    for m in SNAP['monsters']
)  # fmt: skip
FOES = [m for m in MONSTERS if not m.ally and m.owner == NO_OWNER and m.mode not in (0, 12)]
HERALD = next(m for m in FOES if m.unit_id == 2412395574)
HELM = Drop(1556594108, 10091.0, 5635.0, 'Magic Alpha Helm', VALUABLE)
HELM_GOAL = Goal(f'{HELM.label}, on the way', (HELM.x, HELM.y), PICK_UP, PICK_REACH, PRESSED, unit=HELM.unit_id)
FIGHT_GOAL = Goal(
    'full clear: the elite 31 (2412395574)', (HERALD.x, HERALD.y), FIGHT, 22.1, PRESSED, unit=HERALD.unit_id,
    clearing=True,
)  # fmt: skip
HOP = 14.0  # units of the navigator's Teleport toward the goal (the take's: 9-18)
LOOK = 0.45  # seconds a look (the take: 0.4-0.5)
START = 10.0


@pytest.fixture(autouse=True)
def switched(monkeypatch):
    monkeypatch.setattr(module, 'PACK_RANGE_LANDING', True)
    monkeypatch.setattr(buffs, 'QUIET_BY_THE_BOSS', True)


def toward(here: tuple[float, float], place: tuple[float, float]) -> Step:
    gap = math.dist(here, place)
    share = min(HOP / gap, 1.0) if gap else 0.0
    return Step((here[0] + (place[0] - here[0]) * share, here[1] + (place[1] - here[1]) * share), TELEPORT)


def look_at(safety: module.Safety, goal: Goal, here: tuple[float, float], now: float) -> p.Act:
    """The act the safety and the arbiter choose for `goal` with the character at `here` at clock `now`."""
    me_ = player(SNAP['area'], x=here[0], y=here[1])
    alive = world(SNAP['area'], player=me_, monsters=MONSTERS)
    companions = [m for m in MONSTERS if m.ally or m.owner != NO_OWNER]
    build = ECHOING_STRIKE_BUILD
    attack, settings = build.attack, build.settings.safety
    assert attack is not None
    seen = attack.sees(observe(me_, FOES, companions), companions)
    loot = Loot(
        life=SNAP['player']['life'], max_life=SNAP['player']['max_life'],
        stats=tuple((stat, value) for stat, value in SNAP['stats']), belt=FULL_BELT,
    )  # fmt: skip
    safety.draw_lands = SNAP['draw_lands']
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=now, draw=build.draw)
    near = any(math.dist(here, (m.x, m.y)) <= attack.reach for m in FOES)
    facts = p.Facts(now, goal, False, False, True, lambda: toward(here, goal.place), SNAP['area'])
    facts = replace(facts, near=near, quiet=2.0 if near else 0.0)
    run = p.Pursuit('pickup', START - 60.0, advance=False, leash=p.FULL, area=SNAP['area'])
    found = safety.price(
        facts, run, look, loot, CALM, settings, seen, attack, lambda point: Step(point, TELEPORT),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return p.decide(found, run)


def replay(hold: bool, seconds: float = 12.0) -> tuple[list[tuple[tuple[float, float], str, p.Act]], str | None]:
    """The closed replay: (where the look stood, its goal's label, the act) a look, and why a budget gave the goal
    up (None: none did within `seconds`)."""
    kept = hunt.QUIET_HOLD
    setattr(hunt, 'QUIET_HOLD', hold)  # ruff: ignore[set-attr-with-constant] - both arms in one test
    try:
        play = game()
        play.loot = Loot((HELM,), room=('..........',) * 4)
        chooser, run = hunter(play), play.run()
        safety, here, now, played = module.Safety(), (SNAP['player']['x'], SNAP['player']['y']), START, []
        while now < START + seconds:
            play.clock.now = now
            play.world = replace(play.world, player=replace(me(play.world), x=here[0], y=here[1]), monsters=MONSTERS)
            side = chooser.side_drop(run, here, FOES, play.world)
            goal = HELM_GOAL if side is not None and side.unit_id == HELM.unit_id else FIGHT_GOAL
            act = look_at(safety, goal, here, now)
            played.append((here, goal.label, act))
            danced = judging.danced(chooser, play.world, goal, act, now)
            knot = judging.knotted(chooser, play.world, goal, act, now, False)
            if danced or knot:
                return played, danced or knot
            if isinstance(act, p.Move):
                here = act.step.spot
            now += LOOK
        return played, None
    finally:
        setattr(hunt, 'QUIET_HOLD', kept)  # ruff: ignore[set-attr-with-constant]


def flips(played) -> int:
    return sum(1 for (_, a, _), (_, b, _) in itertools.pairwise(played) if a != b)


def test_the_cut_look_is_the_take_s_out_of_the_herald_s_reach_with_the_helm_the_goal():
    here = (SNAP['player']['x'], SNAP['player']['y'])
    assert 22.1 < math.dist(here, (HERALD.x, HERALD.y)) < 26.0
    assert sum(1 for m in FOES if m.tier == 5) == 14
    played, _ = replay(False, seconds=0.1)
    assert played[0][1] == HELM_GOAL.label


def test_off_the_goal_flips_between_the_helm_and_the_fight_and_no_budget_ever_counts():
    played, given_up = replay(False, seconds=30.0)
    assert given_up is None  # the take: 64 s
    assert flips(played) >= 30, [(label, getattr(act, 'reason', '')) for _, label, act in played]
    spread = max(math.dist(played[0][0], here) for here, _, _ in played)
    assert spread < 30.0  # the take: 62 Teleports within ~20 units


def test_on_the_goal_is_the_fight_s_after_the_third_deferral_and_a_budget_gives_it_up():
    played, given_up = replay(True, seconds=30.0)
    labels = [label for _, label, _ in played]
    third = [i for i, (a, b) in enumerate(itertools.pairwise(labels)) if a == HELM_GOAL.label and b != a][2] + 1
    assert third * LOOK < 6.0
    assert HELM_GOAL.label not in labels[third:]
    assert given_up is not None
    assert given_up.endswith(('(DANCE_BUDGET)', '(STILL_BUDGET)')), given_up
    assert len(played) * LOOK <= third * LOOK + judging.DANCE_SECONDS + 2 * LOOK
    # The safety's own: no move of the fight's lands nearer the Herald than the flip's did
    nearest = min(math.dist(here, (HERALD.x, HERALD.y)) for here, _, _ in played)
    off, _ = replay(False, seconds=len(played) * LOOK)
    assert nearest >= min(math.dist(here, (HERALD.x, HERALD.y)) for here, _, _ in off) - 1.0
