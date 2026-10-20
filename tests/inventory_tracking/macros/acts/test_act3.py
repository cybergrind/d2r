"""Act 3 by its script (macros/acts/act3.py): the player's order (2026-10-20 ~22:50: "act3: act3 shard -> durance ->
mephisto -> rest of zones") pinned, and the game walked: the Southern shard, the Durance from its waypoint to Mephisto,
then the act zone by zone down from Travincal, then the rotation.

The walk needs loop.py REPEATS' TZ_PORTAL over the act's 15 trips (raised 2026-10-20) and tzloop.py `reenter` for the
second trip through the Kurast Causeway."""

from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from tests.inventory_tracking.macros.acts.harness import ActGame, line_of, plan_of, trips_of
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS


KURAST_DOCKS = 75
PLAN = (
    'Macro: tz: zone Act3-Manual + Act1-Catacombs: Mephisto from 101: [101, 102]; Mephisto from 83: [83, 100]; '
    'Ruined Fane from 81: [81, 82, 98]; Disused Reliquary from 81: [81, 82, 99]; '
    'Forgotten Reliquary from 81: [81, 96]; Forgotten Temple from 81: [81, 97]; Kurast Sewers from 80: [80, 92, 93]; '
    'Ruined Temple from 80: [80, 94]; Disused Fane from 80: [80, 95]; Lower Kurast from 79: [79]; '
    'Flayer Dungeon from 78: [78, 88, 89, 91]; Swampy Pit from 78: [78, 86, 87, 90]; Great Marsh from 77: [77]; '
    'Arachnid Lair from 76: [76, 84]; Spider Cavern from 76: [76, 85]; Andariel from 35: [35, 36, 37]'
)
ACT_LEVELS = frozenset(range(76, 103))  # Spider Forest .. Durance of Hate Level 3 (the manual zone Act3-Manual)


def test_the_act_3_plan_is_the_durance_to_mephisto_then_the_act_down_from_travincal(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 3, rotation=CATACOMBS)
    assert any(record.getMessage().startswith(PLAN + '; skipped') for record in caplog.records)
    assert line_of(plan) in PLAN
    assert trips_of(plan) == [
        ('Mephisto', 101, (101, 102)),  # the Durance: its waypoint (Level 2), Level 3, Mephisto
        ('Mephisto', 83, (83, 100)),  # Travincal's Council, Durance Level 1
        ('Ruined Fane', 81, (81, 82, 98)),  # Upper Kurast and the Causeway worked on the way
        ('Disused Reliquary', 81, (81, 82, 99)),  # the Causeway's other temple
        ('Forgotten Reliquary', 81, (81, 96)),
        ('Forgotten Temple', 81, (81, 97)),
        ('Kurast Sewers', 80, (80, 92, 93)),  # the Bazaar worked on the way
        ('Ruined Temple', 80, (80, 94)),
        ('Disused Fane', 80, (80, 95)),
        ('Lower Kurast', 79, (79,)),
        ('Flayer Dungeon', 78, (78, 88, 89, 91)),  # the Flayer Jungle worked on the way
        ('Swampy Pit', 78, (78, 86, 87, 90)),
        ('Great Marsh', 77, (77,)),
        ('Arachnid Lair', 76, (76, 84)),  # the Spider Forest worked on the way
        ('Spider Cavern', 76, (76, 85)),
        ('Andariel', 35, (35, 36, 37)),  # the rotation
    ]
    assert not any(trip.passes for trip in plan.excursions)  # every level worked as it is crossed: no trip again
    assert 'Macro: act:' not in caplog.text  # no step skipped
    covered = [level for trip in plan.excursions for level in trip.areas if level in ACT_LEVELS]
    assert set(covered) == ACT_LEVELS
    # No trip wasted: each works a level no trip before it did
    seen: set[int] = set()
    for trip in plan.excursions:
        assert set(trip.areas) - seen, trip
        seen |= set(trip.areas)


def test_an_act_3_game_is_the_shard_then_mephisto_first_then_the_act_then_the_rotation(monkeypatch):
    walk = ActGame(3, monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [3]
    home = ('portal', KURAST_DOCKS)
    assert walk.moves == [
        ('waypoint', 101),  # Durance 2, then 3 and Mephisto
        ('door', 102),
        home,
        ('waypoint', 83),  # Travincal, then Durance 1
        ('door', 100),
        home,
        ('waypoint', 81),  # Upper Kurast, the Causeway, the Ruined Fane
        ('door', 82),
        ('door', 98),
        home,
        ('waypoint', 81),  # through the Causeway again, to the Disused Reliquary
        ('door', 82),
        ('door', 99),
        home,
        ('waypoint', 81),
        ('door', 96),
        home,
        ('waypoint', 81),
        ('door', 97),
        home,
        ('waypoint', 80),  # the Bazaar, the Sewers
        ('door', 92),
        ('door', 93),
        home,
        ('waypoint', 80),
        ('door', 94),
        home,
        ('waypoint', 80),
        ('door', 95),
        home,
        ('waypoint', 79),  # Lower Kurast
        home,
        ('waypoint', 78),  # the Flayer Jungle, the Flayer Dungeon
        ('door', 88),
        ('door', 89),
        ('door', 91),
        home,
        ('waypoint', 78),  # the Swampy Pit
        ('door', 86),
        ('door', 87),
        ('door', 90),
        home,
        ('waypoint', 77),  # the Great Marsh
        home,
        ('waypoint', 76),  # the Spider Forest, the Arachnid Lair
        ('door', 84),
        home,
        ('waypoint', 76),  # the Spider Cavern
        ('door', 85),
        home,
        ('waypoint', 35),  # the rotation: the Catacombs, Andariel
        ('door', 36),
        ('door', 37),
    ]
    assert set(walk.levels) == ACT_LEVELS | {35, 36, 37}  # every level of the act run
    assert walk.levels[:2] == [101, 102]  # Mephisto first
    assert walk.kills == [
        'Mephisto',
        'Ismail Vilehand',  # the Council
        'Battlemaid Sarina',  # the Ruined Temple
        'Witch Doctor Endugu',  # Flayer Dungeon 3
        'Sszark the Burning',  # the Spider Cavern
        'Andariel',
    ]
    assert walk.legs[-1] == LEAVE
