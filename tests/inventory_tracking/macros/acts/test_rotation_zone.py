"""The rotating terror zones played by zone navigation (macros/zonenav.py ROTATION, stage 2 of macros/zone-nav-plan.md,
2026-10-21): every installed zone walked in TZ+ and Full clear TZ with the switch off and on, its open passages crossed
as the live run crosses them (harness.py `crossing`). On: the same levels and bosses, never more waypoints, no stop;
Kurast's three roots, the Lost City's and the Spider Forest's children from one waypoint, the Canyon's tombs a tour."""

import logging

import pytest

from inventory_tracking.macros import tzloop, zonenav
from inventory_tracking.macros.loop import LEAVE, TZ, TZ_CLEAR, TZ_UP, Loop
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import installed_active_zones
from tests.inventory_tracking.macros.acts.harness import NEAREST_TOMBS, TRUE_TOMB, ActGame, Walk, ZoneWalk, crossing


FORTRESS, LUT_GHOLEIN = 103, 40
ZONES = {zone.name: zone for zone in installed_active_zones()}


def rotation(monkeypatch, name: str, on: bool, kind=TZ) -> Walk:
    monkeypatch.setattr(zonenav, 'ROTATION', on)
    return crossing(ZoneWalk(monkeypatch, frozenset(ZONES[name].core), kind)).play()


@pytest.mark.parametrize('kind', [TZ, TZ_CLEAR], ids=['tz', 'tzclear'])
@pytest.mark.parametrize('name', sorted(ZONES))
def test_every_installed_zone_plays_the_same_levels_with_no_more_waypoints(monkeypatch, name, kind):
    off = rotation(monkeypatch, name, False, kind)
    on = rotation(monkeypatch, name, True, kind)

    assert on.stopped == off.stopped  # none, or the same "not playable" wait (the Moo Moo Farm: no excursion)
    if off.stopped is None:
        assert on.legs[-1] == LEAVE
    assert set(on.levels) == set(off.levels)
    assert set(on.kills) == set(off.kills)
    assert len(on.waypoints) <= len(off.waypoints)
    assert TZ_UP not in off.legs  # the switch off: the itinerary's trips, no climb


@pytest.mark.parametrize(
    ('name', 'before', 'after', 'climbs'),
    [
        ('Act3-Kurast', [80, 80, 80, 81, 81, 81, 81, 79, FORTRESS], [80, 81, 79, FORTRESS], 5),
        ('Act2-LostCity', [44, 44], [44], 1),
        ('Act3-SpiderForest', [76, 76, FORTRESS], [76, FORTRESS], 1),
        ('Act1-BurialGrounds', [3, 3], [3], 1),
        ('Act3-FlayerJungle', [78, 78, FORTRESS], [78, 78, FORTRESS], 0),  # one root, two deep chains: "TP for deep"
        ('Act1-Tower', [6, 6], [6, 6], 0),  # Black Marsh one root: the Tower's chain and the Hole, both deep
        ('Act5-GlacialTrail', [115], [115], 0),  # the Drifter Cavern its root's last: the Town Portal after it
    ],
)
def test_the_waypoints_of_the_rotating_zones_with_children(monkeypatch, name, before, after, climbs):
    off = rotation(monkeypatch, name, False)
    on = rotation(monkeypatch, name, True)

    assert sorted(off.waypoints) == sorted(before)
    assert on.waypoints == after
    assert on.legs.count(TZ_UP) == climbs


def test_kurast_is_three_roots_each_with_its_temples_climbed_out_of(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    walk = rotation(monkeypatch, 'Act3-Kurast', True)

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert 'Macro: zone: graph Act3-Kurast: 80 (92 (93), 94, 95); 81 (82 (98, 99), 96, 97); 79;' in caplog.text
    assert ('walk', 82) in walk.moves  # Upper Kurast's open passage to the Causeway, crossed by the run
    assert 'Macro: zone: Kurast Bazaar (80) cleared' in caplog.text


@pytest.mark.parametrize('kind', [TZ, TZ_CLEAR], ids=['tz', 'tzclear'])
def test_the_canyon_is_a_root_whose_seven_tombs_are_toured_each_once_by_the_nearest_entrance(monkeypatch, kind):
    walk = rotation(monkeypatch, 'Act2-TalRashas', True, kind)

    assert walk.stopped is None, (walk.stopped, walk.where)
    # Duriel's Lair from the true tomb (harness.py TRUE_TOMB, the third nearest; levels/handlers/tal_rasha.py DURIEL,
    # on since 2026-10-21): through the Orifice's portal, Duriel, the Town Portal home and the Canyon's waypoint again
    assert walk.waypoints == [46, 46]
    tombs = [area for what, area in walk.moves if what == 'door' and area != 46]
    assert tombs == list(NEAREST_TOMBS)  # which entrance leads into which tomb is the game's: the nearest first
    third = NEAREST_TOMBS.index(TRUE_TOMB) + 1
    assert walk.runs == [46, *NEAREST_TOMBS[:third], 73, *NEAREST_TOMBS[third:]]  # the Canyon first, each level once
    assert walk.moves[walk.moves.index(('door', TRUE_TOMB)) + 1] == ('portal', 73)
    assert walk.kills == ['Duriel']
    assert walk.legs.count(TZ_UP) == 5  # out of each but the true tomb (its way on the portal) and the last
    assert walk.legs[-1] == LEAVE


def test_a_tomb_left_unfinished_is_blocked_once_the_canyon_is_stood_in_again(monkeypatch, caplog):
    # Its entrance was gone through (the tour skips it) and which mark leads back is not known: blocked, said, and the
    # tour goes on with the others, never a stall
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'ROTATION', True)
    game = crossing(ZoneWalk(monkeypatch, frozenset(ZONES['Act2-TalRashas'].core), TZ))
    first = NEAREST_TOMBS[0]
    left: list[int] = []

    def run_of(area: int) -> None:
        if area == first and not left:
            left.append(area)
            game.game.unmapped.add(area)  # its run reads no map: not explored
            game.game.go('waypoint', 46)  # back in the Canyon by its waypoint (a trip to town and back)

    game.on_run = run_of
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert 'entered and left unfinished' in caplog.text
    assert set(walk.levels) == {46, *NEAREST_TOMBS, 73}  # and Duriel's Lair from the true tomb (harness.py TRUE_TOMB)
    assert walk.runs.count(first) == 1


def restarted(walk: ZoneWalk, store) -> None:
    """A service restart mid-game: the loop and the route's progress afresh (macros/runner.py builds them anew), the
    game and the loop's store kept."""
    game = walk.game
    kind, area = game.loop.kind, game.area
    records = game.loop.records
    game.loop = Loop(on=True, kind=kind, chosen=True, prebuffed=game.play.world.game_name, store=store)
    game.loop.records = records  # the game's record (macros/midgame.py RECORD), in the tracker's store
    game.loop.start()
    game.progress = Progress(ROUTES, PERFORMED, game.book.killed, wanted=lambda level: level in game.zone)
    game.progress.note(game.play.world.game_name, area)


@pytest.mark.parametrize('resume', [True, False])
def test_a_service_restart_mid_zone_goes_on_where_it_was_with_the_facts_kept(monkeypatch, tmp_path, caplog, resume):
    # Stage 3 (zonenav.py RESUME): the zone's facts in the game's record (macros/midgame.py RECORD, 2026-10-22), taken
    # back by the first leg after a restart in the same game; the Bazaar's root, done before the restart, is not played
    # again
    from inventory_tracking.macros import midgame

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'ROTATION', True)
    monkeypatch.setattr(midgame, 'RECORD', resume)
    store = tmp_path / 'loop-items.json'
    walk = crossing(ZoneWalk(monkeypatch, frozenset(ZONES['Act3-Kurast'].core), TZ))
    walk.game.loop.store = store
    walk.game.loop.records = walk.game.book
    before = walk.play(legs=60, until=lambda game: game.area == 81)
    assert before.stopped is None
    assert {80, 92, 93, 94, 95} <= set(before.levels)
    restarted(walk, store)
    after = walk.play()
    runs = after.runs[len(before.runs) :]

    assert after.stopped is None, (after.stopped, after.where)
    assert after.legs[-1] == LEAVE
    if resume:
        assert 'taken up after a restart' in caplog.text
        assert not {80, 92, 93, 94, 95} & set(runs)  # done before it
        assert after.waypoints[len(before.waypoints) :] == [79, FORTRESS]
    else:
        assert 80 in runs  # afresh: the Bazaar's root played again
        assert 'taken up after a restart' not in caplog.text


RIVER = frozenset((106, 107))


@pytest.mark.parametrize('first', [True, False])
def test_a_shard_games_rotation_in_the_fortresss_act_is_played_before_the_shards_act(monkeypatch, first, caplog):
    # cyberr5 (14:00-14:12 on 2026-10-21): the graph 'Act3-Manual + Act4-RiverOfFlame' put the River's root after every
    # Act 3 root; an Act 3 game takes ~48 min, the rotation turns every 30 (tzloop.py ZONE_TURN), so the River was never
    # reached while terrorized. The player: "I haven't seen your visit to the rotating level (river of flame)". The
    # shard is used in the Fortress, one waypoint from the River
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((3,)))
    monkeypatch.setattr(zonenav, 'ROTATION_FIRST', first)
    monkeypatch.setattr(zonenav, 'ROTATION_ANY_ACT', False)  # the order of before 2026-10-23 (tested below)
    walk = crossing(ActGame(3, monkeypatch, rotation=RIVER)).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert {106, 107} <= set(walk.levels)
    if first:
        assert walk.waypoints[:2] == [106, 101]  # the River from the Fortress, then Act 3 by its script (Mephisto)
        assert 'Macro: zone: the rotation first' in caplog.text
    else:
        assert walk.waypoints[0] == 101
        assert walk.waypoints[-1] == 106  # after every Act 3 root: its Town Portal ends in the Fortress


@pytest.mark.parametrize('left', [tzloop.ZONE_TURN / 2, zonenav.ROTATION_LEAST - 1])
def test_a_shard_games_rotation_of_another_act_comes_right_after_the_act_boss(monkeypatch, caplog, left):
    # zonenav.py ROTATION_ANY_ACT (2026-10-23; lever 3 of rca/2026-10-22/exp-hour-findings.md): a Shard: Act 1 game
    # with the Outer Steppes' rotation (act 4) plays Andariel first ("act boss first"), then the rotation while its slot
    # lasts, then act 1's rest; with the slot nearly gone, the order of before (the Fortress's act first)
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((1,)))
    monkeypatch.setattr(tzloop, 'slot_left', lambda: left)
    walk = crossing(ActGame(1, monkeypatch)).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert {'Andariel', 'Izual'} <= set(walk.kills)
    if left >= zonenav.ROTATION_LEAST:
        assert walk.kills[:2] == ['Andariel', 'Izual']
        assert walk.runs[:5] == [35, 36, 37, 104, 105]  # Andariel's root, then the rotation's
        assert 'Macro: zone: the rotation from any act' in caplog.text
    else:
        assert walk.kills[:2] == ['Izual', 'Andariel']
        assert 'Macro: zone: the rotation from any act' not in caplog.text
    assert len(walk.runs) == len(set(walk.runs))  # each level once: the act's all played


def test_a_rotation_turned_before_its_roots_come_up_is_dropped_and_the_game_goes_on(monkeypatch):
    # The plan is read afresh at each leg (tzloop.py `zone_of`: the tracker's terror zones now): a rotation that turned
    # is no root any more, and the new one's are added
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((3,)))
    monkeypatch.setattr(zonenav, 'ROTATION_FIRST', False)
    game = crossing(ActGame(3, monkeypatch, rotation=RIVER))

    def run_of(area: int) -> None:
        if area == 102:
            game.game.zone = frozenset()  # the 30 minutes' turn: the River no longer terrorized

    game.on_run = run_of
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert not {106, 107} & set(walk.levels)
    assert walk.legs[-1] == LEAVE
