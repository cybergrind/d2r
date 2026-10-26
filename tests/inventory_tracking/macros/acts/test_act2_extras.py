"""The Act 2 TZ leveling kind's extra acts (macros/acts/act2.py TZ_LEVELING_EXTRAS; macros/actloop.py `extra_acts`). The
player, 2026-10-26 ~09:00: "if we get act 4 extra shard (like now, over 99) - we terrorize it and run baal - if we get
act 5 extra shard - we terrorize it and do full clear of worldstone keep 2, 3, trone room and baal"; asked whether act 4
meant Baal: "act 4 terrorized: run full CS + Diablo". An extra shard is one over the limit (its stack at 99, or more
carried than its stack has room for); the Deep's and the Northern's only. After act 2's steps: act 4's Chaos Sanctuary
toured whole with the seals and Diablo (the River of Flame only crossed), act 5's Worldstone Keep 2 and 3 toured whole,
the Throne and Baal; then Save and Exit. The other shards, and the other kinds, as before."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.game.stash import STACK_MOST
from inventory_tracking.macros import actloop, terrorize, tzroutine, zonenav
from inventory_tracking.macros.acts import act2
from inventory_tracking.macros.agenda import ON_THE_WAY, PLUS, PLUS_WAY, Agenda
from inventory_tracking.macros.loop import ACT2_TZ, ACT_KINDS, LEAVE, TZ, TZ_SHARD
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.acts.harness import SHARD_OF, ActGame, force_ready, trips_of
from tests.inventory_tracking.macros.acts.test_act2 import tomb_entrances
from tests.inventory_tracking.macros.test_tzloop import CANYON, TOMBS


LAIR, SANCTUARY = 73, 74
RIVER, CHAOS = 107, 108
KEEP_2, KEEP_3, THRONE, CHAMBER = 129, 130, 131, 132
WESTERN, EASTERN, SOUTHERN, DEEP, NORTHERN = (SHARD_OF[act] for act in range(1, 6))
SEALS = ['Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls']
ACT_2_LINE = (
    "Macro: tz: zone Act2-Manual: Tal Rasha's Tombs from 46: [46, 66, 67, 68, 69, 70, 71, 72, 73], [66, 67, 68, 69, "
    '70, 71, 72] a tour from 46 one by one; Summoner from 74: [74]; skipped none'
)
ALONE_LINE = (
    "Macro: act: act 2 alone (Act 2 TZ leveling): its script's alone steps only, then the game's end: no rest of the "
    'act, no rotation, no other act'
)


@pytest.fixture(autouse=True)
def caches_cleared():
    tzroutine.itinerary.cache_clear()
    zonenav.graph_of.cache_clear()
    yield
    tzroutine.itinerary.cache_clear()
    zonenav.graph_of.cache_clear()


def alone_plan(monkeypatch, order: tuple[int, ...]):
    """Act 2 TZ leveling's itinerary with the acts of `order` terrorized (act 2 first)."""
    force_ready(monkeypatch, 2)
    zones = [manual_zone(act) for act in order]
    found = tzroutine.itinerary(
        frozenset(area for zone in zones if zone is not None for area in zone.core), order, True
    )
    assert found is not None
    return found


# -- the plans


def test_no_extra_act_leaves_the_plan_and_its_lines_as_they_were(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        found = alone_plan(monkeypatch, (2,))
    assert [record.getMessage() for record in caplog.records] == [ALONE_LINE, ACT_2_LINE]
    assert [trip.route for trip in found.excursions] == ["Tal Rasha's Tombs", 'Summoner']


def test_act_4_extra_is_the_chaos_sanctuary_whole_and_diablo_only(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        found = alone_plan(monkeypatch, (2, 4))
    assert trips_of(found)[2:] == [('Diablo', RIVER, (RIVER, CHAOS))]  # no River rest, City, Steppes or Plains
    assert found.zone == 'Act2-Manual + Act4-Manual'
    diablo = found.excursions[2]
    assert diablo.passes == frozenset((RIVER,))
    assert diablo.whole == frozenset((CHAOS,))
    assert tzroutine.policy_of(RIVER, diablo) == ON_THE_WAY  # crossed: the leaders near only
    assert tzroutine.policy_of(CHAOS, diablo) == PLUS  # "full CS": every room toured, the seals, Diablo
    said = [record.getMessage() for record in caplog.records]
    assert said[0] == (
        "Macro: act: act 2 alone (Act 2 TZ leveling): its script's alone steps only, then act 4 by a shard over the "
        "limit: act 4 (Diablo to 108 from 107); then the game's end: no rest of the acts, no rotation, no other act"
    )
    assert said[1] == (
        ACT_2_LINE.replace('Act2-Manual:', 'Act2-Manual + Act4-Manual:').removesuffix('; skipped none')
        + '; Diablo from 107: [107, 108], [107] only crossed to the boss; skipped none'
    )


def test_act_5_extra_is_the_keep_2_and_3_whole_the_throne_and_baal_only(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        found = alone_plan(monkeypatch, (2, 5))
    assert trips_of(found)[2:] == [('Baal', KEEP_2, (KEEP_2, KEEP_3, THRONE, CHAMBER))]  # no halls, Keep 1, rest
    baal = found.excursions[2]
    assert baal.passes == frozenset()  # worked, not crossed
    assert baal.whole == frozenset((KEEP_2, KEEP_3))
    policies = [tzroutine.policy_of(area, baal) for area in baal.areas]
    assert policies == [PLUS, PLUS, PLUS_WAY, PLUS]  # the Keeps toured whole; the Throne's stand and waves; Baal
    assert 'Baal from 129: [129, 130, 131, 132]; skipped none' in caplog.text
    assert 'then act 5 by a shard over the limit: act 5 (Baal to 132 from 129)' in caplog.text


def test_both_extras_play_act_4_then_act_5_and_nothing_else(monkeypatch):
    found = alone_plan(monkeypatch, (2, 4, 5))
    assert [trip.route for trip in found.excursions] == ["Tal Rasha's Tombs", 'Summoner', 'Diablo', 'Baal']
    assert {area for trip in found.excursions for area in trip.areas} == {
        CANYON, *TOMBS, LAIR, SANCTUARY, RIVER, CHAOS, KEEP_2, KEEP_3, THRONE, CHAMBER
    }  # fmt: skip


def test_another_acts_shard_in_the_order_is_not_played(monkeypatch):
    # Act 1 or 3 never in an Act 2 TZ leveling game's order (its overflow refuses them); were one there, no trip of it
    found = alone_plan(monkeypatch, (2, 1, 3, 4))
    assert [trip.route for trip in found.excursions] == ["Tal Rasha's Tombs", 'Summoner', 'Diablo']


def test_the_act_scripts_of_the_other_kinds_are_untouched(monkeypatch):
    # "Shard: Act 4" and "Shard: Act 5" (and any game not alone) play their own scripts, as before
    from tests.inventory_tracking.macros.acts.test_act4 import LIVE

    force_ready(monkeypatch, 4)
    zone = manual_zone(4)
    assert zone is not None
    found = tzroutine.itinerary(zone.core, (4,), False)
    assert found is not None
    assert tzroutine.trips_said(found.excursions) == LIVE.split(': ', 3)[-1].split('; Andariel')[0]
    assert act2.SCRIPT.extra(4) is not None
    assert act2.SCRIPT.extra(1) is None


# -- the overflow: which shards an Act 2 TZ leveling game uses


def over(*shards: int) -> StashView:
    return StashView((), tuple((shard, STACK_MOST) for shard in shards))


def test_only_the_deep_and_the_northern_over_the_limit_are_its_extras():
    agenda = Agenda()
    view = over(WESTERN, EASTERN, SOUTHERN, DEEP, NORTHERN)
    assert actloop.extra_acts(ACT2_TZ) == frozenset((4, 5))
    assert actloop.extra_acts(ACT_KINDS['act2']) == frozenset()
    assert [act for act, _ in actloop.overflow_due(view, agenda, 2, alone=True)] == [4, 5]  # act 4 first
    assert actloop.overflow_due(over(WESTERN, SOUTHERN), agenda, 2, alone=True) == ()  # "no other shards"
    # The other kinds' overflow as before: every act over the limit but the own, the acts after it first
    assert [act for act, _ in actloop.overflow_due(view, agenda, 2)] == [3, 4, 5, 1]
    assert [act for act, _ in actloop.overflow_due(view, agenda, 4)] == [5, 1, 2, 3]
    deep = Carried(7, DEEP, 0, 0, (1, 1))
    assert actloop.overflow_due(StashView((), ((DEEP, 98),)), agenda, 2, (deep,), alone=True) == ()  # room for it
    two = (deep, replace(deep, unit_id=8))
    assert actloop.overflow_due(StashView((), ((DEEP, 98),)), agenda, 2, two, alone=True) == ((4, deep),)


def loop_of(kind, shard: str | None):
    from types import SimpleNamespace

    agenda = Agenda()
    agenda.begin('g1')
    agenda.shard = shard
    return SimpleNamespace(kind=kind, agenda=agenda, done=None)


def test_a_carried_deep_or_northern_is_kept_once_act_2_is_terrorized(monkeypatch):
    monkeypatch.setattr(terrorize, 'CLICKS', True)
    lone = loop_of(ACT2_TZ, actloop.USED)
    assert actloop.unusable(lone, 4) is None
    assert actloop.unusable(lone, 5) is None
    assert actloop.unusable(lone, 1) == 'Act 2 TZ leveling plays act 2 alone: no other act in its game'
    assert actloop.unusable(lone, 3) == 'Act 2 TZ leveling plays act 2 alone: no other act in its game'
    failed = loop_of(ACT2_TZ, actloop.FAILED)
    assert actloop.unusable(failed, 4) == 'no shard is risked in this game (failed): it ends unplayed'
    assert actloop.picked_shards(lone) == frozenset((DEEP, NORTHERN))
    assert actloop.picked_shards(failed) == frozenset()


# -- the games walked


def act2tz_game(monkeypatch) -> ActGame:
    act = ActGame(2, monkeypatch)
    act.game.loop.kind = ACT2_TZ
    tomb_entrances(act)
    return act


def terrorized_by_hand(act: ActGame, number: int) -> None:
    """Act `number`'s levels read terrorized from its shard's use, as live (the harness's own shard does so)."""
    zone = manual_zone(number)
    assert zone is not None
    act.game.zone = act.game.zone | frozenset(zone.areas)
    act.game.progress.wanted = lambda level: level in act.game.zone


def assert_act_2_then(walk, *levels: int) -> None:
    from tests.inventory_tracking.macros.acts.harness import TRUE_TOMB
    from tests.inventory_tracking.macros.test_tzloop import NEAREST

    third = NEAREST.index(TRUE_TOMB) + 1
    assert walk.levels == [CANYON, *NEAREST[:third], LAIR, *NEAREST[third:], SANCTUARY, *levels]  # each first run


@pytest.mark.parametrize('graph', [False, True], ids=['itinerary', 'zone navigation'])
def test_a_deep_stack_at_99_and_one_carried_play_the_chaos_sanctuary_and_diablo_after_act_2(monkeypatch, caplog, graph):
    caplog.set_level(logging.INFO)
    if not graph:
        monkeypatch.setattr(zonenav, 'ACTS', frozenset())
    act = act2tz_game(monkeypatch)
    play = act.game.play
    play.stacks[DEEP] = STACK_MOST
    play.pack = Pack(items=(Carried(901, DEEP, 0, 3, (1, 1)),))
    uses: list[tuple[int, int]] = []

    def carried(run, item, key, terrorized):
        pack = play.pack
        assert pack is not None
        play.pack = replace(pack, items=tuple(each for each in pack.items if each.unit_id != item.unit_id))
        uses.append((terrorize.SHARDS[item.txt], item.unit_id))
        terrorized_by_hand(act, terrorize.SHARDS[item.txt])
        return terrorize.Used(item.txt, 4, STACK_MOST, STACK_MOST, gone=True, listed=False, carried=True)

    monkeypatch.setattr(actloop, 'use_carried', carried)
    walk = act.play(legs=400)

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [2]  # the Eastern from its stack
    assert uses == [(4, 901)]  # the carried Deep first, where it lies
    assert act.game.loop.agenda.acts == (2, 4)
    assert_act_2_then(walk, RIVER, CHAOS)  # the River crossed, the Sanctuary: nothing else of act 4
    assert walk.runs.count(RIVER) == 1  # no River rest after Diablo
    assert walk.kills == ['Duriel', 'The Summoner', *SEALS, 'Diablo']
    assert ('waypoint', RIVER) in walk.moves
    assert walk.legs[-1] == LEAVE
    assert 'Macro: act: Deep shard over the limit (99), a carried one: act 4 terrorized too, played after act 2' in (
        caplog.text
    )


@pytest.mark.parametrize('graph', [False, True], ids=['itinerary', 'zone navigation'])
def test_a_northern_over_the_limit_plays_the_keep_the_throne_and_baal_after_act_2(monkeypatch, caplog, graph):
    caplog.set_level(logging.INFO)
    if not graph:
        monkeypatch.setattr(zonenav, 'ACTS', frozenset())
    act = act2tz_game(monkeypatch)
    play = act.game.play
    play.stacks[NORTHERN] = STACK_MOST
    own = actloop.terrorize
    stacked: list[int] = []

    def used(run, key, number, terrorized, floor=0):
        if number == 2:
            return own(run, key, number, terrorized, floor)
        stacked.append(number)
        play.stacks[NORTHERN] -= 1
        terrorized_by_hand(act, number)
        return terrorize.Used(NORTHERN, number, STACK_MOST, STACK_MOST - 1, gone=True, listed=False)

    monkeypatch.setattr(actloop, 'terrorize', used)
    walk = act.play(legs=400)

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.shard == [2]
    assert stacked == [5]  # one from its stack at the shard step
    assert act.game.loop.agenda.acts == (2, 5)
    assert_act_2_then(walk, KEEP_2, KEEP_3, THRONE, CHAMBER)  # the Keep 2 and 3, the Throne, Baal: no other level
    assert walk.kills == ['Duriel', 'The Summoner', 'Lister the Tormentor', 'Baal']
    assert walk.legs[-1] == LEAVE


@pytest.mark.parametrize('shard', [WESTERN, SOUTHERN])
def test_a_western_or_southern_over_the_limit_is_still_not_used(monkeypatch, shard):
    act = act2tz_game(monkeypatch)
    play = act.game.play
    play.stacks[shard] = STACK_MOST
    play.pack = Pack(items=(Carried(902, shard, 0, 3, (1, 1)),))
    calls: list[int] = []
    own = actloop.terrorize

    def used(run, key, number, terrorized, floor=0):
        calls.append(number)
        return own(run, key, number, terrorized, floor)

    monkeypatch.setattr(actloop, 'terrorize', used)
    monkeypatch.setattr(actloop, 'use_carried', lambda *args: calls.append(-1))
    walk = act.play(legs=400)
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert calls == [2]  # the kind's own Eastern only
    assert act.game.loop.agenda.acts == (2,)
    assert_act_2_then(walk)


def test_the_tz_kinds_overflow_is_as_before():
    # TZ leveling (no act of its own): a carried shard over the limit of any act, as before
    agenda = Agenda()
    western = Carried(1, WESTERN, 0, 0, (1, 1))
    assert [act for act, _ in actloop.overflow_due(over(WESTERN), agenda, None, (western,), carried_only=True)] == [1]
    assert actloop.extra_acts(TZ) == frozenset()
