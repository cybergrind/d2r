"""Act 2 by its script (macros/acts/act2.py). The player, 2026-10-20 ~22:50: "act2: act2 shard -> canyon of the
magic -> toms ... -> duriel -> rest of tombs -> arcane sanctuary -> summoner -> rest of arcane sanctuary -> rest of
zones one by one". The plan pinned, Duriel's skip said, and the game walked: the Eastern shard, the Canyon and its seven
tombs, the Arcane Sanctuary, the Palace Cellars and the Harem, the sewers, the act's rest, then the rotation."""

from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from tests.inventory_tracking.macros.acts.harness import ActGame, line_of, plan_of, trips_of
from tests.inventory_tracking.macros.test_tzloop import CANYON, CATACOMBS, LUT_GHOLEIN, NEAREST, TOMBS


PLAN = (
    "Macro: tz: zone Act2-Manual + Act1-Catacombs: Tal Rasha's Tombs from 46: [46, 66, 67, 68, 69, 70, 71, 72], "
    '[66, 67, 68, 69, 70, 71, 72] a tour from 46 one by one; Summoner from 74: [74]; Summoner from 52: [52, 53, 54]; '
    'Harem from 52: [52, 51, 50]; Radament from 48: [48, 49]; Sewers 1 from 48: [48, 47]; Halls of the Dead from 42: '
    '[42, 56, 57, 60]; Maggot Lair from 43: [43, 62, 63, 64]; Claw Viper Temple from 44: [44, 45, 58, 61]; Stony Tomb '
    'from 40: [40, 41, 55, 59]; Ancient Tunnels from 44: [44, 65]; Andariel from 35: [35, 36, 37]'
)
DURIEL = "Macro: act: act 2 step 2 (Duriel to 73): no way into Duriel's Lair yet"


def test_the_act_2_plan_is_the_players_order_with_duriel_skipped_and_said(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 2, rotation=CATACOMBS)
    said = [record.getMessage() for record in caplog.records]
    assert any(line.startswith(PLAN + '; skipped') for line in said)
    assert trips_of(plan) == [
        ("Tal Rasha's Tombs", 46, (46, *TOMBS)),  # the Canyon, then the tombs one by one
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
    ]
    assert line_of(plan) in PLAN
    assert all(not trip.passes for trip in plan.excursions)  # every level worked on the way
    # Duriel's Lair is the plan's one level skipped, its step said; no other step skipped, no trip blocked
    assert [line for line in said if line.startswith('Macro: act:')] == [line for line in said if DURIEL in line]
    assert len([line for line in said if DURIEL in line]) == 1
    skipped = next(line for line in said if line.startswith(PLAN)).split('; skipped ')[1]
    assert '73 (no catalogue excursion covers it)' in skipped
    assert not any(f"'{area} (" in skipped for area in (47, 50, 51, 52, 53, 54, 74))


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
    tour = [move for tomb in NEAREST for move in (('tomb', tomb), ('door', CANYON))][:-1]  # the last left by portal
    home = ('portal', LUT_GHOLEIN)
    assert walk.moves == [
        ('waypoint', CANYON),
        *tour,
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
    ]
    assert walk.runs == [CANYON, *NEAREST, 74, 52, 53, 54, 51, 50, 48, 49, 47, 42, 56, 57, 60, 43, 62, 63, 64, 44, 45,
                         58, 61, 41, 55, 59, 65, 35, 36, 37]  # fmt: skip
    assert walk.kills == [
        'The Summoner',
        'Radament',
        'Bloodwitch the Wild',
        'Coldworm the Burrower',
        'Fangskin',
        'Creeping Feature',
        'Andariel',
    ]  # no Duriel: his step skipped
    assert walk.legs[-1] == LEAVE
