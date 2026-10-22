"""A service restart in the middle of a game (macros/midgame.py; the player, 2026-10-21 ~14:50: "pick new code in the
middle of the act run, without save/exit, just continue"): the safe point the loop stands at, the game's state carried
to the next service (`MacroRunner.resume_state` -> `resume`, taken up at the first leg in that game) over the scripted
act game of test_tzloop.py. Offline: no proof of the game's own behaviour."""

import json
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.appraisal import service
from inventory_tracking.macros import midgame, tzloop
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.agenda import Agenda, Objective, room_package
from inventory_tracking.macros.loop import ACT4, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_SHARD, TZ_WAYPOINT, GameId, Loop
from inventory_tracking.macros.midgame import SAFE, TOWN, Moment, refusal
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.sightings import Sighting
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import Monster, player, world
from tests.inventory_tracking.macros.test_tzloop import GAME, act4_game


SIGHT = 30.0


# -- the safe point (`refusal`) ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('when', 'moment', 'why'),
    [
        (SAFE, Moment(in_game=False), None),  # the lobby: the lobby restart's own moment
        (TOWN, Moment(in_game=False), None),
        (TOWN, Moment(in_game=True, in_town=True), None),
        (SAFE, Moment(in_game=True, in_town=True, stack=('the town visit', 'back through the portal')), None),
        (TOWN, Moment(in_game=True), 'not in a town'),
        (SAFE, Moment(in_game=True, hostile=40.0), None),  # a level whose run ended, nothing near
        (SAFE, Moment(in_game=True, hostile=12.0), 'a hostile 12 away'),  # a restart mid-fight is forbidden
        (SAFE, Moment(in_game=True, valuable='Ko Rune at (1, 2)'), 'Ko Rune at (1, 2) on the ground'),
        (SAFE, Moment(in_game=True, valuable='unread'), 'unread on the ground'),
        (SAFE, Moment(in_game=True, remembered='Ring at (3, 4)'), 'Ring at (3, 4) remembered on the level'),
        (SAFE, Moment(in_game=True, stack=('Town Portal for room',)), 'a package under way (Town Portal for room)'),
        (SAFE, Moment(in_game=True, in_town=True, panels=('stash',)), 'stash open'),
        (SAFE, Moment(in_game=True, in_town=True, swap=True), "the Gheed's swap is under way"),
        (SAFE, Moment(in_game=True, in_town=True, pending=('room in the cube',)), 'room in the cube due'),
        (SAFE, Moment(in_game=True, dead=True), 'the character is dead'),
    ],
)
def test_a_safe_point_is_between_legs_with_nothing_near_nothing_down_nothing_under_way(when, moment, why):
    assert refusal(when, moment, SIGHT) == why


def test_the_sight_is_the_hunts() -> None:
    from inventory_tracking.macros.hunting.base import SIGHT as HUNT_SIGHT

    assert midgame.sight() == HUNT_SIGHT == SIGHT


# -- the game carried over a restart -----------------------------------------------------------------------------------


def restarted(game, monkeypatch, kept: dict | None) -> None:
    """The new service: a fresh loop and route progress (as `make serve` builds them), the old one's state taken up
    through JSON as resume.json carries it."""
    loop = Loop(on=True, kind=ACT4, chosen=True)
    loop.start()
    loop.carried = json.loads(json.dumps(kept)) if kept is not None else None
    game.loop = loop
    game.progress = Progress(ROUTES, PERFORMED, lambda: frozenset(game.killed), wanted=lambda a: a in game.zone)
    game.progress.note(GAME, game.area)


def test_a_restart_in_the_fortress_after_the_shard_uses_no_second_one(monkeypatch, caplog):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None
    assert kept['agenda']['acts'] == [4]

    restarted(game, monkeypatch, kept)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_WAYPOINT  # the act's boss first, as before the restart
    assert [call for call in game.calls if call[0] == 'terrorize'] == [('terrorize', 4)]
    assert game.loop.agenda.acts == (4,)
    assert game.loop.agenda.game == GameId(GAME, 1)
    assert 'Macro: loop: game cyber32 (player unit 1) taken up after a restart' in caplog.text


def test_without_the_game_carried_a_restart_in_town_would_use_a_second_shard(monkeypatch):
    # What the carried state prevents (the lobby restart's state had none of the game's)
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    restarted(game, monkeypatch, None)
    assert game.leg() == TZ_SHARD
    assert [call for call in game.calls if call[0] == 'terrorize'] == [('terrorize', 4)] * 2


def test_a_level_run_before_the_restart_stays_run(monkeypatch):
    game = act4_game(monkeypatch)
    legs = [game.leg() for _ in range(4)]
    assert legs == [TZ_SHARD, TZ_WAYPOINT, TZ_LEVEL, TZ_NEXT_LEVEL]  # the River of Flame run, into the Sanctuary
    assert (game.runs, game.area) == ([107], 108)
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None

    restarted(game, monkeypatch, kept)
    assert game.leg() == TZ_LEVEL
    assert game.runs == [107, 108]  # on with the Sanctuary: the River of Flame is not played again
    assert (game.loop.agenda.worked[107], game.loop.agenda.worked[108]) == (1, 1)
    assert {107, 108} <= game.loop.agenda.entered
    assert game.progress.facts.entered >= set(kept['facts']['entered'])
    assert [call for call in game.calls if call[0] == 'terrorize'] == [('terrorize', 4)]


def test_the_act_seconds_clock_goes_on_from_the_games_start(monkeypatch):
    game = act4_game(monkeypatch)
    game.loop.seen = (GAME, time.monotonic() - 1000.0)  # the game began 1000 s ago
    assert game.leg() == TZ_SHARD
    kept = midgame.snapshot(game.loop, game.progress)
    restarted(game, monkeypatch, kept)
    assert game.leg() == TZ_WAYPOINT
    left = tzloop.time_left(game.loop, GAME)
    assert left is not None
    assert ACT4.game_seconds is not None
    assert ACT4.game_seconds - 1010 < left < ACT4.game_seconds - 990  # not a fresh 2700 s


def test_a_new_game_is_never_taken_for_the_kept_one(monkeypatch):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None
    restarted(game, monkeypatch, {**kept, 'game': ['cyber33', 1]})  # another game's name
    assert game.leg() == TZ_SHARD  # this game's own shard
    assert game.loop.carried is None  # looked at once
    restarted(game, monkeypatch, {**kept, 'game': [GAME, 2]})  # the name again, another character unit
    assert game.leg() == TZ_SHARD


def test_a_room_package_under_way_in_town_goes_on_after_the_restart(monkeypatch):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    game.loop.agenda.push(*room_package(107)[1:])  # the Town Portal made: the visit, back through the portal
    game.loop.portal_at, game.loop.trip, game.loop.trips = (5010.0, 5020.0), GAME, 1
    kept = midgame.snapshot(game.loop, game.progress)
    restarted(game, monkeypatch, kept)
    assert game.loop.carried is not None
    midgame.restore(game.loop, game.play.world, game.progress, game.loop.carried)
    assert [goal.label for goal in reversed(game.loop.agenda.stack)] == [
        'the town visit',
        'back through the portal',
        'continue the run',
    ]
    assert game.loop.portal_at == (5010.0, 5020.0)
    assert game.loop.trips_in(GAME) == 1


def test_an_objective_with_a_place_comes_back_whole() -> None:
    agenda = Agenda()
    agenda.push(Objective('kill', 'a group of 5', 4, 107, (5000.5, 6000.0), 77))
    again = Agenda()
    again.take_up(json.loads(json.dumps(agenda.state())), GameId(GAME, 1))
    assert again.stack == agenda.stack
    assert again.game == GameId(GAME, 1)


def test_a_malformed_kept_game_leaves_the_loops_own_agenda(monkeypatch):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    before = game.loop.agenda
    kept = midgame.snapshot(game.loop, game.progress)
    assert kept is not None
    broken = {**kept, 'agenda': {**kept['agenda'], 'worked': 'nonsense'}}
    assert not midgame.restore(game.loop, game.play.world, game.progress, broken)
    assert game.loop.agenda is before


def runner() -> MacroRunner:
    return MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'))


def test_a_remembered_valuable_and_the_game_ride_the_restart_state(monkeypatch):
    before = runner()
    before.loop.on, before.loop.kind = True, ACT4
    before.loop.game_id = GameId(GAME, 1)
    before.loop.agenda.begin(before.loop.game_id)
    before.loop.agenda.shard, before.loop.agenda.acts = 'used', (4,)
    before.sightings.game = (GAME, 1)
    before.sightings.items[9] = Sighting(9, 'Ber Rune', 5100.0, 5200.0, 107, time.monotonic(), read=False)
    state = json.loads(json.dumps(before.resume_state()))
    before.close()

    after = runner()
    after.resume(state)
    assert [found.label for found in after.sightings.outstanding()] == ['Ber Rune']  # still fetched
    assert after.loop.carried is not None
    assert midgame.restore(after.loop, world(107, player=player(107)), None, after.loop.carried)
    assert after.loop.agenda.acts == (4,)
    assert after.loop.agenda.shard == 'used'
    after.close()


def test_the_kind_playing_stays_and_the_asked_one_comes_next() -> None:
    before = runner()
    before.loop.kind, before.loop.pending = ACT4, None
    from inventory_tracking.macros.loop import ANDARIEL

    before.loop.pending = ANDARIEL
    state = before.resume_state()
    before.close()
    assert (state['loop_kind'], state['loop_pending']) == ('act4', 'andariel')
    after = runner()
    after.resume(state)
    assert after.loop.kind == ACT4  # the game goes on as the act it is
    assert after.loop.pending == ANDARIEL  # from the next game
    after.close()

    # With the loop on: the resume's own turn on (a turn on takes a pending kind at once) leaves the kind playing
    on = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=Path('/nonexistent'),
        execute=lambda cancelled, routine: None,
        place=lambda: (GAME, 107),
    )
    on.resume({**state, 'loop': True})
    on.poll(10.0)
    assert on.loop.on
    assert (on.loop.kind, on.loop.pending) == (ACT4, ANDARIEL)
    on.close()


# -- the hold: the loop stands at the safe point, the service restarts -----------------------------------------------


def test_the_loop_stands_at_a_safe_point_until_the_restart_cancels_the_run(monkeypatch, caplog):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    game.loop.restart_when = SAFE
    run = game.play.run()
    seen: list[str | None] = []

    def restart() -> None:
        while game.loop.safe_point is None:
            time.sleep(0.01)
        seen.append(game.loop.safe_point)
        run.cancelled.set()  # the service's close()

    helper = threading.Thread(target=restart)
    helper.start()
    with caplog.at_level('INFO'), pytest.raises(Cancelled):
        game.loop.leg(run, lambda *_: {}, game.progress, game.hands())
    helper.join(5)
    assert seen == ['The Pandemonium Fortress']
    assert game.loop.safe_point is None
    assert 'Macro: loop: safe point: The Pandemonium Fortress, cyber32 (player unit 1): the loop stands' in caplog.text


def test_no_safe_point_by_a_hostile_the_leg_is_made_and_the_refusal_said(monkeypatch, caplog):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    assert game.leg() == TZ_WAYPOINT  # in the River of Flame now
    foe = Monster(41, 5, 1, 5010.0, 5000.0)
    game.play.world = replace(game.play.world, monsters=(foe,))
    game.loop.restart_when = SAFE
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_LEVEL  # the leg is made: no stand by a fight
    assert 'Macro: loop: no safe point for the restart yet: a hostile 10 away' in caplog.text
    assert game.loop.safe_point is None
    assert game.loop.restart_when == SAFE  # still waiting


def test_a_restart_that_never_comes_drops_the_hold_and_the_loop_goes_on(monkeypatch, caplog):
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    monkeypatch.setattr(midgame, 'PARK_SECONDS', 0.2)
    game.loop.restart_when = TOWN
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_WAYPOINT
    assert game.loop.restart_when is None
    assert 'no restart came at the safe point' in caplog.text


def test_the_runner_gives_the_restart_once_the_loop_stands_or_is_off() -> None:
    made = runner()
    assert made.restart_due() is None
    made.loop.on = True
    made.hold_restart(SAFE, {'loop': True})
    assert made.loop.restart_when == SAFE
    assert made.restart_due() is None  # still on the way
    made.loop.safe_point = 'River of Flame'
    assert made.restart_due() == {'loop': True}
    assert made.restart_due() is None  # once
    made.hold_restart(TOWN, {'loop': True})
    made.loop.on = False  # the player's pause wins
    assert made.restart_due() == {'loop': False}
    made.hold_restart(TOWN, {})
    made.cancel_restart()
    assert made.loop.restart_when is None
    made.loop.on = True
    made.loop.safe_point = 'x'
    assert made.restart_due() is None
    made.close()


def test_the_service_holds_a_restart_asked_with_when_and_restarts_at_once_without() -> None:
    made = runner()
    made.loop.on = True
    service.restart_now(made, {'loop': True, 'when': SAFE})
    assert made.loop.restart_when == SAFE
    service.restart_now(made, {'when': 'cancel'})
    assert made.loop.restart_when is None
    with pytest.raises(service.Restart) as raised:
        service.restart_now(made, {'loop': True, 'loop_kind': 'act4'})
    assert raised.value.target == {'loop': True, 'loop_kind': 'act4', 'loop_pending': None}
    with pytest.raises(service.Restart):
        service.restart_now(made, {'when': 'lobby'})  # restart.py's own wait: at once here
    made.close()
