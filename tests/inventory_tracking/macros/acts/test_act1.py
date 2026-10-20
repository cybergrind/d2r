"""Act 1 by its script (macros/acts/act1.py), the player's order of 2026-10-20 ~22:50: "act1 shard -> catacombs 2 -> 3
-> 4 -> andariel -> marsh -> tower -> countess -> rest of zones one by one". The plan pinned, the Forgotten Tower's
way on checked, and the game walked: the Western shard, Andariel, the Countess, then the act's zones one by one."""

from inventory_tracking.levels.exits import short_name
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.acts.harness import ActGame, line_of, plan_of, trips_of


PLAN = (
    'Macro: tz: zone Act1-Manual: Andariel from 35: [35, 36, 37]; Countess from 6: [6, 20, 21, 22, 23, 24, 25]; '
    'Hole from 6: [6, 11, 15]; Andariel from 32: [32, 33, 34]; Andariel from 27: [27, 28, 29, 30, 31]; '
    'Pit from 27: [27, 26, 7, 12, 16]; Underground Passage from 5: [5, 10, 14]; Tristram from 4: [4, 38]; '
    'Crypt from 3: [3, 17, 18]; Mausoleum from 3: [3, 17, 19]; Cave from 3: [3, 9, 13]; Den of Evil from 1: [1, 2, 8]'
)


def test_the_act_1_plan_is_andariel_then_the_countess_then_the_zones_one_by_one(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 1)
    assert any(record.getMessage() == PLAN + '; skipped none' for record in caplog.records)
    assert trips_of(plan)[:2] == [
        ('Andariel', 35, (35, 36, 37)),  # "catacombs 2 -> 3 -> 4 -> andariel", worked on the way
        ('Countess', 6, (6, 20, 21, 22, 23, 24, 25)),  # "marsh -> tower -> countess", worked on the way
    ]
    assert all(not trip.passes for trip in plan.excursions)  # nothing only crossed: every level worked on its trip
    assert line_of(plan) in PLAN
    assert 'Macro: act:' not in caplog.text  # no step skipped
    zone = manual_zone(1)
    assert zone is not None
    assert set(zone.areas) <= {area for trip in plan.excursions for area in trip.areas}  # all 37 levels have a trip


def test_the_forgotten_tower_has_no_handler_and_its_way_on_is_the_warps_generic_mark():
    # No handler for level 20 (one 8x8 preset, no monsters): levels/exits.py `warp_exits` marks its stairs down by
    # the DS1 warp, labelled with the level behind them (tests/inventory_tracking/levels/test_exits.py pins it),
    # the label the Countess route's stage walks to
    countess = next(route for route in ROUTES if route.name == 'Countess')
    tower = next(script for script in countess.scripts if script.area == 20)
    assert handler_for(20) is None
    assert [(stage.mark, stage.to) for stage in tower.stages] == [(short_name(21), 21)]


def test_an_act_1_game_is_the_shard_then_andariel_then_the_countess_then_every_level(monkeypatch):
    walk = ActGame(1, monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [1]
    assert walk.waypoints == [35, 6, 6, 32, 27, 27, 5, 4, 3, 3, 3, 103]  # 103: the rotation (the Steppes)
    assert walk.moves[:12] == [
        ('waypoint', 35),
        ('door', 36),
        ('door', 37),  # Andariel
        ('portal', 1),
        ('waypoint', 6),
        ('door', 20),  # the Forgotten Tower
        ('door', 21),
        ('door', 22),
        ('door', 23),
        ('door', 24),
        ('door', 25),  # the Countess
        ('portal', 1),
    ]
    assert ('walk out', 2) in walk.moves  # the Blood Moor out of the Rogue Encampment
    zone = manual_zone(1)
    assert zone is not None
    assert set(walk.levels) >= set(zone.areas)  # every level of the act run
    assert walk.levels[:10] == [35, 36, 37, 6, 20, 21, 22, 23, 24, 25]
    assert walk.kills == ['Andariel', 'The Countess', 'Bonebreaker', 'Blood Raven', 'Coldcrow', 'Corpsefire', 'Izual']
    assert walk.legs[-1] == LEAVE
