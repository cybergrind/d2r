"""Act 5 played by zone navigation (macros/zonenav.py; macros/zone-nav-plan.md §10): the same levels and bosses as the
itinerary's game, in its boss order, with fewer waypoints; the Halls of Pain and of Anguish run on their way to
Nihlathak and Pindleskin, Pindleskin fought by the Halls of Anguish trip's script, the one-floor children climbed out
of and the deep chains ended by the Town Portal."""

import logging

import pytest

from inventory_tracking.macros import zonenav
from inventory_tracking.macros.loop import LEAVE, TZ_SHARD, TZ_UP
from tests.inventory_tracking.macros.acts.harness import ActGame, Walk


HARROGATH = 109
KILLS = ['Lister the Tormentor', 'Baal', 'Nihlathak Boss', 'Pindleskin', 'Frozenstein', 'Snapchip Shatter', 'Andariel']
# Zone navigation's order: the rotation's root holding a boss alive right after the act's boss (zonenav.py
# ROTATION_BOSSES_FIRST, 2026-10-22), the rest of its act's rotation from there (ROTATION_FIRST)
ZONE_KILLS = [
    'Lister the Tormentor',
    'Baal',
    'Andariel',
    'Nihlathak Boss',
    'Pindleskin',
    'Frozenstein',
    'Snapchip Shatter',
]


@pytest.fixture
def zone(monkeypatch):
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((5,)))


def between(moves, first, then):
    """Whether `then` comes right after `first` among the moves."""
    return any(moves[index : index + 2] == [first, then] for index in range(len(moves) - 1))


def act_5(monkeypatch) -> Walk:
    walk = ActGame(5, monkeypatch).play()
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    return walk


@pytest.mark.usefixtures('zone')
def test_act_5_kills_baal_nihlathak_then_pindleskin_and_takes_fewer_waypoints(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    walk = act_5(monkeypatch)

    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [5]
    assert walk.kills == ZONE_KILLS
    # was 12 with the itinerary's trips (the Halls of Pain twice, the Keep 2 three times); 32: tzroutine.py
    # SKIPPED_TRIPS
    assert walk.waypoints == [129, 129, 35, 32, 123, 111, 113, 115, 118, 112, 117]
    assert walk.moves[:24] == [
        ('waypoint', 129),
        ('door', 130),  # the Keep 3 crossed to the boss
        ('door', 131),
        ('door', 132),  # Baal
        ('portal', HARROGATH),  # the Chamber three floors down: the Town Portal
        ('waypoint', 129),
        ('door', 130),  # the Keep 3's own run after Baal
        ('door', 129),  # climbed back to the Keep 2
        ('door', 128),  # the Keep 1, the Keep 2's last child
        ('portal', HARROGATH),
        ('waypoint', 35),  # the rotation's Catacombs: Andariel, after Baal (ROTATION_BOSSES_FIRST)
        ('door', 36),
        ('door', 37),
        ('portal', 1),
        ('waypoint', 32),  # the rest of the Catacombs from act 1 (ROTATION_FIRST): the Cathedral (SKIPPED_TRIPS)
        ('door', 33),
        ('door', 34),
        ('portal', 1),
        ('waypoint', 123),
        ('door', 124),  # Nihlathak
        ('door', 123),  # climbed back to the Halls of Pain
        ('door', 122),  # the deep chain last: the Halls of Anguish, then the Temple
        ('door', 121),
        ('portal', HARROGATH),  # its end: the Town Portal
    ]
    assert walk.legs.count(TZ_UP) == 2  # out of 130 and 124
    said = caplog.text
    assert (
        'Macro: zone: graph Act5-Manual + Act1-Catacombs: 129 (130 (131 (132)), 128); 35 (36 (37)); 123 (124, 122'
        in said
    )
    assert 'Macro: zone: Halls of Pain (123) cleared' in said
    assert "Macro: zone: Nihlathak's Temple (121) cleared" in said


@pytest.mark.usefixtures('zone')
def test_the_halls_are_run_on_their_way_to_nihlathak_and_pindleskin(monkeypatch):
    # They were "explored" on arrival (tz+ on the way, no stage of their own) and never run (the act harness,
    # 2026-10-21): a way on's level has its one run, as the itinerary's rule
    walk = act_5(monkeypatch)

    halls = walk.runs[walk.runs.index(123) :][:4]
    assert halls == [123, 124, 122, 121]


def test_act_5_runs_every_level_the_itinerarys_game_runs(monkeypatch):
    off = act_5(monkeypatch)
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((5,)))
    on = act_5(monkeypatch)

    assert set(on.levels) == set(off.levels)
    assert {121, 122, 123, 124} <= set(on.levels)
    assert off.kills == KILLS
    assert on.kills == ZONE_KILLS  # the same bosses, the rotation's after the act's boss (ROTATION_BOSSES_FIRST)
    assert len(on.waypoints) < len(off.waypoints)
    assert TZ_UP not in off.legs


# The Worldstone Chamber's portal (17:24:25-17:24:39 on 2026-10-21, rca/2026-10-21/worldstone-chamber-findings.md):
# clicked while Baal sat on his throne, "no click took Worldstone Chamber" left the game with act 5's other zones
# unplayed. Zone navigation keeps the game: the way in made again (tzloop.py USE_TRIES), then blocked.
@pytest.mark.usefixtures('zone')
def test_a_chamber_portal_that_opens_late_is_entered_on_a_later_way_and_baal_is_killed(monkeypatch, caplog):
    from inventory_tracking.macros import tzloop

    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: tzloop.USE_TRIES - 1}  # every try but the last in vain
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.moves.count(('untook', 132)) == tzloop.USE_TRIES - 1
    assert between(walk.moves, ('untook', 132), ('door', 132))
    assert walk.kills == ZONE_KILLS  # Baal, his loot, then the halls: the act's order kept
    assert walk.moves.index(('door', 132)) < walk.moves.index(('door', 124))
    assert 'Macro: zone: no click took Worldstone Chamber: try 1 of 3 into The Worldstone Chamber' in caplog.text
    assert 'game is left' not in caplog.text


@pytest.mark.usefixtures('zone')
def test_a_chamber_portal_that_never_opens_stops_the_loop_at_the_throne_and_never_leaves_baal_alive(
    monkeypatch, caplog
):
    # The player, 2026-10-22: "we need to kill all bosses, no exceptions to that -> they can give a very valuable drops,
    # especially baal's statue" (tzloop.py BOSS_STAYS): the Chamber is never blocked, the loop stops for the player
    from inventory_tracking.macros import stops, tzloop

    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: None}
    walk = game.play()

    assert walk.stopped is not None
    assert walk.stopped.endswith('Baal (The Worldstone Chamber) alive: the loop stops here for the player')
    assert walk.where == 131  # at the Throne, the game kept
    assert LEAVE not in walk.legs
    assert walk.moves.count(('untook', 132)) == tzloop.USE_TRIES
    assert 'The Worldstone Chamber (132) blocked' not in caplog.text
    assert stops.first('idle', on=True, dead=False) == stops.Remedy.STOP  # the stop's cause: no Save and Exit
    assert tzloop.SKIP_USE  # the dated switches are on
    assert tzloop.BOSS_STAYS


@pytest.mark.usefixtures('zone')
def test_without_boss_stays_a_chamber_portal_that_never_opens_blocks_the_chamber_and_act_5_goes_on(monkeypatch, caplog):
    from inventory_tracking.macros import tzloop

    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: None}
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert walk.moves.count(('untook', 132)) == tzloop.USE_TRIES
    assert ('door', 132) not in walk.moves
    assert 'Baal' not in walk.kills
    # Nihlathak, Pindleskin, the rest: all played (the switch off: no boss ledger asked, the rotation last as before)
    assert [kill for kill in KILLS if kill != 'Baal'] == walk.kills
    assert ('door', 124) in walk.moves
    assert ('door', 121) in walk.moves
    assert 'Macro: zone: The Worldstone Chamber (132) blocked: no click took its way in in 3 tries' in caplog.text
    assert '; Throne of Destruction goes on' in caplog.text


@pytest.mark.usefixtures('zone')
def test_the_game_is_never_left_for_no_goals_left_with_baal_alive(monkeypatch, caplog):
    # The last net (tzloop.py `boss_alive`): the Chamber blocked by any other way (here the block's own guard off), the
    # act played on, and at its end "no goals left" stops the loop instead of the Save and Exit
    from inventory_tracking.macros import tzloop

    monkeypatch.setattr(tzloop, 'boss_stays', lambda agenda, child, why: None)
    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: None}
    walk = game.play()

    assert walk.stopped == (
        'no goals left, but Baal (The Worldstone Chamber) alive: the loop stops here for the player'
    )
    assert LEAVE not in walk.legs
    assert [kill for kill in ZONE_KILLS if kill != 'Baal'] == walk.kills  # the rest of the act played first
    assert 'The Worldstone Chamber (132) blocked' in caplog.text
    # Baal dead: the game ends as before
    assert tzloop.boss_alive(game.game.loop.agenda) is not None
    game.game.killed.add('Baal')
    assert tzloop.boss_alive(game.game.loop.agenda) is None


# Games 4-6 at 09:13, 09:21, 09:27 on 2026-10-22 (rca/2026-10-22/baal-skipped-findings.md): Lister died with his last
# minions alive, the way on's press came at once from the stand, and the portal's gate (running/legs.py
# `throne_shut`) never held: the zone's script had the Chamber's way in as an `enter`, the gate reads the route's `use`
@pytest.mark.usefixtures('zone')
def test_the_thrones_way_on_is_the_routes_use_of_the_portal_and_its_gate_holds_while_the_hall_is_not_clear(
    monkeypatch,
):
    from inventory_tracking.game.records import Monster
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.macros.running.legs import throne_shut
    from inventory_tracking.routes.model import ENTER, use
    from tests.inventory_tracking.macros.fakes import player, world

    game = ActGame(5, monkeypatch)
    stages, gates = [], []
    door = game.way_on
    baal = Monster(1390514718, throne.THRONE_BAAL, 1, 15090.5, 5011.5)
    minion = Monster(2088635103, 571, 1, 15086.1, 5025.9)  # Lister's, alive as the press came at 09:13:34.8
    here = player(throne.THRONE, x=15080.5, y=5015.5)  # the stand, 14 from the portal: at the way on

    def way_on() -> None:
        if game.game.area == throne.THRONE:
            step = game.game.progress.step(throne.THRONE)
            stages.append(step.stage if step is not None else None)
            read = world(throne.THRONE, monsters=(baal, minion), game_name='g', player=here)
            gates.append(throne_shut(throne.Waves(), game.game.progress, read, 0.0))
        door()

    game.way_on = way_on
    walk = game.play()
    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.kills == ZONE_KILLS
    assert stages == [use('Worldstone Chamber', throne.CHAMBER)]
    assert gates == ['the throne hall first (1 left)']  # the level run, not the press
    monkeypatch.setattr(zonenav, 'PORTAL_USES', False)  # as before: the zone's `enter`, no gate
    stages.clear()
    gates.clear()
    game = ActGame(5, monkeypatch)
    door = game.way_on
    game.way_on = way_on
    game.play()
    assert [stage.kind for stage in stages if stage is not None] == [ENTER]
    assert gates == [None]


# The safety net behind the gate (tzloop.py FOUGHT_FIRST): teleport.py `baal_gone`'s "the throne hall is not clear:
# fought first" three times in a row (games 4-6 on 2026-10-22: the three tries in 0.12 s, the Chamber blocked) posts
# the level run each time, no try counted, and the Chamber is entered after
@pytest.mark.usefixtures('zone')
def test_three_fought_first_untooks_in_a_row_post_the_level_run_and_block_nothing(monkeypatch, caplog):
    from inventory_tracking.macros import tzloop

    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: 3}
    game.game.untook_why = '{}: the throne hall is not clear: fought first'
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.moves.count(('untook', 132)) == 3
    assert ('door', 132) in walk.moves
    assert walk.kills == ZONE_KILLS  # Baal killed, the act's order kept
    throne_runs = walk.runs.count(131)
    assert 'The Worldstone Chamber (132) blocked' not in caplog.text
    assert caplog.text.count('the level run fights it') == 3
    assert (
        'Macro: zone: Worldstone Chamber: the throne hall is not clear: fought first: the level run fights it (1 of 4)'
        in caplog.text
    )
    # Without the net each one is a try: after USE_TRIES the loop stops for the player (BOSS_STAYS), Baal alive
    monkeypatch.setattr(tzloop, 'FOUGHT_FIRST', False)
    caplog.clear()
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: 3}
    game.game.untook_why = '{}: the throne hall is not clear: fought first'
    walk = game.play()
    assert 'Baal' not in walk.kills
    assert walk.stopped is not None
    assert walk.stopped.endswith('Baal (The Worldstone Chamber) alive: the loop stops here for the player')
    assert walk.runs.count(131) < throne_runs  # the fought-first runs were the net's


@pytest.mark.usefixtures('zone')
def test_a_hall_the_run_cannot_clear_ends_in_the_tries_and_stops_the_loop_for_the_player(monkeypatch, caplog):
    from inventory_tracking.macros import tzloop

    caplog.set_level(logging.INFO)
    game = ActGame(5, monkeypatch)
    game.game.untook = {132: None}  # never takes
    game.game.untook_why = '{}: the throne hall is not clear: fought first'
    walk = game.play()

    assert caplog.text.count('the level run fights it') == tzloop.FOUGHT_RUNS
    assert walk.moves.count(('untook', 132)) == tzloop.FOUGHT_RUNS + tzloop.USE_TRIES
    assert walk.stopped is not None
    assert walk.stopped.endswith('Baal (The Worldstone Chamber) alive: the loop stops here for the player')
    assert walk.where == 131
    assert LEAVE not in walk.legs
    assert 'The Worldstone Chamber (132) blocked' not in caplog.text
