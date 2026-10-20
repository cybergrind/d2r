"""Act 4 by its script (macros/acts/act4.py): the live plan of 2026-10-20 22:00-22:39 (both games clean, ~11M exp/h)
pinned, and the game walked: the Deep shard, Diablo from the River of Flame, the River's rest, the City, the Steppes and
the Plains (Izual), then the rotation."""

from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from tests.inventory_tracking.macros.acts.harness import ActGame, line_of, plan_of, trips_of
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS, FORTRESS


LIVE = (
    'Macro: tz: zone Act4-Manual + Act1-Catacombs: Diablo from 107: [107, 108], [107] crossed to the boss, worked '
    'after it; Diablo from 107: [107]; Diablo from 106: [106]; Izual from 103: [103, 104, 105]; '
    'Andariel from 35: [35, 36, 37]'
)


def test_the_act_4_plan_is_the_live_one(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 4, rotation=CATACOMBS)
    assert any(record.getMessage().startswith(LIVE + '; skipped') for record in caplog.records)
    assert trips_of(plan) == [
        ('Diablo', 107, (107, 108)),  # the River crossed to the Sanctuary: the seals, Diablo
        ('Diablo', 107, (107,)),  # the River's rest after the kill
        ('Diablo', 106, (106,)),  # the City of the Damned
        ('Izual', 103, (103, 104, 105)),  # the Steppes and the Plains, walked out of the Fortress
        ('Andariel', 35, (35, 36, 37)),  # the rotation
    ]
    assert plan.excursions[0].passes == frozenset((107,))
    assert line_of(plan) in LIVE
    assert 'Macro: act:' not in caplog.text  # no step skipped


def test_an_act_4_game_is_the_shard_then_diablo_first_then_the_act_then_the_rotation(monkeypatch):
    walk = ActGame(4, monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [4]
    assert walk.moves == [
        ('waypoint', 107),
        ('door', 108),  # straight through the River to the Sanctuary
        ('portal', FORTRESS),  # Diablo dead: home for the next trip
        ('waypoint', 107),  # the River's rest
        ('portal', FORTRESS),
        ('waypoint', 106),  # the City of the Damned
        ('portal', FORTRESS),
        ('walk out', 104),  # the Steppes, then the Plains and Izual
        ('door', 105),
        ('portal', FORTRESS),
        ('waypoint', 35),  # the rotation: the Catacombs, Andariel
        ('door', 36),
        ('door', 37),
    ]
    assert walk.levels == [107, 108, 106, 104, 105, 35, 36, 37]
    assert walk.runs.index(107, 1) > walk.runs.index(108)  # the River's own run after Diablo's
    seals = ['Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls']
    assert walk.kills == [*seals, 'Diablo', 'Izual', 'Andariel']
    assert walk.legs[-1] == LEAVE
