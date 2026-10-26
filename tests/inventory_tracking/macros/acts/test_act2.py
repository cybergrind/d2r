"""Act 2 by its script (macros/acts/act2.py). The player, 2026-10-20 ~22:50: "act2: act2 shard -> canyon of the
magic -> toms ... -> duriel -> rest of tombs -> arcane sanctuary -> summoner -> rest of arcane sanctuary -> rest of
zones one by one". The plan pinned and the game walked: the Eastern shard, the Canyon and its seven tombs with
Duriel's Lair from the true tomb (levels/handlers/tal_rasha.py DURIEL, on since 2026-10-21; before, his step skipped and
said), the Arcane Sanctuary, the Palace Cellars and the Harem, the sewers, the act's rest, then the rotation."""

from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from tests.inventory_tracking.macros.acts.harness import TRUE_TOMB, ActGame, line_of, plan_of, trips_of
from tests.inventory_tracking.macros.test_tzloop import CANYON, CATACOMBS, LUT_GHOLEIN, NEAREST, TOMBS


PLAN = (
    "Macro: tz: zone Act2-Manual + Act1-Catacombs: Tal Rasha's Tombs from 46: [46, 66, 67, 68, 69, 70, 71, 72, 73], "
    '[66, 67, 68, 69, 70, 71, 72] a tour from 46 one by one; Summoner from 74: [74]; Summoner from 52: [52, 53, 54]; '
    'Harem from 52: [52, 51, 50]; Radament from 48: [48, 49]; Sewers 1 from 48: [48, 47]; Halls of the Dead from 42: '
    '[42, 56, 57, 60]; Maggot Lair from 43: [43, 62, 63, 64]; Claw Viper Temple from 44: [44, 45, 58, 61]; Stony Tomb '
    'from 40: [40, 41, 55, 59]; Ancient Tunnels from 44: [44, 65]; Andariel from 35: [35, 36, 37]; '
    'Andariel from 32: [32, 33, 34]'
)
LAIR = 73


def test_the_act_2_plan_is_the_players_order_with_duriel_on_the_tombs_tour(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 2, rotation=CATACOMBS)
    said = [record.getMessage() for record in caplog.records]
    assert any(line.startswith(PLAN + '; skipped') for line in said)
    assert trips_of(plan) == [
        ("Tal Rasha's Tombs", 46, (46, *TOMBS, LAIR)),  # the Canyon, the tombs one by one, Duriel from the true one
        ('Summoner', 74, (74,)),  # the Arcane Sanctuary, the Summoner
        ('Summoner', 52, (52, 53, 54)),  # the rest of it: the Palace Cellars
        ('Harem', 52, (52, 51, 50)),  # and the Harem, up the stairs
        ('Radament', 48, (48, 49)),
        ('Sewers 1', 48, (48, 47)),
        ('Halls of the Dead', 42, (42, 56, 57, 60)),  # the act's rest, zone by zone
        ('Maggot Lair', 43, (43, 62, 63, 64)),
        ('Claw Viper Temple', 44, (44, 45, 58, 61)),
        ('Stony Tomb', 40, (40, 41, 55, 59)),
        ('Ancient Tunnels', 44, (44, 65)),
        ('Andariel', 35, (35, 36, 37)),  # the rotation
        ('Andariel', 32, (32, 33, 34)),  # its levels before her (tzroutine.py SKIPPED_TRIPS, 2026-10-22)
    ]
    assert line_of(plan) in PLAN
    assert all(not trip.passes for trip in plan.excursions)  # every level worked on the way
    # No step skipped (before 2026-10-21 Duriel's, said), no act 2 level skipped, no trip blocked
    assert not any(line.startswith('Macro: act:') for line in said)
    skipped = next(line for line in said if line.startswith(PLAN)).split('; skipped ')[1]
    assert not any(f"'{area} (" in skipped for area in (47, 50, 51, 52, 53, 54, 73, 74))


def tomb_entrances(act: ActGame) -> None:
    """The Canyon's tour through the nearest entrance not entered, noted gone through (test_tzloop.py `tomb_tour`, the
    runner's macros/route.py `note_toured`): the harness's own way on runs the level again at a tour's stage (it has
    no level to go into), so the walk stopped at the Canyon ("TZ Town Portal again and again")."""
    game, own = act.game, act.way_on

    def way_on() -> None:
        step = game.progress.step(game.area)
        if game.area != CANYON or step is None or not step.stage.tours:
            own()
            return
        used = {place for _, _, place in game.progress.facts.used}
        tomb = next(level for level in NEAREST if (float(level), 0.0) not in used)
        game.progress.used(CANYON, 'Tomb', (float(tomb), 0.0), ())
        game.go('tomb', tomb)

    act.way_on = way_on


def test_an_act_2_game_is_the_shard_then_the_tombs_then_the_sanctuary_then_the_act_then_the_rotation(monkeypatch):
    act = ActGame(2, monkeypatch)
    tomb_entrances(act)
    walk = act.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [2]
    # The tombs one by one; the true tomb's way on the Orifice's portal into Duriel's Lair, Duriel, the Town Portal
    # home and the Canyon's waypoint again for the tour's rest; the last tomb left by the Town Portal
    home = ('portal', LUT_GHOLEIN)
    third = NEAREST.index(TRUE_TOMB) + 1
    lair = [('portal', LAIR), home, ('waypoint', CANYON)]
    before = [move for tomb in NEAREST[:third] for move in (('tomb', tomb), ('door', CANYON))][:-1]
    after = [move for tomb in NEAREST[third:] for move in (('tomb', tomb), ('door', CANYON))][:-1]
    assert walk.moves == [
        ('waypoint', CANYON),
        *before,
        *lair,
        *after,
        home,
        ('waypoint', 74),  # the Arcane Sanctuary, the Summoner
        home,
        ('waypoint', 52),  # Palace Cellars 1-3
        ('door', 53),
        ('door', 54),
        home,
        ('waypoint', 52),  # crossed again, up the stairs: Harem 2, Harem 1
        ('door', 51),
        ('door', 50),
        home,
        ('waypoint', 48),  # Sewers 2, 3: Radament
        ('door', 49),
        home,
        ('waypoint', 48),  # crossed again, up the stairs: Sewers 1
        ('door', 47),
        home,
        ('waypoint', 42),  # the Halls of the Dead
        ('door', 56),
        ('door', 57),
        ('door', 60),
        home,
        ('waypoint', 43),  # the Maggot Lair
        ('door', 62),
        ('door', 63),
        ('door', 64),
        home,
        ('waypoint', 44),  # the Valley of Snakes, the Claw Viper Temple
        ('door', 45),
        ('door', 58),
        ('door', 61),
        home,
        ('walk out', 41),  # the Rocky Waste, the Stony Tomb
        ('door', 55),
        ('door', 59),
        home,
        ('waypoint', 44),  # the Ancient Tunnels
        ('door', 65),
        home,
        ('waypoint', 35),  # the rotation: the Catacombs, Andariel
        ('door', 36),
        ('door', 37),
        ('portal', 1),  # then the Inner Cloister, the Cathedral, Catacombs 1 (tzroutine.py SKIPPED_TRIPS)
        ('waypoint', 32),
        ('door', 33),
        ('door', 34),
    ]
    assert walk.runs == [CANYON, *NEAREST[:third], LAIR, *NEAREST[third:], 74, 52, 53, 54, 51, 50, 48, 49, 47, 42, 56,
                         57, 60, 43, 62, 63, 64, 44, 45, 58, 61, 41, 55, 59, 65, 35, 36, 37, 32, 33, 34]  # fmt: skip
    assert walk.kills == [
        'Duriel',  # the act's boss, from the true tomb, each level run once
        'The Summoner',
        'Radament',
        'Bloodwitch the Wild',
        'Coldworm the Burrower',
        'Fangskin',
        'Creeping Feature',
        'Andariel',
    ]
    assert walk.legs[-1] == LEAVE


def test_the_act_2_kind_uses_an_eastern_shard_from_a_stack_of_90_or_more(monkeypatch, caplog):
    # The player, 2026-10-21 ~14:45: "after that shard's stack go to 90, let's use act2 shards"; 2026-10-20: "any stone
    # with 90+ quantity". Act 2's shard is the Eastern Worldstone Shard (misc.txt xa2, class 675: terrorize.py SHARDS)
    from inventory_tracking.game.records import StashView
    from inventory_tracking.macros.terrorize import SHARD_FLOOR, SHARDS, choose_shard

    eastern, southern = 675, 676
    assert SHARDS[eastern] == 2
    assert SHARD_FLOOR == 90
    assert choose_shard(StashView((), ((eastern, 90), (southern, 150))), 2) == eastern  # the act's own, at the floor
    assert choose_shard(StashView((), ((eastern, 89), (southern, 150))), 2) is None  # never another act's
    used = ActGame(2, monkeypatch, shards=90).play(legs=3)
    assert used.shard == [2]
    with caplog.at_level('INFO'):
        under = ActGame(2, monkeypatch, shards=89).play(legs=3)
    assert under.shard == []
    assert 'Macro: act: no shard for act 2 at 90 or more' in caplog.text
