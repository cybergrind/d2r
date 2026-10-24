"""The game's bosses by zone navigation (macros/bossledger.py; rca/2026-10-22/boss-audit-findings.md). The player,
2026-10-22: "we need to kill all bosses, no exceptions to that -> they can give a very valuable drops, especially baal's
statue"; "we should always kill act bosses, no need to kill hepasto if it is just travel through"."""

import logging
from types import SimpleNamespace
from typing import Any, cast

import pytest

from inventory_tracking.macros import tzloop, zonenav
from inventory_tracking.macros.agenda import ON_THE_WAY, ZONE_LEFT, Agenda
from inventory_tracking.macros.hunting import choice
from inventory_tracking.macros.loop import LEAVE
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.tzroutine import itinerary
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import installed_active_zones
from inventory_tracking.terror.tracker import ZoneTracker
from tests.inventory_tracking.macros.acts.harness import ActGame, ZoneWalk
from tests.inventory_tracking.macros.acts.test_act2 import tomb_entrances
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS


def zone_named(name: str) -> frozenset[int]:
    return next(zone.core for zone in installed_active_zones() if zone.name == name)


TAL_RASHAS = zone_named('Act2-TalRashas')
TOWER = zone_named('Act1-Tower')


def test_an_act_3_game_with_the_tal_rasha_rotation_kills_duriel_right_after_mephisto(monkeypatch):
    # Duriel was never killed in 16 TZ games: the rotation's tombs root last behind the shard act's roots, the zone
    # turned before it (cyberr14 10-21 21:40, cyberr15 22:26). zonenav.py ROTATION_BOSSES_FIRST
    monkeypatch.setattr(zonenav, 'ACTS', frozenset({3}))
    act = ActGame(3, monkeypatch, rotation=TAL_RASHAS)
    tomb_entrances(act)
    walk = act.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert walk.kills[:2] == ['Mephisto', 'Duriel']  # the act's boss, then the rotation's
    assert walk.kills.count('Duriel') == 1
    monkeypatch.setattr(zonenav, 'ROTATION_BOSSES_FIRST', False)
    monkeypatch.setattr(zonenav, 'ROTATION_ANY_ACT', False)  # it too puts the rotation after the act's boss
    act = ActGame(3, monkeypatch, rotation=TAL_RASHAS)
    tomb_entrances(act)
    before = act.play()
    assert before.kills[-1] == 'Duriel'  # last, as before: the rotation that turned in 30 min took him away


def turning_game(monkeypatch, *, at: int = 35) -> ZoneWalk:
    """A TZ+ game of the Catacombs whose zone turns to the Forgotten Tower's as the run of level `at` ends."""
    monkeypatch.setattr(zonenav, 'ROTATION', True)
    walk = ZoneWalk(monkeypatch, CATACOMBS)
    game = walk.game
    game.progress.wanted = lambda level: level in game.zone  # the tracker's read, as it turns
    turned: list[int] = []

    def on_run(area: int) -> None:
        if area == at and not turned:
            turned.append(area)
            game.zone = TOWER

    walk.on_run = on_run
    return walk


def test_a_zone_turned_under_the_game_keeps_its_bosses_and_blocks_its_other_levels(monkeypatch, caplog):
    # The audit's "zone rotation" (72 boss-game rows in 32 games): Andariel seen 64 units off as Catacombs Level 4 was
    # no longer terrorized (10-21 06:00), a replanned zone dropping the old zone's bosses. tzloop.py BOSS_ZONES
    caplog.set_level(logging.INFO)
    walk = turning_game(monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert 'Andariel' in walk.kills  # the turned zone's boss, then the new zone's
    assert 'The Countess' in walk.kills
    assert walk.kills.index('Andariel') < walk.kills.index('The Countess')  # her level under way: she first
    assert not {32, 33, 34} & set(walk.runs)  # the turned zone's levels holding no boss: blocked
    assert 'Macro: zone: turned and kept in the plan for their bosses: Act1-Catacombs (Andariel (Catacombs Level 4)' \
        in caplog.text  # fmt: skip


def test_without_boss_zones_the_turned_zones_boss_is_left_as_before(monkeypatch):
    monkeypatch.setattr(tzloop, 'BOSS_ZONES', False)
    walk = turning_game(monkeypatch).play()
    assert 'Andariel' not in walk.kills
    assert 'The Countess' in walk.kills


@pytest.mark.parametrize(('rotation', 'policy'), [(True, ON_THE_WAY), (False, ZONE_LEFT)])
def test_a_level_the_zone_left_with_a_boss_alive_under_it_is_worked_on_the_way(monkeypatch, rotation, policy):
    # hunting/choice.py BOSS_ROTATION: the run on Catacombs Level 3 goes on for Andariel under it (zone navigation);
    # off the graph the level's own bosses only (none on Level 3). BOSSES_ONLY off: on the way, as before
    monkeypatch.setattr(choice, 'BOSSES_ONLY', False)
    monkeypatch.setattr(zonenav, 'ROTATION', rotation)
    agenda = Agenda()
    agenda.begin('cyberr29')
    plan = itinerary(CATACOMBS)
    assert plan is not None
    agenda.plan = plan
    tracker = ZoneTracker()
    tzloop.bosses_planned(agenda, Progress(ROUTES, PERFORMED, tracker.killed), plan)
    # The hunter's and the read's parts it asks: their policy, the agenda, the said level; the game's name
    hunter = cast(Any, SimpleNamespace(agenda_policy=lambda area: ZONE_LEFT, agenda=agenda, zone_left=None))
    world = cast(Any, SimpleNamespace(game_name='cyberr29'))
    assert choice.level_policy(hunter, world, 36) == policy
    assert choice.level_policy(hunter, world, 37) == ON_THE_WAY
    tracker.slain = frozenset({'Andariel'})
    assert choice.level_policy(hunter, world, 37) == ZONE_LEFT


def test_a_level_the_zone_left_is_worked_for_its_bosses_alone(monkeypatch):
    # hunting/choice.py BOSSES_ONLY (2026-10-23, lever 2 of rca/2026-10-22/exp-hour-findings.md): its plain monsters
    # no goal, its bosses still killed ("Kill every boss")
    from inventory_tracking.macros.agenda import BOSS_WAY

    monkeypatch.setattr(zonenav, 'ROTATION', True)  # zone navigation: Andariel under Level 3 holds it
    agenda = Agenda()
    agenda.begin('cyberr29')
    plan = itinerary(CATACOMBS)
    assert plan is not None
    agenda.plan = plan
    tracker = ZoneTracker()
    tzloop.bosses_planned(agenda, Progress(ROUTES, PERFORMED, tracker.killed), plan)
    hunter = cast(Any, SimpleNamespace(agenda_policy=lambda area: ZONE_LEFT, agenda=agenda, zone_left=None))
    world = cast(Any, SimpleNamespace(game_name='cyberr29'))
    assert choice.BOSSES_ONLY
    assert choice.level_policy(hunter, world, 36) == BOSS_WAY
    assert choice.level_policy(hunter, world, 37) == BOSS_WAY
    tracker.slain = frozenset({'Andariel'})
    assert choice.level_policy(hunter, world, 37) == ZONE_LEFT  # dead: the run ends at once


def test_a_zone_turned_under_the_game_still_kills_its_boss_with_bosses_only(monkeypatch):
    # The turned Catacombs' Andariel killed on its levels worked for her alone (hunting/choice.py BOSSES_ONLY)
    walk = turning_game(monkeypatch).play()
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.kills.index('Andariel') < walk.kills.index('The Countess')
