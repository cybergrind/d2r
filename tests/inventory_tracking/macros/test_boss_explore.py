"""A level run kept exploring for a boss of the game's ledger with no place known (macros/pursuit.py BOSS_EXPLORE,
hunting/judging.py `unfound_bosses`, `boss_explore`; the coordinator's relay of rca/2026-10-22/boss-ledger-findings.md
cause 4, 2026-10-22; the player: "we need to kill all bosses, no exceptions to that")."""

import math
from types import SimpleNamespace

from inventory_tracking.macros import pursuit, zonenav
from inventory_tracking.macros.bossledger import Boss
from inventory_tracking.macros.goals import REACH, Goal
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.pursuit import NOTHING_LEFT, Ended, Facts, Pursuit, ends_run, run_level
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.routes.model import LOOT


DURANCE_3 = 102
LOOT_GOAL = Goal('loot', (100.0, 100.0), LOOT, 5.0, STANDING, route='Mephisto')
ROOM = ((300.0, 340.0), 'an unexplored room', None)
ISMAIL = Boss('Ismail Vilehand', DURANCE_3)
MAFFER = Boss('Maffer Dragonhand', DURANCE_3, place=(400.0, 400.0))  # placed: the agenda's boss goal takes him


def facts(goal: Goal | None, bosses: int = 0) -> Facts:
    return Facts(10.0, goal, False, False, True, lambda: math.inf, DURANCE_3, bosses_left=bosses)  # type: ignore[arg-type]


def hunter(*alive: Boss, room=ROOM, plan: object = 'plan', worked: int = 0) -> SimpleNamespace:
    bosses = SimpleNamespace(alive_in=lambda area: [b for b in alive if b.area == area])
    agenda = SimpleNamespace(plan=plan, worked={DURANCE_3: worked}, bosses=bosses)
    return SimpleNamespace(agenda=agenda, reach=20.0, next_room=lambda run, player, area, now: room)


def test_the_loot_left_or_no_stage_ends_the_run_with_no_press_only() -> None:
    assert ends_run(LOOT_GOAL, pressed=False)
    assert ends_run(None, pressed=False)
    assert not ends_run(LOOT_GOAL, pressed=True)
    assert not ends_run(Goal('the Council', (1.0, 1.0), REACH, 5.0, STANDING, route='Mephisto'), pressed=False)


def test_an_end_with_a_boss_unfound_names_it_and_keeps_the_reason_s_start() -> None:
    run = Pursuit('pickup', 0.0, advance=False, leash=pursuit.FULL, area=DURANCE_3)
    ended = run_level(facts(LOOT_GOAL, bosses=1), False, run)
    assert isinstance(ended, Ended)
    assert ended.reason.startswith('what is left of the route is loot, which takes a press')
    assert 'no room left to explore' in ended.reason
    bare = run_level(facts(None, bosses=2), False, run)
    assert isinstance(bare, Ended)
    assert bare.reason.startswith(NOTHING_LEFT)
    assert '2 bosses of the ledger' in bare.reason
    plain = run_level(facts(LOOT_GOAL), False, run)
    assert isinstance(plain, Ended)
    assert plain.reason == 'what is left of the route is loot, which takes a press'


def test_only_a_live_boss_with_no_place_and_no_unit_is_counted() -> None:
    taken = Boss('Geleb Flamefinger', DURANCE_3, unit=77)
    assert judging.unfound_bosses(hunter(ISMAIL, MAFFER, taken), DURANCE_3) == [ISMAIL]  # type: ignore[arg-type]
    assert judging.unfound_bosses(hunter(MAFFER), DURANCE_3) == []  # type: ignore[arg-type]
    no_zone = SimpleNamespace(agenda=None)
    assert judging.unfound_bosses(no_zone, DURANCE_3) == []  # type: ignore[arg-type]


def test_the_ledger_s_hold_bounds_it(monkeypatch) -> None:
    monkeypatch.setattr(judging, 'Itinerary', str)  # the plan below counts as a zone's itinerary
    monkeypatch.setattr(zonenav, 'on', lambda plan: True)
    node = SimpleNamespace(children=())
    monkeypatch.setattr(zonenav, 'graph_of', lambda plan: SimpleNamespace(nodes={DURANCE_3: node}))
    spent = zonenav.runs_allowed(node) + zonenav.BOSS_RUNS  # type: ignore[arg-type]
    assert judging.unfound_bosses(hunter(ISMAIL, worked=spent - 1), DURANCE_3) == [ISMAIL]  # type: ignore[arg-type]
    assert judging.unfound_bosses(hunter(ISMAIL, worked=spent), DURANCE_3) == []  # type: ignore[arg-type]
    monkeypatch.setattr(zonenav, 'BOSSES_HOLD', False)
    assert judging.unfound_bosses(hunter(ISMAIL), DURANCE_3) == []  # type: ignore[arg-type]
    monkeypatch.setattr(zonenav, 'BOSSES_HOLD', True)
    monkeypatch.setattr(pursuit, 'BOSS_EXPLORE', False)
    assert judging.unfound_bosses(hunter(ISMAIL), DURANCE_3) == []  # type: ignore[arg-type]


def test_the_next_unexplored_room_is_the_run_s_goal_and_none_left_keeps_the_end() -> None:
    world = SimpleNamespace(game_name='game-1')
    player = SimpleNamespace(area=DURANCE_3)
    goal = judging.boss_explore(hunter(ISMAIL), None, world, player, LOOT_GOAL, [ISMAIL], 10.0)  # type: ignore[arg-type]
    assert goal is not None
    assert goal.place == ROOM[0]
    assert goal.clearing
    assert goal.do == REACH
    assert goal.label.startswith('Ismail Vilehand (')
    assert pursuit.BOSS_EXPLORE_SAID in goal.label
    assert not ends_run(goal, pressed=False)  # the run goes on toward the room
    left = judging.boss_explore(hunter(ISMAIL, room=None), None, world, player, LOOT_GOAL, [ISMAIL], 10.0)  # type: ignore[arg-type]
    assert left is LOOT_GOAL
