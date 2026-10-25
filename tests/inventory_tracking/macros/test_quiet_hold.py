"""QUIET_HOLD (macros/hunt.py; rca/2026-10-25/pickup-veto-pingpong-findings.md): Harem Level 2, 03:35:24-03:36:28 on
2026-10-25, take 20261025T003442Z-51. A Magic Alpha Helm at (10091, 5635) lay 18 units from an idle tier 5 Herald
(the elite 31, unit 2412395574, at (10074, 5630)); buffs.py QUIET_BY_THE_BOSS defers a side drop while a boss stands
within the strike's reach (22.1) of the character. The looks went by turns: at (10066, 5608), 24.4 from the Herald,
the helm was the run's goal ("safe approach" toward it); at (10070, 5612), 18.4 from him, it was deferred and the goal
was his fight, every landing of which the pack's range barred ("retreating: every progress act is vetoed"), the
retreat back beyond 22.1: 62 Teleports in 64 s, 0 kills. With the switch on, the third deferral a moment after the helm
was the goal leaves the helm alone while the Herald lives."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.game.records import HEALING, VALUABLE, Drop, Loot, Monster
from inventory_tracking.macros import buffs, hunt as module, pickup
from inventory_tracking.macros.pursuit import FULL, Pursuit
from tests.inventory_tracking.macros.test_hunt import game, hunter, me


HELM = Drop(1556594108, 10091.0, 5635.0, 'Magic Alpha Helm', VALUABLE)
HERALD = Monster(2412395574, 31, 1, 10074.0, 5630.0, 0xFFFFFFFF, 0x08, life=128, max_life=128, tier=5)
OUT = (10066.0, 5608.0)  # 03:35:24.20: 24.4 from the Herald, the helm the goal
IN = (10070.0, 5612.0)  # 03:35:25.25: 18.4 from him, the helm deferred
LOOK = 0.45  # seconds a look (the take: 0.4-0.5)


@pytest.fixture(autouse=True)
def switches(monkeypatch):
    monkeypatch.setattr(buffs, 'QUIET_BY_THE_BOSS', True)
    monkeypatch.setattr(module, 'QUIET_HOLD', True)


def scene(*drops: Drop):
    play = game()
    play.loot = Loot(drops or (HELM,), room=('..........',) * 4)
    return play, hunter(play)


def looks(play, hunt, count: int, foes=(HERALD,), start: int = 0) -> list[Drop | None]:
    """`count` looks by turns out of and in the Herald's reach (the take's dance), LOOK s apart."""
    run, found = play.run(), []
    for index in range(start, start + count):
        play.clock.now += LOOK
        found.append(hunt.side_drop(run, OUT if index % 2 == 0 else IN, list(foes), play.world))
    return found


def test_the_take_s_two_places_are_either_side_of_the_strike_s_reach():
    _, hunt = scene()
    assert hunt.reach == pytest.approx(22.1, abs=0.1)
    assert hunt.boss(HERALD)  # a Herald is a boss to the rule
    import math

    assert math.dist(OUT, (HERALD.x, HERALD.y)) > hunt.reach > math.dist(IN, (HERALD.x, HERALD.y))


def test_off_the_helm_is_the_goal_out_of_reach_and_deferred_in_it_at_every_look(monkeypatch):
    monkeypatch.setattr(module, 'QUIET_HOLD', False)
    play, hunt = scene()
    found = looks(play, hunt, 20)
    assert found == [HELM, None] * 10  # the flip, look after look, for as long as the dance lasts


def test_on_the_third_deferral_holds_the_helm_while_the_herald_lives(caplog):
    play, hunt = scene()
    with caplog.at_level(logging.INFO):
        found = looks(play, hunt, 20)
    assert found[:6] == [HELM, None] * 3
    assert found[6:] == [None] * 14  # out of reach too: no goal flip, the fight's goal and its budgets stand
    assert HELM.unit_id in pickup.SHUNNED
    assert sum('(QUIET_HOLD)' in record.getMessage() for record in caplog.records) == 1


def test_the_held_helm_is_taken_up_again_once_the_herald_is_dead():
    play, hunt = scene()
    looks(play, hunt, 6)
    assert looks(play, hunt, 2, start=6) == [None, None]
    dying = replace(HERALD, mode=0)
    assert looks(play, hunt, 1, foes=(dying,), start=8) == [HELM]  # out of reach, the Herald down: the helm
    assert HELM.unit_id not in pickup.SHUNNED
    assert not hunt.quiet_holds


def test_the_hold_ends_with_its_seconds_or_another_level():
    play, hunt = scene()
    looks(play, hunt, 6)
    play.clock.now += module.QUIET_HOLD_SECONDS
    assert looks(play, hunt, 1, start=6) == [HELM]  # the hold ran out (the boss rule counts afresh)
    play, hunt = scene()
    looks(play, hunt, 6)
    play.world = replace(play.world, player=replace(me(play.world), area=102))
    assert looks(play, hunt, 1, start=6) == [HELM]


def test_deferrals_long_after_the_drop_was_the_goal_are_no_flips():
    # A drop deferred while the boss's fight goes on, its looks out of reach QUIET_FLIP_GAP and more apart: no hold
    play, hunt = scene()
    run = play.run()
    for _ in range(6):
        play.clock.now += 0.4
        assert hunt.side_drop(run, OUT, [HERALD], play.world) == HELM
        play.clock.now += module.QUIET_FLIP_GAP + 0.5
        assert hunt.side_drop(run, IN, [HERALD], play.world) is None
    assert not hunt.quiet_holds


def test_a_potion_is_never_held():
    from inventory_tracking.game.layout import SUPER_HEALING

    potion = Drop(77, 10080.0, 5615.0, 'Super Healing Potion', HEALING, txt=SUPER_HEALING)
    play, hunt = scene(potion)
    play.loot = replace(play.loot, belt=(None,) * 16)  # the belt empty: the potion is wanted by the boss too
    found = looks(play, hunt, 12)
    assert found == [potion] * 12
    assert not hunt.quiet_holds


def test_the_run_s_goal_stops_flipping_once_the_helm_is_held(monkeypatch):
    """The goal (hunting/choice.py `goal`) of a level run's look at each place: off, the helm and another by turns
    look after look; on, the helm's goal no more after the third deferral."""

    def labels(hold: bool) -> list[str]:
        monkeypatch.setattr(module, 'QUIET_HOLD', hold)
        play, hunt = scene()
        posted = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=me(play.world).area)
        hunt.post(posted)
        run, said = play.run(), []
        for index in range(12):
            play.clock.now += LOOK
            x, y = OUT if index % 2 == 0 else IN
            play.world = replace(play.world, player=replace(me(play.world), x=x, y=y), monsters=(HERALD,))
            goal = hunt.goal(run, play.world, [HERALD], False, hunt.pursuit)
            said.append(goal.label if goal is not None else '')
        return said

    off, on = labels(False), labels(True)
    helm = 'Magic Alpha Helm, on the way'
    assert off[::2] == [helm] * 6
    assert helm not in off[1::2]
    assert on[:6:2] == [helm] * 3
    assert helm not in on[6:]
