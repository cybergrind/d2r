"""The restart by a portal trip (macros/midgame.py TRIP, restart.py --when trip; the player, 2026-10-24 ~13:35: "we need
to restart in the middle of the run (on safe spot and time, maybe something like -> go to town and restart -> return
back)"): the field level's safe moment, the Town Portal, the stand in town, the new service back through the portal it
left (or the loop's own way back with the portal gone), over the scripted terror zone game of test_tzloop.py. Offline:
no proof of the game's own behaviour."""

import threading
import time
from dataclasses import replace

import pytest

from inventory_tracking.appraisal import service
from inventory_tracking.macros import loop as loop_module, midgame
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.agenda import HERALD, Objective
from inventory_tracking.macros.loop import TZ, TZ_BACK, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_PORTAL, TZ_WAYPOINT, Loop
from inventory_tracking.macros.midgame import TRIP, TRIP_BACK, TRIP_PORTAL, TRIP_TRIES, Moment, refusal
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.tracker import ZoneTracker
from tests.inventory_tracking.macros.fakes import Monster
from tests.inventory_tracking.macros.test_midgame import runner
from tests.inventory_tracking.macros.test_tzloop import GAME, ROGUE_ENCAMPMENT, Script


SIGHT = 30.0
LEVEL = 36  # Catacombs Level 3: a field level of the Catacombs zone


# -- the safe moment (`refusal`) ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('moment', 'why'),
    [
        (Moment(in_game=False), None),  # the lobby: the lobby restart's own moment
        (Moment(in_game=True, in_town=True), None),  # in town already: at once there
        (Moment(in_game=True, in_town=True, stack=('the town visit',)), None),  # a room package's town legs: carried
        (Moment(in_game=True, in_town=True, tripped=TRIP_TRIES, trips=False), None),
        (Moment(in_game=True), None),  # a field level, nothing near: the portal trip
        (Moment(in_game=True, hostile=40.0), None),
        (Moment(in_game=True, hostile=12.0), 'a hostile 12 away'),
        (Moment(in_game=True, valuable='Ko Rune at (1, 2)'), 'Ko Rune at (1, 2) on the ground'),
        (Moment(in_game=True, valuable='unread'), 'unread on the ground'),
        (Moment(in_game=True, remembered='Ring at (3, 4)'), 'Ring at (3, 4) remembered on the level'),
        (Moment(in_game=True, stack=('Town Portal for room',)), 'a package under way (Town Portal for room)'),
        (Moment(in_game=True, arena='Andariel'), 'Andariel alive on the level'),
        (Moment(in_game=True, herald='a Herald'), 'a Herald known on the level'),
        (Moment(in_game=True, trips=False), 'no portal trip in this kind: a town waited for'),
        (
            Moment(in_game=True, tripped=TRIP_TRIES),
            f'{TRIP_TRIES} portal trips made for the restart in this game: a town waited for',
        ),
        (Moment(in_game=True, pending=('a fight back',)), 'a fight back due'),
        (Moment(in_game=True, in_town=True, panels=('stash',)), 'stash open'),
        (Moment(in_game=True, dead=True), 'the character is dead'),
    ],
)
def test_the_trip_waits_for_a_quiet_field_moment_and_takes_a_town_at_once(moment, why):
    assert refusal(TRIP, moment, SIGHT) == why


@pytest.mark.parametrize('when', [midgame.SAFE, midgame.TOWN])
def test_the_trips_own_refusals_leave_the_other_words_as_they_were(when):
    # The arena and the Herald are TRIP's: `safe` and `town` judge as before
    assert refusal(when, Moment(in_game=True, in_town=True, arena='Andariel', herald='x'), SIGHT) is None
    assert refusal(midgame.SAFE, Moment(in_game=True, arena='Andariel', herald='x', trips=False), SIGHT) is None


def test_the_word_is_the_services_and_restart_pys() -> None:
    import importlib
    import sys
    from pathlib import Path

    tools = Path(__file__).resolve().parents[3] / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
    sys.path.insert(0, str(tools))
    restart = importlib.import_module('restart')
    assert TRIP in midgame.WHENS
    assert restart.TRIP == TRIP
    assert set(midgame.WHENS) == {restart.TOWN, restart.SAFE, restart.TRIP}


def test_the_package_is_the_portal_and_back_with_no_visit() -> None:
    goals = midgame.restart_package(LEVEL)
    assert [goal.label for goal in goals] == [TRIP_PORTAL, TRIP_BACK, 'continue the run']
    assert (goals[0].to, goals[1].to) == (ROGUE_ENCAMPMENT, LEVEL)


# -- the trip in the game ----------------------------------------------------------------------------------------------


def tripping(monkeypatch) -> Script:
    """A terror zone game in Catacombs Level 3, its run made, the games' records kept (midgame.py RECORD), the restart
    asked by the trip."""
    game = Script(LEVEL, monkeypatch)
    game.loop.records = ZoneTracker()
    assert game.leg() == TZ_LEVEL
    game.loop.restart_when = TRIP
    return game


def stand(game: Script) -> tuple[list[str | None], Cancelled | None]:
    """The next leg with the service's restart: its run cancelled once the loop stands (`safe_point`)."""
    run = game.play.run()
    seen: list[str | None] = []

    def restart() -> None:
        deadline = time.monotonic() + 5
        while game.loop.safe_point is None and time.monotonic() < deadline:
            time.sleep(0.01)
        seen.append(game.loop.safe_point)
        run.cancelled.set()  # the service's close()

    helper = threading.Thread(target=restart)
    helper.start()
    stopped = None
    try:
        game.loop.leg(run, lambda *_: {}, game.progress, game.hands())
    except Cancelled as error:
        stopped = error
    helper.join(5)
    return seen, stopped


def restarted(game: Script) -> None:
    """The new service: a fresh loop and route progress (as `make serve` builds them) on the same games' records."""
    records = game.loop.records
    loop = Loop(on=True, kind=TZ, chosen=True)
    loop.start()
    loop.records = records
    game.loop = loop
    game.progress = Progress(ROUTES, PERFORMED, game.book.killed, wanted=lambda a: a in game.zone)
    game.progress.note(GAME, game.area)


def test_a_quiet_field_moment_casts_town_portal_and_the_loop_stands_in_town_for_the_restart(monkeypatch, caplog):
    game = tripping(monkeypatch)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_PORTAL
    assert game.calls[-1] == ('portal', ROGUE_ENCAMPMENT)
    assert 'Macro: loop: safe moment for the restart: Catacombs Level 3, cyber32 (player unit 1): Town Portal' in (
        caplog.text
    )
    assert [goal.label for goal in reversed(game.loop.agenda.stack)] == [TRIP_BACK, 'continue the run']
    assert game.loop.restart_trip == GAME
    assert game.loop.trips_in(GAME) == 0  # no trip for room: its count and cap untouched

    with caplog.at_level('INFO'):
        seen, stopped = stand(game)
    assert stopped is not None
    assert seen == ['Rogue Encampment']
    assert 'Macro: loop: safe point: Rogue Encampment, cyber32 (player unit 1): the loop stands' in caplog.text
    assert [call for call in game.calls if call[0] == 'through'] == []  # still in town


def test_the_new_service_goes_back_through_the_portal_it_left_and_the_level_goes_on(monkeypatch, caplog):
    game = tripping(monkeypatch)
    assert game.leg() == TZ_PORTAL
    game.loop.portal_at = (5010.0, 5020.0)  # where the fake's town arrival put the character (portal.py `to_town`)
    _, stopped = stand(game)
    assert stopped is not None

    restarted(game)
    near: list[tuple[float, float] | None] = []

    def through(run, at=None) -> None:
        near.append(at)
        game.go('through', LEVEL)

    monkeypatch.setattr(loop_module, 'through_portal', through)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_BACK
    assert 'taken up after a restart' in caplog.text
    assert 'Macro: loop: back through the portal left for the restart' in caplog.text
    assert near == [(5010.0, 5020.0)]  # the portal found by its place in the record
    assert game.area == LEVEL
    assert game.loop.restart_trip is None
    assert game.loop.restart_when is None  # the new service holds nothing
    assert game.leg() == TZ_NEXT_LEVEL  # the level goes on: its run made, its way on
    assert game.loop.agenda.stack == []


def test_with_the_portal_gone_the_loop_takes_its_own_way_back_from_town(monkeypatch, caplog):
    game = tripping(monkeypatch)
    assert game.leg() == TZ_PORTAL
    _, stopped = stand(game)
    assert stopped is not None
    restarted(game)

    def gone(run, near=None) -> None:
        raise Abort('no Town Portal in sight')

    monkeypatch.setattr(loop_module, 'through_portal', gone)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_BACK  # no stop: no recovery, no game left
    assert "the portal left for the restart is not taken (no Town Portal in sight): the loop's own way back" in (
        caplog.text
    )
    assert game.area == ROGUE_ENCAMPMENT
    assert game.loop.restart_trip is None
    assert game.leg() == TZ_WAYPOINT  # the zone's own way from town
    assert game.loop.agenda.stack == []


def test_a_stop_out_of_town_on_the_way_back_is_a_stop(monkeypatch):
    game = tripping(monkeypatch)
    assert game.leg() == TZ_PORTAL
    game.loop.restart_when = None  # the hold dropped: the loop goes on

    def lost(run, near=None) -> None:
        game.go('through', LEVEL)
        raise Abort('the level is not under the pointer')

    monkeypatch.setattr(loop_module, 'through_portal', lost)
    with pytest.raises(Abort, match='not under the pointer'):
        game.leg()
    assert game.loop.restart_trip == GAME  # the next try is the restart's return still


def test_a_restart_that_never_comes_in_town_sends_the_loop_back_through_the_portal(monkeypatch, caplog):
    game = tripping(monkeypatch)
    monkeypatch.setattr(midgame, 'PARK_SECONDS', 0.2)
    assert game.leg() == TZ_PORTAL
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_BACK
    assert 'no restart came at the safe point' in caplog.text
    assert game.calls[-1] == ('through', LEVEL)
    assert game.loop.restart_when is None


def test_in_town_already_the_loop_stands_at_once_and_casts_nothing(monkeypatch):
    game = Script(ROGUE_ENCAMPMENT, monkeypatch)
    game.loop.restart_when = TRIP
    seen, stopped = stand(game)
    assert stopped is not None
    assert seen == ['Rogue Encampment']
    assert game.calls == []


def test_a_hostile_near_makes_no_trip_and_the_leg_is_made(monkeypatch, caplog):
    game = tripping(monkeypatch)
    here = game.play.world.player
    assert here is not None
    foe = Monster(41, 5, 1, here.x + 10.0, here.y)
    game.play.world = replace(game.play.world, monsters=(foe,))
    with caplog.at_level('INFO'):
        assert game.leg() != TZ_PORTAL
    assert 'Macro: loop: no safe point for the restart yet: a hostile 10 away' in caplog.text
    assert game.loop.restart_trip is None
    assert game.loop.restart_when == TRIP  # still waiting


def test_a_valuable_on_the_level_makes_no_trip(monkeypatch, caplog):
    game = tripping(monkeypatch)
    game.sightings[LEVEL] = 'Ist Rune at (100, 200)'
    game.picks = [True]  # the leg made instead: its pickup
    with caplog.at_level('INFO'):
        game.leg()
    assert 'no safe point for the restart yet: Ist Rune at (100, 200) remembered on the level' in caplog.text
    assert ('portal', ROGUE_ENCAMPMENT) not in game.calls


def test_a_herald_known_on_the_level_makes_no_trip(monkeypatch, caplog):
    game = tripping(monkeypatch)
    game.loop.agenda.kills[9] = Objective('kill', 'a Herald', HERALD, LEVEL, unit=9)
    assert game.loop.moment(game.play.world, game.hands(), game.progress).herald == 'a Herald'


def test_the_boss_alive_on_his_level_makes_no_trip_and_dead_he_does_not_hold_it(monkeypatch):
    game = Script(37, monkeypatch)  # Catacombs Level 4: Andariel's
    assert game.leg() == TZ_LEVEL  # the route chosen there
    game.loop.restart_when = TRIP
    assert game.loop.moment(game.play.world, game.hands(), game.progress).arena == 'Andariel'
    game.killed.add('Andariel')
    assert game.loop.moment(game.play.world, game.hands(), game.progress).arena == ''


def test_a_kind_with_no_package_waits_for_a_town(monkeypatch):
    from inventory_tracking.macros.loop import ANDARIEL

    game = tripping(monkeypatch)
    game.loop.kind = ANDARIEL
    assert game.loop.moment(game.play.world, game.hands(), game.progress).trips is False


def test_the_trips_a_game_are_capped(monkeypatch):
    game = tripping(monkeypatch)
    game.loop.restart_trips = (GAME, TRIP_TRIES)
    assert game.loop.moment(game.play.world, game.hands(), game.progress).tripped == TRIP_TRIES
    game.loop.restart_trips = ('another', TRIP_TRIES)
    assert game.loop.moment(game.play.world, game.hands(), game.progress).tripped == 0


# -- the service ------------------------------------------------------------------------------------------------------


def test_the_service_holds_a_trip_restart_and_the_players_pause_keeps_the_loop_off() -> None:
    made = runner()
    made.loop.on = True
    service.restart_now(made, {'loop': True, 'when': TRIP})
    assert made.loop.restart_when == TRIP
    assert made.restart_due() is None  # on the way: the field level, the portal
    made.loop.on = False  # the player's KP_6 while the trip-restart waits
    assert made.restart_due() == {'loop': False}
    service.restart_now(made, {'when': TRIP})
    service.restart_now(made, {'when': 'cancel'})
    assert made.loop.restart_when is None
    made.close()
